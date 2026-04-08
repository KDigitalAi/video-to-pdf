"""
Flask web application for Vimeo Subtitle Automation Pipeline.
"""
import os
import uuid
import time
import re
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import threading
import zipfile

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.workflow.pipeline import Pipeline
from src.processing.vtt_parser import parse_vtt_to_text
from src.processing.text_cleaner import clean_subtitle_text
from src.processing.smart_summarizer import smart_summarize, rule_based_filter
from src.processing.pdf_generator import markdown_string_to_pdf
from src.utils.helpers import sanitize_filename
from src.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Initialize Flask app with explicit template and static folders
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
# Total request size cap (multiple VTTs in one upload)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size

# Use /tmp for Vercel (writable) or local directories for development
if os.getenv('VERCEL'):
    # Vercel serverless environment - use /tmp
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    app.config['OUTPUT_FOLDER'] = '/tmp/output/final_pdfs'
    app.config['RAW_VTT_FOLDER'] = '/tmp/output/raw_vtt'
    app.config['MARKDOWN_FOLDER'] = '/tmp/output/cleaned_markdown'
else:
    # Local development
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['OUTPUT_FOLDER'] = 'output/final_pdfs'
    app.config['RAW_VTT_FOLDER'] = 'output/raw_vtt'
    app.config['MARKDOWN_FOLDER'] = 'output/cleaned_markdown'

# Ensure directories exist
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config.get('RAW_VTT_FOLDER', 'output/raw_vtt')).mkdir(parents=True, exist_ok=True)
Path(app.config.get('MARKDOWN_FOLDER', 'output/cleaned_markdown')).mkdir(parents=True, exist_ok=True)

logger = setup_logger()

# Store job status (in production, use Redis or database)
job_status = {}


def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in {'csv', 'vtt'}


def get_file_extension(filename: str) -> str:
    """Get lowercase extension without leading dot."""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def is_valid_vtt_file(filepath: Path) -> bool:
    """Validate VTT signature to avoid parsing non-VTT files."""
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            first_non_empty = ''
            for line in f:
                stripped = line.strip()
                if stripped:
                    first_non_empty = stripped
                    break
        return first_non_empty.upper().startswith('WEBVTT')
    except Exception:
        return False


def _collect_recent_pdfs(job_start_time: float) -> list[Path]:
    """Collect PDFs generated recently by a job."""
    pdf_files = []
    for pdf_file in Path(app.config['OUTPUT_FOLDER']).glob('*.pdf'):
        if pdf_file.stat().st_mtime >= (job_start_time - 300):
            pdf_files.append(pdf_file)
    pdf_files.sort(key=lambda p: p.stat().st_mtime)
    return pdf_files


def _create_zip_for_job(job_id: str, pdf_files: list[Path]) -> Path:
    """Create ZIP archive for generated PDFs."""
    zip_filename = f"{job_id}_all_modules.zip"
    zip_path = Path(app.config['OUTPUT_FOLDER']) / zip_filename
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pdf_file in pdf_files:
            zipf.write(str(pdf_file), pdf_file.name)
    return zip_path


def _unique_pdf_title_bases(original_filenames: list[str]) -> list[str]:
    """
    Build unique sanitized title bases for PDF filenames when multiple uploads share the same stem.
    """
    stems = []
    for name in original_filenames:
        stem = Path(secure_filename(name)).stem or "Uploaded_Video"
        stems.append(sanitize_filename(stem))
    seen: dict[str, int] = {}
    out: list[str] = []
    for s in stems:
        if s not in seen:
            seen[s] = 0
            out.append(s)
        else:
            seen[s] += 1
            out.append(f"{s}_{seen[s]}")
    return out


def _natural_sort_key(name: str) -> list[object]:
    """
    Natural sort key so names like ``file_2`` come before ``file_10``.
    """
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name or "")]


def _truncate_for_filename_phrase(text: str, max_len: int = 72) -> str:
    """Shorten a title phrase for use in a filesystem-safe base name."""
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1].rsplit(" ", 1)[0]
    return cut.strip() or t[:max_len].strip()


def _is_placeholder_heading(heading: str, stem_hint: str) -> bool:
    """
    Return True if a markdown heading is likely an auto filename (not real topic).

    Examples: ``auto_generated_captions_4``, generic upload stems.
    """
    h = (heading or "").strip().lower()
    s = (stem_hint or "").strip().lower()
    if not h:
        return True
    if h in ("video notes", "uploaded video", "uploaded_video", "video_notes"):
        return True
    if s and h == s:
        if re.search(r"auto[_\s-]*generated|caption|subtitle|transcript|vtt|webvtt|upload", h):
            return True
        if re.fullmatch(r"[\w-]+_\d+", h.replace(" ", "_")):
            return True
    if re.search(r"^auto[_\s-]*generated", h):
        return True
    if re.search(r"captions?_\d+$", h) or re.search(r"_captions?_\d+", h):
        return True
    return False


