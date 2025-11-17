"""
Flask web application for Vimeo Subtitle Automation Pipeline.
"""
import os
import uuid
import time
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


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
            'error': None
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
        pdf_files = []
        
        # Wait a bit for PDFs to be written
        time.sleep(2)
        
        for pdf_file in Path(app.config['OUTPUT_FOLDER']).glob('*.pdf'):
            # Check if file was modified after job started (or within last 5 minutes)
            if pdf_file.stat().st_mtime >= (job_start_time - 300):
                pdf_files.append(pdf_file)
        
        if pdf_files:
            # Sort by modification time to get all PDFs
            pdf_files.sort(key=lambda p: p.stat().st_mtime)
            
            # Create ZIP file containing all PDFs
            zip_filename = f"{job_id}_all_modules.zip"
            zip_path = Path(app.config['OUTPUT_FOLDER']) / zip_filename
            
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for pdf_file in pdf_files:
                    zipf.write(str(pdf_file), pdf_file.name)
            
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


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing."""
    # Check if Vimeo token is configured
    vimeo_token = os.getenv("VIMEO_TOKEN")
    if not vimeo_token:
        return jsonify({
            'success': False,
            'error': 'VIMEO_TOKEN not configured. Please set it in .env file.'
        }), 400
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file uploaded'
        }), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    # Check file extension
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': 'Invalid file type. Please upload a CSV file.'
        }), 400
    
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = Path(app.config['UPLOAD_FOLDER']) / f"{job_id}_{filename}"
        file.save(str(filepath))
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_pipeline_async,
            args=(job_id, str(filepath), vimeo_token)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'File uploaded successfully. Processing started...'
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
        'error': status.get('error')
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
    
    # Fallback: if ZIP doesn't exist but we have PDFs, create it on the fly
    if status['status'] == 'completed' and status.get('pdf_paths'):
        pdf_paths = [Path(p) for p in status['pdf_paths'] if Path(p).exists()]
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

