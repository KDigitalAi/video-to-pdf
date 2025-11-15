#!/usr/bin/env python3
"""
Main entry point for the Vimeo Subtitle Automation Pipeline.

Usage:
    python run_pipeline.py manifest.csv
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.workflow.pipeline import Pipeline
from src.utils.logger import setup_logger

logger = setup_logger()


def main():
    """Main entry point for the pipeline."""
    # Load environment variables
    env_path = Path(".env")
    if not env_path.exists():
        logger.error(
            ".env file not found. Please create one based on .env.example\n"
            "Required: VIMEO_TOKEN=your_token_here"
        )
        sys.exit(1)
    
    load_dotenv()
    
    # Check for Vimeo token
    vimeo_token = os.getenv("VIMEO_TOKEN")
    if not vimeo_token:
        logger.error(
            "VIMEO_TOKEN not found in .env file.\n"
            "Please add: VIMEO_TOKEN=your_token_here"
        )
        sys.exit(1)
    
    # Get manifest path
    if len(sys.argv) < 2:
        logger.error("Usage: python run_pipeline.py <manifest.csv>")
        sys.exit(1)
    
    manifest_path = sys.argv[1]
    if not Path(manifest_path).exists():
        logger.error(f"Manifest file not found: {manifest_path}")
        sys.exit(1)
    
    # Initialize and run pipeline
    try:
        pipeline = Pipeline(vimeo_token)
        pipeline.run(manifest_path)
    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

