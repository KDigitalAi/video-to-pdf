"""
PDF generator using Pandoc to convert Markdown to PDF.
Falls back to ReportLab if Pandoc is not available.
"""
import os
import subprocess
import re
from typing import Optional

from src.utils.logger import setup_logger
from src.utils.helpers import ensure_directory

logger = setup_logger()

# Try to import optional dependencies
try:
    import pypandoc
    PYPANDOC_AVAILABLE = True
except ImportError:
    PYPANDOC_AVAILABLE = False

# Markdown library (always try to import)
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# ReportLab (pure Python, works on Windows)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _escape_for_reportlab(text: str) -> str:
    """
    Escape special characters for ReportLab Paragraph.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    # ReportLab uses XML-like format, so we need to escape properly
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def _process_markdown_for_reportlab(text: str) -> str:
    """
    Convert markdown formatting to ReportLab XML format.
    
    Args:
        text: Markdown text
        
    Returns:
        ReportLab XML formatted text
    """
    # First escape special characters
    text = _escape_for_reportlab(text)
    
    # Convert markdown bold **text** to <b>text</b>
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)
    
    # Convert markdown italic *text* to <i>text</i> (but not if it's part of **)
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<i>\1</i>', text)
    
    # Convert markdown links [text](url) to just text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    return text


def check_pandoc_installed() -> bool:
    """
    Check if Pandoc is installed on the system.
    
    Returns:
        True if Pandoc is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def markdown_to_pdf(
    markdown_filepath: str,
    output_filepath: str,
    title: Optional[str] = None
) -> bool:
    """
    Convert a Markdown file to PDF using Pandoc.
    
    Args:
        markdown_filepath: Path to input Markdown file
        output_filepath: Path to output PDF file
        title: Optional title for the PDF document
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if Pandoc is installed
        if not check_pandoc_installed():
            logger.error(
                "Pandoc is not installed. Please install it:\n"
                "  Windows: choco install pandoc\n"
                "  macOS: brew install pandoc\n"
                "  Ubuntu: sudo apt-get install pandoc"
            )
            return False
        
        # Ensure output directory exists
        ensure_directory(os.path.dirname(output_filepath))
        
        # Prepare Pandoc options
        extra_args = [
            '--pdf-engine=xelatex',  # Use XeLaTeX for better Unicode support
            '--variable=geometry:margin=1in',
            '--variable=fontsize:11pt',
            '--variable=linestretch:1.2',
        ]
        
        if title:
            extra_args.append(f'--variable=title:{title}')
        
        # Convert to PDF
        logger.info(f"Converting {markdown_filepath} to PDF...")
        
        output = pypandoc.convert_file(
            markdown_filepath,
            'pdf',
            format='markdown',
            outputfile=output_filepath,
            extra_args=extra_args
        )
        
        if os.path.exists(output_filepath):
            logger.info(f"Successfully generated PDF: {output_filepath}")
            return True
        else:
            logger.error(f"PDF generation failed. Output file not created: {output_filepath}")
            return False
            
    except Exception as e:
        logger.error(f"Error converting Markdown to PDF: {e}")
        return False


def markdown_string_to_pdf_reportlab(
    markdown_content: str,
    output_filepath: str,
    title: Optional[str] = None
) -> bool:
    """
    Convert Markdown to PDF using ReportLab (pure Python, works on Windows).
    
    Args:
        markdown_content: Markdown content as string
        output_filepath: Path to output PDF file
        title: Optional title for the PDF document
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not REPORTLAB_AVAILABLE:
            return False
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#2c3e50',
            spaceAfter=20,
            alignment=TA_LEFT
        )
        
        h1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=22,
            textColor='#2c3e50',
            spaceAfter=20,
            spaceBefore=40,
            borderWidth=0,
            borderPadding=5,
            backColor='#ecf0f1'
        )
        
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=18,
            textColor='#34495e',
            spaceAfter=12,
            spaceBefore=25,
            borderWidth=0,
            borderPadding=3
        )
        
        h3_style = ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=14,
            textColor='#555',
            spaceAfter=8,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=6,
            textColor='#333'
        )
        
        # Add title if provided
        if title:
            elements.append(Paragraph(title, title_style))
            elements.append(Spacer(1, 0.2*inch))
        
        # Parse markdown content line by line
        lines = markdown_content.split('\n')
        i = 0
        prev_was_module = False  # Track if previous line was a module header
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip empty lines (but add small spacing)
            if not line:
                if i > 0 and i < len(lines) - 1:  # Don't add space at start/end
                    elements.append(Spacer(1, 0.03*inch))
                i += 1
                continue
            
            # Parse headers
            if line.startswith('# '):
                # Course title - already handled above
                text = line[2:].strip()
                if text and text != title:  # Only add if different from title
                    elements.append(Paragraph(_escape_for_reportlab(text), h1_style))
            elif line.startswith('## '):
                # Module header - add page break before (except first module)
                text = line[3:].strip()
                if text:
                    if prev_was_module or len(elements) > 2:  # Not the first module
                        elements.append(PageBreak())
                    elements.append(Spacer(1, 0.1*inch))
                    elements.append(Paragraph(_escape_for_reportlab(text), h1_style))
                    elements.append(Spacer(1, 0.15*inch))
                    prev_was_module = True
            elif line.startswith('### '):
                # Video header
                text = line[4:].strip()
                if text:
                    elements.append(Spacer(1, 0.1*inch))
                    elements.append(Paragraph(_escape_for_reportlab(text), h2_style))
                    elements.append(Spacer(1, 0.08*inch))
                    prev_was_module = False
            elif line.startswith('#### '):
                # Sub-video header
                text = line[5:].strip()
                if text:
                    elements.append(Spacer(1, 0.05*inch))
                    elements.append(Paragraph(_escape_for_reportlab(text), h3_style))
                    elements.append(Spacer(1, 0.05*inch))
                    prev_was_module = False
            else:
                # Regular paragraph - process markdown formatting
                text = _process_markdown_for_reportlab(line)
                if text:
                    elements.append(Paragraph(text, normal_style))
                    prev_was_module = False
            
            i += 1
        
        # Build PDF
        logger.info(f"Converting Markdown to PDF using ReportLab: {output_filepath}")
        doc.build(elements)
        
        if os.path.exists(output_filepath):
            logger.info(f"Successfully generated PDF using ReportLab: {output_filepath}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Error converting Markdown to PDF with ReportLab: {e}")
        import traceback
        traceback.print_exc()
        return False


