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

# Vercel's @vercel/python automatically detects Flask/WSGI apps
# The app variable must be in module scope for Vercel to detect it

