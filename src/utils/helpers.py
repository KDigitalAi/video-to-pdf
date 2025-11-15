"""
Helper utility functions for the pipeline.
"""
import re
from pathlib import Path
from typing import Optional


def extract_video_id(video_url: str) -> Optional[str]:
    """
    Extract Vimeo video ID from URL.
    
    Supports formats:
    - https://vimeo.com/123456789
    - https://vimeo.com/123456789?param=value
    - vimeo.com/123456789
    
    Args:
        video_url: Vimeo video URL
        
    Returns:
        Video ID string or None if not found
    """
    patterns = [
        r'vimeo\.com/(\d+)',
        r'vimeo\.com/video/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    
    return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: Original filename string
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized


def ensure_directory(path: str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

