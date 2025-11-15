"""
VTT (WebVTT) file parser for extracting clean text from subtitle files.
"""
from typing import Optional
import webvtt

from src.utils.logger import setup_logger

logger = setup_logger()


def parse_vtt_to_text(vtt_filepath: str) -> Optional[str]:
    """
    Parse a VTT file and extract clean text without timestamps.
    
    Args:
        vtt_filepath: Path to the VTT file
        
    Returns:
        Clean text string, or None if error
    """
    try:
        # Read and parse VTT file
        vtt = webvtt.read(vtt_filepath)
        
        # Extract text from all cues
        text_lines = []
        for cue in vtt:
            # Get the text content, removing any HTML tags
            text = cue.text.strip()
            
            # Skip empty cues
            if not text:
                continue
            
            # Remove HTML tags if present
            import re
            text = re.sub(r'<[^>]+>', '', text)
            
            # Add to lines
            text_lines.append(text)
        
        # Join all lines with newlines
        full_text = '\n'.join(text_lines)
        
        logger.info(f"Successfully parsed VTT file: {vtt_filepath} ({len(text_lines)} cues)")
        return full_text
        
    except FileNotFoundError:
        logger.error(f"VTT file not found: {vtt_filepath}")
        return None
    except Exception as e:
        logger.error(f"Error parsing VTT file {vtt_filepath}: {e}")
        return None