def markdown_string_to_pdf(
    markdown_content: str,
    output_filepath: str,
    title: Optional[str] = None
) -> bool:
    """
    Convert a Markdown string directly to PDF.
    Tries Pandoc first, falls back to ReportLab if Pandoc is not available.
    
    Args:
        markdown_content: Markdown content as string
        output_filepath: Path to output PDF file
        title: Optional title for the PDF document
        
    Returns:
        True if successful, False otherwise
    """
    # Ensure output directory exists
    ensure_directory(os.path.dirname(output_filepath))
    
    # Try Pandoc first (better quality)
    if PYPANDOC_AVAILABLE and check_pandoc_installed():
        try:
            # Prepare Pandoc options
            extra_args = [
                '--pdf-engine=xelatex',
                '--variable=geometry:margin=1in',
                '--variable=fontsize:11pt',
                '--variable=linestretch:1.2',
            ]
            
            if title:
                extra_args.append(f'--variable=title:{title}')
            
            # Convert to PDF
            logger.info(f"Converting Markdown content to PDF using Pandoc: {output_filepath}")
            
            output = pypandoc.convert_text(
                markdown_content,
                'pdf',
                format='markdown',
                outputfile=output_filepath,
                extra_args=extra_args
            )
            
            if os.path.exists(output_filepath):
                logger.info(f"Successfully generated PDF using Pandoc: {output_filepath}")
                return True
        except Exception as e:
            logger.warning(f"Pandoc conversion failed: {e}. Trying fallback method...")
    
    # Fallback to ReportLab (pure Python, works on Windows)
    if REPORTLAB_AVAILABLE:
        logger.info("Pandoc not available. Using ReportLab fallback...")
        return markdown_string_to_pdf_reportlab(markdown_content, output_filepath, title)
    else:
        logger.error(
            "Neither Pandoc nor ReportLab is available.\n"
            "Install Pandoc:\n"
            "  Windows: Download from https://pandoc.org/installing.html\n"
            "  Or install ReportLab: pip install reportlab\n"
            "  Then run: pip install -r requirements.txt"
        )
        return False

