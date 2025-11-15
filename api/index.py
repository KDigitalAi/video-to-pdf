"""
Vercel serverless function wrapper for Flask app.
"""
import os
import sys
from pathlib import Path

# Set Vercel environment flag
os.environ['VERCEL'] = '1'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Flask app
from app import app

# Vercel Python runtime handler
def handler(request):
    """
    Vercel serverless function handler.
    """
    return app(request.environ, lambda status, headers: None)

# Export app for Vercel
__all__ = ['app', 'handler']

