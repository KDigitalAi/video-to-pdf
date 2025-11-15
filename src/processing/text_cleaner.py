"""
Text cleaning utilities for processing subtitle text.
"""
import re
from typing import Optional

from src.utils.logger import setup_logger

logger = setup_logger()


def clean_subtitle_text(text: str) -> str:
    """
    Clean subtitle text by removing unwanted elements.
    
    Removes:
    - Speaker labels (e.g., "John:", "Speaker 1:")
    - Bracketed labels (e.g., "[Music]", "[Applause]", "[Laughter]")
    - Multiple consecutive newlines
    - Leading/trailing whitespace
    
    Args:
        text: Raw subtitle text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove speaker labels (pattern: word(s) followed by colon at start of line)
    # Examples: "John:", "Speaker 1:", "Narrator:"
    text = re.sub(r'^[A-Z][a-zA-Z\s]+:\s*', '', text, flags=re.MULTILINE)
    
    # Remove bracketed labels
    # Examples: [Music], [Applause], [Laughter], [Background Music]
    text = re.sub(r'\[[^\]]+\]', '', text)
    
    # Remove parentheses with common labels
    # Examples: (music), (applause), (laughter)
    common_labels = ['music', 'applause', 'laughter', 'background music', 'music playing']
    pattern = r'\(' + '|'.join(re.escape(label) for label in common_labels) + r'\)'
    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove timestamps that might have been missed (HH:MM:SS format)
    text = re.sub(r'\d{1,2}:\d{2}:\d{2}', '', text)
    
    # Remove cue identifiers (numbers at start of line)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    
    # Normalize whitespace
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines (3+) with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove lines that are only whitespace
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    text = '\n'.join(cleaned_lines)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def format_markdown_section(title: str, content: str, level: int = 1) -> str:
    """
    Format a section as markdown with proper headers.
    
    Args:
        title: Section title
        content: Section content
        level: Header level (1-6)
        
    Returns:
        Formatted markdown string
    """
    if not content.strip():
        return ""
    
    # Create header based on level
    header_prefix = "#" * level
    
    # Format the section
    section = f"\n{header_prefix} {title}\n\n{content}\n\n"
    
    return section