def _first_sentence(text: str) -> str:
    """Return the first sentence-like chunk from a line or paragraph."""
    t = (text or "").strip()
    if not t:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)
    return parts[0].strip() if parts else t


def _title_from_plain_text(plain: str) -> str:
    """
    Derive a short topic phrase from cleaned/filtered subtitle prose (no markdown).
    """
    body = re.sub(r"\s+", " ", (plain or "").strip())
    if not body or body.startswith("[No subtitle"):
        return ""
    words = body.split()
    if len(words) >= 8:
        return " ".join(words[:12])
    if len(words) >= 4:
        return " ".join(words)
    return ""


def _replace_first_h2_markdown(markdown_text: str, new_heading: str) -> str:
    """
    Replace the first top-level ``##`` heading in markdown, or prepend one if absent.

    Does not modify ``###`` or deeper headings.
    """
    nh = (new_heading or "").strip().replace("\n", " ").replace("\r", "")
    if not nh:
        return markdown_text
    lines = (markdown_text or "").splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("###"):
            continue
        if re.match(r"^##\s*", s):
            lines[i] = f"## {nh}"
            return "\n".join(lines)
    return f"## {nh}\n\n{(markdown_text or '').strip()}\n"


def _derive_pdf_title(markdown_text: str, stem_hint: str, content_hint: str) -> str:
    """
    Choose a human-meaningful title for the output PDF from markdown and subtitle text.

    Ignores generic ``##`` headings that mirror upload filenames. Uses Overview,
    Key Concepts, Detailed Notes, then filtered subtitle prose.
    """
    lines = [ln.rstrip() for ln in (markdown_text or "").splitlines()]

    for prefix, skip in (("## ", 3), ("# ", 2)):
        for line in lines:
            s = line.strip()
            if s.startswith(prefix):
                cand = s[skip:].strip()
                if cand and not _is_placeholder_heading(cand, stem_hint):
                    return _truncate_for_filename_phrase(cand)

    in_overview = False
    for line in lines:
        ls = line.strip()
        if ls == "### Overview":
            in_overview = True
            continue
        if in_overview:
            if ls.startswith("### ") or ls.startswith("## "):
                break
            if ls:
                sent = _first_sentence(ls)
                if sent and len(sent.split()) >= 4:
                    return _truncate_for_filename_phrase(sent)
                break

    for line in lines:
        m = re.match(r"^[-*]\s*\*\*([^*]+)\*\*", line.strip())
        if m:
            term = m.group(1).strip()
            if len(term) >= 3 and not _is_placeholder_heading(term, stem_hint):
                return _truncate_for_filename_phrase(term)

    in_dn = False
    for line in lines:
        ls = line.strip()
        if ls == "### Detailed Notes":
            in_dn = True
            continue
        if in_dn:
            if ls.startswith("### ") or ls.startswith("## "):
                break
            if ls and not ls.startswith("|") and not ls.startswith("---"):
                sent = _first_sentence(ls)
                if sent and len(sent.split()) >= 3:
                    return _truncate_for_filename_phrase(sent)
                break

    from_plain = _title_from_plain_text(content_hint)
    if from_plain:
        return _truncate_for_filename_phrase(from_plain)

    stem = (stem_hint or "").strip() or "video_notes"
    return _truncate_for_filename_phrase(stem)


