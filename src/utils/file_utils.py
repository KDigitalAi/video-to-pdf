"""
File utility functions for reading and writing files.
"""
import os
from pathlib import Path
from typing import Optional

from src.utils.helpers import ensure_directory, sanitize_filename


def write_markdown_file(filepath: str, content: str) -> bool:
    """
    Write content to a markdown file.
    
    Args:
        filepath: Full path to the markdown file
        content: Content to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_directory(os.path.dirname(filepath))
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error writing markdown file {filepath}: {e}")
        return False


def write_text_file(filepath: str, content: str) -> bool:
    """
    Write content to a text file.
    
    Args:
        filepath: Full path to the text file
        content: Content to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_directory(os.path.dirname(filepath))
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error writing text file {filepath}: {e}")
        return False


def read_file(filepath: str) -> Optional[str]:
    """
    Read content from a file.
    
    Args:
        filepath: Full path to the file
        
    Returns:
        File content as string, or None if error
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return None


def append_to_file(filepath: str, content: str) -> bool:
    """
    Append content to a file.
    
    Args:
        filepath: Full path to the file
        content: Content to append
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_directory(os.path.dirname(filepath))
        
        # Append to file
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error appending to file {filepath}: {e}")
        return False


def get_output_paths(course: str, module: str = None, video_title: str = None, output_base: str = None) -> dict:
    """
    Generate standardized output paths for different file types.
    
    Args:
        course: Course name
        module: Module name (optional)
        video_title: Video title (optional)
        output_base: Base output directory (defaults to "output" or "/tmp/output" on Vercel)
        
    Returns:
        Dictionary with paths for raw_vtt, cleaned_markdown, and final_pdfs
    """
    import os
    if output_base:
        base_output = Path(output_base)
    elif os.getenv('VERCEL'):
        base_output = Path("/tmp/output")
    else:
        base_output = Path("output")
    
    # Sanitize names
    safe_course = sanitize_filename(course)
    safe_module = sanitize_filename(module) if module else None
    safe_video = sanitize_filename(video_title) if video_title else None
    
    paths = {
        "raw_vtt": base_output / "raw_vtt",
        "cleaned_markdown": base_output / "cleaned_markdown",
        "final_pdfs": base_output / "final_pdfs"
    }
    
    if safe_course:
        paths["raw_vtt"] = paths["raw_vtt"] / safe_course
        paths["cleaned_markdown"] = paths["cleaned_markdown"] / safe_course
    
    if safe_module:
        paths["raw_vtt"] = paths["raw_vtt"] / safe_module
        paths["cleaned_markdown"] = paths["cleaned_markdown"] / safe_module
    
    return paths

