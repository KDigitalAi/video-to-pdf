"""
Logging utility for the Vimeo subtitle automation pipeline.
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(log_dir: str = None) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        log_dir: Directory to store log files (auto-detected if None)
        
    Returns:
        Configured logger instance
    """
    # Auto-detect log directory based on environment
    if log_dir is None:
        if os.getenv('VERCEL'):
            # Vercel environment - use /tmp for writable files
            log_dir = '/tmp/logs'
        else:
            # Local development
            log_dir = 'logs'
    
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("vimeo_pipeline")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    log_file = os.path.join(
        log_dir, 
        f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