def _title_to_filename_base(title: str, fallback_base: str = "video_notes") -> str:
    """
    Convert a human title into a safe filename base.
    """
    cleaned = re.sub(r"[^\w\s-]", " ", title or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = fallback_base
    base = sanitize_filename(cleaned)
    if len(base) > 100:
        base = base[:100].rstrip("_- ")
    return base or fallback_base


def _vtt_to_structured_markdown(vtt_path: Path, title_hint: str) -> tuple[str, str]:
    """
    Parse one VTT file and return structured markdown with a derived display title.
    """
    if not is_valid_vtt_file(vtt_path):
        raise ValueError("Invalid VTT file. File must start with WEBVTT.")

    raw_text = parse_vtt_to_text(str(vtt_path))
    if not raw_text:
        raise ValueError("Could not parse VTT file. Ensure it is a valid WebVTT file.")

    cleaned_text = clean_subtitle_text(raw_text)
    if not cleaned_text.strip():
        cleaned_text = "[No subtitle content available]"

    structured_md = smart_summarize(
        raw_text=cleaned_text,
        video_title=title_hint,
        use_ai=True,
    ).strip()
    filtered_for_title = rule_based_filter(cleaned_text)
    display_title = _derive_pdf_title(structured_md, title_hint, filtered_for_title)
    structured_md = _replace_first_h2_markdown(structured_md, display_title)
    return display_title, structured_md


def _vtt_file_to_pdf(vtt_path: Path, title_base: str) -> Path:
    """
    Parse one VTT file, summarize, and write a PDF under OUTPUT_FOLDER.

    Args:
        vtt_path: Path to the WebVTT file on disk.
        title_base: Sanitized base name (without extension) for the output PDF.

    Returns:
        Path to the written PDF file.

    Raises:
        ValueError: If VTT is invalid or empty after parse.
        RuntimeError: If PDF generation fails.
    """
    display_title, structured_md = _vtt_to_structured_markdown(vtt_path, title_base)
    markdown_content = f"{structured_md}\n"

    file_base = _title_to_filename_base(display_title, fallback_base=title_base)
    pdf_path = Path(app.config['OUTPUT_FOLDER']) / f"{file_base}.pdf"
    if not markdown_string_to_pdf(markdown_content, str(pdf_path), title=None):
        raise RuntimeError("PDF generation failed.")
    return pdf_path


def process_vtt_async(job_id: str, vtt_path: str, original_name: str):
    """Process a directly-uploaded VTT file into PDF."""
    try:
        job_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Parsing VTT file...',
            'pdf_paths': [],
            'zip_path': None,
            'error': None,
            'file_errors': [],
        }

        source_path = Path(vtt_path)
        bases = _unique_pdf_title_bases([original_name])
        title_base = bases[0]

        job_status[job_id]['progress'] = 20
        job_status[job_id]['message'] = 'Cleaning and summarizing...'
        pdf_path = _vtt_file_to_pdf(source_path, title_base)

        job_status[job_id]['status'] = 'completed'
        job_status[job_id]['pdf_paths'] = [str(pdf_path)]
        job_status[job_id]['zip_path'] = None
        job_status[job_id]['message'] = 'Generated 1 PDF successfully. File ready for download.'
        job_status[job_id]['progress'] = 100
    except Exception as e:
        logger.error(f"VTT processing error for job {job_id}: {e}")
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['error'] = str(e)
        job_status[job_id]['message'] = f'Error: {str(e)}'


def process_multiple_vtt_async(job_id: str, saved: list[tuple[str, str]]):
    """
    Process multiple uploaded VTT paths sequentially in one background job.

    Args:
        job_id: Job identifier for status and ZIP naming.
        saved: List of (absolute_path_on_disk, original_filename) for each VTT.
    """
    job_status[job_id] = {
        'status': 'processing',
        'progress': 0,
        'message': 'Starting batch...',
        'pdf_paths': [],
        'zip_path': None,
        'error': None,
        'file_errors': [],
    }

    try:
        # Keep output order predictable for merged PDF sections.
        saved = sorted(saved, key=lambda pair: _natural_sort_key(pair[1]))
        n = len(saved)
        orig_names = [pair[1] for pair in saved]
        title_bases = _unique_pdf_title_bases(orig_names)
        combined_sections: list[str] = []
        combined_titles: list[str] = []
        file_errors: list[str] = []

        for i, ((filepath, original_name), title_base) in enumerate(zip(saved, title_bases)):
            job_status[job_id]['message'] = f'Processing VTT {i + 1} of {n}: {original_name}'
            job_status[job_id]['progress'] = max(1, int(5 + (90 * i) / max(n, 1)))
            try:
                section_title, section_md = _vtt_to_structured_markdown(Path(filepath), title_base)
                combined_titles.append(section_title)
                combined_sections.append(section_md)
            except Exception as e:
                err_line = f"{original_name}: {e}"
                file_errors.append(err_line)
                logger.error(f"Batch VTT job {job_id}: {err_line}")

        job_status[job_id]['file_errors'] = file_errors

        if not combined_sections:
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['error'] = '; '.join(file_errors) if file_errors else 'All VTT files failed.'
            job_status[job_id]['message'] = job_status[job_id]['error']
            job_status[job_id]['progress'] = 100
            return

        # Build one merged markdown/PDF for all uploaded VTT files.
        merged_markdown = "\n\n---\n\n".join(combined_sections).strip() + "\n"
        merged_title = combined_titles[0].strip() if combined_titles else "video_notes"
        merged_title = _truncate_for_filename_phrase(merged_title, max_len=40)
        merged_base = _title_to_filename_base(f"{merged_title}_notes", fallback_base="video_notes")
        merged_pdf = Path(app.config['OUTPUT_FOLDER']) / f"{merged_base}.pdf"

        job_status[job_id]['message'] = 'Creating merged PDF...'
        job_status[job_id]['progress'] = 95
        if not markdown_string_to_pdf(merged_markdown, str(merged_pdf), title=None):
            raise RuntimeError("Failed to generate merged PDF.")

        job_status[job_id]['status'] = 'completed'
        job_status[job_id]['pdf_paths'] = [str(merged_pdf)]
        job_status[job_id]['zip_path'] = None
        ok_count = len(combined_sections)
        if file_errors:
            job_status[job_id]['message'] = (
                f'Generated 1 merged PDF from {ok_count} of {n} file(s). Some files failed — see details below.'
            )
        else:
            job_status[job_id]['message'] = (
                f'Generated 1 merged PDF from {ok_count} uploaded VTT files.'
            )
        job_status[job_id]['progress'] = 100
    except Exception as e:
        logger.error(f"Batch VTT processing error for job {job_id}: {e}")
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['error'] = str(e)
        job_status[job_id]['message'] = f'Error: {str(e)}'


def process_pipeline_async(job_id, manifest_path, vimeo_token):
    """
    Process pipeline in background thread.
    
    Args:
        job_id: Unique job identifier
        manifest_path: Path to uploaded CSV file
        vimeo_token: Vimeo API token
    """
    try:
        job_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Initializing pipeline...',
            'pdf_paths': [],  # Changed from pdf_path to pdf_paths (list)
            'zip_path': None,  # Add ZIP file path
            'error': None,
            'file_errors': [],
        }
        
        # Initialize pipeline with output base path
        output_folder = app.config.get('OUTPUT_FOLDER', 'output/final_pdfs')
        if '/final_pdfs' in output_folder:
            output_base = output_folder.rsplit('/final_pdfs', 1)[0]
        elif '/tmp' in output_folder:
            output_base = '/tmp/output'
        else:
            output_base = 'output'
        
        pipeline = Pipeline(vimeo_token, output_base=output_base)
        
        # Run pipeline
        job_status[job_id]['message'] = 'Processing videos...'
        job_status[job_id]['progress'] = 10
        
        # Run pipeline (this will process all videos)
        pipeline.run(manifest_path)
        
        job_status[job_id]['progress'] = 90
        job_status[job_id]['message'] = 'Generating PDFs...'
        
        # Find generated PDFs - look for PDFs created after job started
        job_start_time = time.time()
        # Wait a bit for PDFs to be written
        time.sleep(2)
        pdf_files = _collect_recent_pdfs(job_start_time)
        
        if pdf_files:
            zip_path = _create_zip_for_job(job_id, pdf_files)
            
            job_status[job_id]['status'] = 'completed'
            job_status[job_id]['pdf_paths'] = [str(p) for p in pdf_files]  # Store all PDF paths
            job_status[job_id]['zip_path'] = str(zip_path)  # Store ZIP path
            job_status[job_id]['message'] = f'Generated {len(pdf_files)} PDF(s) successfully. ZIP file ready for download.'
            job_status[job_id]['progress'] = 100
        else:
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['error'] = 'PDF generation failed. Check logs for details.'
            job_status[job_id]['message'] = 'PDF generation failed'
            
    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}")
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['error'] = str(e)
        job_status[job_id]['message'] = f'Error: {str(e)}'


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


def _collect_uploaded_files():
    """
    Normalize multipart input to a list of FileStorage objects.

    Accepts multiple parts named ``files`` (recommended) or a single ``file`` (legacy).
    """
    multi = [f for f in request.files.getlist('files') if f and f.filename]
    if multi:
        return multi
    single = request.files.get('file')
    if single and single.filename:
        return [single]
    return []


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle one or more file uploads and start processing."""
    files = _collect_uploaded_files()
    if not files:
        return jsonify({
            'success': False,
            'error': 'No file uploaded'
        }), 400

    for f in files:
        if not allowed_file(f.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Each file must be .csv or .vtt.'
            }), 400

    extensions = {get_file_extension(secure_filename(f.filename)) for f in files}
    if 'csv' in extensions and 'vtt' in extensions:
        return jsonify({
            'success': False,
            'error': 'Upload either a CSV manifest or one or more VTT files, not both in the same request.'
        }), 400
    if extensions == {'csv'} and len(files) > 1:
        return jsonify({
            'success': False,
            'error': 'Only one CSV manifest can be uploaded at a time.'
        }), 400

    try:
        job_id = str(uuid.uuid4())

        if extensions == {'csv'}:
            file = files[0]
            filename = secure_filename(file.filename)
            filepath = Path(app.config['UPLOAD_FOLDER']) / f"{job_id}_{filename}"
            file.save(str(filepath))
            vimeo_token = os.getenv("VIMEO_TOKEN")
            if not vimeo_token:
                return jsonify({
                    'success': False,
                    'error': 'VIMEO_TOKEN not configured. Please set it in .env file for CSV processing.'
                }), 400
            thread = threading.Thread(
                target=process_pipeline_async,
                args=(job_id, str(filepath), vimeo_token)
            )
        else:
            saved: list[tuple[str, str]] = []
            for idx, file in enumerate(files):
                filename = secure_filename(file.filename)
                filepath = Path(app.config['UPLOAD_FOLDER']) / f"{job_id}_{idx}_{filename}"
                file.save(str(filepath))
                if not is_valid_vtt_file(filepath):
                    return jsonify({
                        'success': False,
                        'error': f'Invalid VTT file ({filename}). File must start with WEBVTT.'
                    }), 400
                saved.append((str(filepath), filename))

            if len(saved) == 1:
                thread = threading.Thread(
                    target=process_vtt_async,
                    args=(job_id, saved[0][0], saved[0][1])
                )
            else:
                thread = threading.Thread(
                    target=process_multiple_vtt_async,
                    args=(job_id, saved)
                )

        thread.daemon = True
        thread.start()

        n = len(files)
        return jsonify({
            'success': True,
            'job_id': job_id,
            'file_count': n,
            'message': (
                'Processing started...'
                if n == 1
                else f'Uploaded {n} VTT files. Processing started...'
            ),
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500


@app.route('/status/<job_id>')
def get_status(job_id):
    """Get processing status for a job."""
    if job_id not in job_status:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404
    
    status = job_status[job_id]
    return jsonify({
        'success': True,
        'status': status['status'],
        'progress': status.get('progress', 0),
        'message': status.get('message', ''),
        'pdf_paths': status.get('pdf_paths', []),  # Changed from pdf_path
        'zip_path': status.get('zip_path'),  # Add ZIP path
        'pdf_count': len(status.get('pdf_paths', [])),  # Add count
        'error': status.get('error'),
        'file_errors': status.get('file_errors', []),
    })


@app.route('/download/<job_id>')
def download_pdf(job_id):
    """Download generated PDFs as ZIP file."""
    if job_id not in job_status:
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404
    
    status = job_status[job_id]
    
    # Check for ZIP file first (preferred)
    if status.get('zip_path'):
        zip_path = Path(status['zip_path'])
        if zip_path.exists():
            return send_file(
                str(zip_path),
                as_attachment=True,
                download_name=f"all_modules_{job_id[:8]}.zip",
                mimetype='application/zip'
            )

    # If there is exactly one generated PDF, return it directly.
    pdf_paths = [Path(p) for p in status.get('pdf_paths', []) if Path(p).exists()]
    if status['status'] == 'completed' and len(pdf_paths) == 1:
        pdf_path = pdf_paths[0]
        return send_file(
            str(pdf_path),
            as_attachment=True,
            download_name=pdf_path.name,
            mimetype='application/pdf'
        )
    
    # Fallback: if ZIP doesn't exist but we have PDFs, create it on the fly
    if status['status'] == 'completed' and status.get('pdf_paths'):
        if pdf_paths:
            zip_filename = f"{job_id}_all_modules.zip"
            zip_path = Path(app.config['OUTPUT_FOLDER']) / zip_filename
            
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for pdf_file in pdf_paths:
                    zipf.write(str(pdf_file), pdf_file.name)
            
            return send_file(
                str(zip_path),
                as_attachment=True,
                download_name=f"all_modules_{job_id[:8]}.zip",
                mimetype='application/zip'
            )
    
    return jsonify({
        'success': False,
        'error': 'PDFs not ready yet'
    }), 400


@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests to prevent 404 errors."""
    from flask import make_response
    response = make_response('', 204)
    response.headers['Content-Type'] = 'image/x-icon'
    return response


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'vimeo_token_configured': bool(os.getenv("VIMEO_TOKEN"))
    })


if __name__ == '__main__':
    # Check for Vimeo token
    if not os.getenv("VIMEO_TOKEN"):
        logger.warning("VIMEO_TOKEN not found in environment. Please set it in .env file.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

