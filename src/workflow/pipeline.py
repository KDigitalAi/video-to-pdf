"""
Main pipeline workflow for processing Vimeo videos to PDFs.
"""
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm

from src.api.vimeo_client import VimeoClient
from src.processing.vtt_parser import parse_vtt_to_text
from src.processing.text_cleaner import clean_subtitle_text, format_markdown_section
from src.processing.pdf_generator import markdown_string_to_pdf
from src.utils.file_utils import (
    write_markdown_file,
    get_output_paths
)
from src.utils.helpers import extract_video_id, sanitize_filename
from src.utils.logger import setup_logger

logger = setup_logger()


class Pipeline:
    """
    Main pipeline for processing Vimeo videos to course PDFs.
    """
    
    def __init__(self, vimeo_token: str, output_base: str = None):
        """
        Initialize the pipeline.
        
        Args:
            vimeo_token: Vimeo API token
            output_base: Base output directory (defaults to "output" or "/tmp/output" on Vercel)
        """
        self.vimeo_client = VimeoClient(vimeo_token)
        self.failed_videos = []
        
        # Determine output base path
        if output_base:
            self.output_base = Path(output_base)
        elif os.getenv('VERCEL'):
            self.output_base = Path("/tmp/output")
        else:
            self.output_base = Path("output")
        
        # Ensure output directories exist
        (self.output_base / "raw_vtt").mkdir(parents=True, exist_ok=True)
        (self.output_base / "cleaned_markdown").mkdir(parents=True, exist_ok=True)
        (self.output_base / "final_pdfs").mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)
    
    def process_video(
        self,
        video_id: str,
        video_title: str,
        course: str,
        module: str
    ) -> Optional[str]:
        """
        Process a single video: download VTT, parse, clean, and save markdown.
        
        Args:
            video_id: Vimeo video ID
            video_title: Video title
            course: Course name
            module: Module name
            
        Returns:
            Path to cleaned markdown file, or None if failed
        """
        try:
            # Get output paths
            paths = get_output_paths(course, module, video_title, output_base=str(self.output_base))
            
            # Step 1: Get text tracks from Vimeo API
            logger.info(f"Fetching text tracks for video: {video_title} ({video_id})")
            track_data = self.vimeo_client.get_text_tracks(video_id)
            
            if not track_data:
                raise Exception(f"No text tracks found for video {video_id}")
            
            # Step 2: Download VTT file
            vtt_url = track_data.get("link")
            if not vtt_url:
                raise Exception(f"No VTT URL found in track data for video {video_id}")
            
            # Save VTT file
            vtt_filename = f"{video_id}.vtt"
            vtt_filepath = paths["raw_vtt"] / vtt_filename
            
            logger.info(f"Downloading VTT file for video: {video_title}")
            if not self.vimeo_client.download_vtt(vtt_url, str(vtt_filepath)):
                raise Exception(f"Failed to download VTT file for video {video_id}")
            
            # Step 3: Parse VTT to text
            logger.info(f"Parsing VTT file for video: {video_title}")
            raw_text = parse_vtt_to_text(str(vtt_filepath))
            
            if not raw_text:
                raise Exception(f"Failed to parse VTT file for video {video_id}")
            
            # Step 4: Clean text
            logger.info(f"Cleaning text for video: {video_title}")
            cleaned_text = clean_subtitle_text(raw_text)
            
            if not cleaned_text.strip():
                logger.warning(f"Cleaned text is empty for video {video_id}")
                cleaned_text = f"[No subtitle content available for {video_title}]"
            
            # Step 5: Save cleaned markdown
            markdown_filename = f"{sanitize_filename(video_title)}.md"
            markdown_filepath = paths["cleaned_markdown"] / markdown_filename
            
            # Format as markdown section
            markdown_content = format_markdown_section(
                f"Video: {video_title}",
                cleaned_text,
                level=3
            )
            
            if not write_markdown_file(str(markdown_filepath), markdown_content):
                raise Exception(f"Failed to write markdown file for video {video_id}")
            
            logger.info(f"Successfully processed video: {video_title}")
            return str(markdown_filepath)
            
        except Exception as e:
            logger.error(f"Error processing video {video_id} ({video_title}): {e}")
            self.failed_videos.append({
                "video_id": video_id,
                "video_title": video_title,
                "course": course,
                "module": module,
                "error": str(e)
            })
            return None
    
    def process_course(self, course_data: pd.DataFrame) -> bool:
        """
        Process all videos in a course and generate final PDF.
        
        Args:
            course_data: DataFrame containing all videos for a course
            
        Returns:
            True if successful, False otherwise
        """
        course_name = course_data.iloc[0]["course"]
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Course: {course_name}")
        logger.info(f"{'='*60}")
        
        # Store module markdowns
        course_markdown_parts = []
        course_markdown_parts.append(f"# {course_name}\n\n")
        
        # Process each module - SORT BY MODULE_INDEX FIRST
        # Group by module name first, then get module_index for sorting
        modules_list = []
        for module_name, module_group in course_data.groupby("module"):
            # Get module_index from first row (all rows in a module should have same index)
            module_index_val = module_group.iloc[0]["module_index"]
            module_index = int(module_index_val) if pd.notna(module_index_val) else 1
            
            modules_list.append({
                "module_name": module_name,
                "module_index": module_index,
                "module_group": module_group
            })
        
        # Sort modules by module_index (ascending order)
        modules_list.sort(key=lambda x: x["module_index"])
        
        # Process each module in sorted order
        for module_info in modules_list:
            module_name = module_info["module_name"]
            module_index = module_info["module_index"]
            module_group = module_info["module_group"]
            
            logger.info(f"\nProcessing Module {module_index}: {module_name}")
            
            module_markdown_parts = []
            module_markdown_parts.append(f"\n## Module {module_index}: {module_name}\n\n")
            
            # Process each video in module, sorted by video_index
            module_videos = module_group.sort_values("video_index")
            
            for _, row in tqdm(module_videos.iterrows(), 
                             total=len(module_videos), 
                             desc=f"Module {module_index}"):
                video_title = row["video_title"]
                video_url = row["video_url"]
                
                # Extract video ID
                video_id = extract_video_id(video_url)
                if not video_id:
                    logger.error(f"Could not extract video ID from URL: {video_url}")
                    self.failed_videos.append({
                        "video_id": "unknown",
                        "video_title": video_title,
                        "course": course_name,
                        "module": module_name,
                        "error": "Could not extract video ID from URL"
                    })
                    continue
                
                # Process video
                markdown_path = self.process_video(
                    video_id,
                    video_title,
                    course_name,
                    module_name
                )
                
                if markdown_path:
                    # Read the markdown content
                    with open(markdown_path, 'r', encoding='utf-8') as f:
                        video_markdown = f.read()
                    module_markdown_parts.append(video_markdown)
            
            # Combine module videos
            module_markdown = "".join(module_markdown_parts)
            course_markdown_parts.append(module_markdown)
        
        # Combine all modules into course markdown
        course_markdown = "".join(course_markdown_parts)
        
        # Save course markdown
        course_markdown_path = self.output_base / "cleaned_markdown" / f"{sanitize_filename(course_name)}.md"
        write_markdown_file(str(course_markdown_path), course_markdown)
        
        # Generate PDF
        logger.info(f"\nGenerating PDF for course: {course_name}")
        pdf_path = self.output_base / "final_pdfs" / f"{sanitize_filename(course_name)}.pdf"
        
        success = markdown_string_to_pdf(
            course_markdown,
            str(pdf_path),
            title=course_name
        )
        
        if success:
            logger.info(f"✓ Successfully generated PDF: {pdf_path}")
        else:
            logger.error(f"✗ Failed to generate PDF: {pdf_path}")
        
        return success
    
    def run(self, manifest_path: str) -> None:
        """
        Run the complete pipeline on a manifest CSV file.
        
        Args:
            manifest_path: Path to manifest CSV file
        """
        logger.info("Starting Vimeo Subtitle Automation Pipeline")
        logger.info(f"Loading manifest: {manifest_path}")
        
        # Load manifest
        try:
            df = pd.read_csv(manifest_path)
            required_columns = ["course", "module", "module_index", "video_title", "video_url", "video_index"]
            
            # Validate columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Fill missing module_index values
            # Convert to numeric first
            df['module_index'] = pd.to_numeric(df['module_index'], errors='coerce')
            
            # For each course, assign module indices sequentially
            # Preserve existing indices where set, fill missing ones
            for course_name in df['course'].unique():
                course_mask = df['course'] == course_name
                course_df = df[course_mask]
                
                # Get unique modules in order
                unique_modules = course_df['module'].unique()
                
                # Assign module indices if missing
                for idx, module_name in enumerate(unique_modules, start=1):
                    module_mask = (df['course'] == course_name) & (df['module'] == module_name)
                    # If module_index is NaN for this module, assign sequential index
                    if df.loc[module_mask, 'module_index'].isna().all():
                        df.loc[module_mask, 'module_index'] = idx
                    else:
                        # Use the first non-null value, or idx if all are null
                        existing_idx = df.loc[module_mask, 'module_index'].dropna()
                        if len(existing_idx) > 0:
                            df.loc[module_mask, 'module_index'] = existing_idx.iloc[0]
                        else:
                            df.loc[module_mask, 'module_index'] = idx
            
            # Fill missing video_index values within each module
            # Convert to numeric first
            df['video_index'] = pd.to_numeric(df['video_index'], errors='coerce')
            
            # For each module, assign sequential video indices
            for (course_name, module_name), module_group in df.groupby(['course', 'module']):
                mask = (df['course'] == course_name) & (df['module'] == module_name)
                # Assign sequential indices starting from 1
                df.loc[mask, 'video_index'] = range(1, len(module_group) + 1)
            
            # Ensure all are integers
            df['module_index'] = df['module_index'].fillna(1).astype(int)
            df['video_index'] = df['video_index'].fillna(1).astype(int)
            
            logger.info(f"Loaded {len(df)} video entries")
            logger.info(f"Found {df['module'].nunique()} unique modules")
            
        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
            return
        
        # Process each course
        courses = df.groupby("course")
        total_courses = len(courses)
        
        logger.info(f"Found {total_courses} courses to process")
        
        for course_name, course_data in courses:
            try:
                self.process_course(course_data)
            except Exception as e:
                logger.error(f"Error processing course {course_name}: {e}")
        
        # Log failed videos
        if self.failed_videos:
            logger.warning(f"\n{len(self.failed_videos)} videos failed to process")
            failed_log_path = "failed_videos.log"
            
            with open(failed_log_path, 'w', encoding='utf-8') as f:
                f.write("Failed Videos Log\n")
                f.write("=" * 60 + "\n\n")
                for failed in self.failed_videos:
                    f.write(f"Video ID: {failed['video_id']}\n")
                    f.write(f"Video Title: {failed['video_title']}\n")
                    f.write(f"Course: {failed['course']}\n")
                    f.write(f"Module: {failed['module']}\n")
                    f.write(f"Error: {failed['error']}\n")
                    f.write("-" * 60 + "\n")
            
            logger.info(f"Failed videos logged to: {failed_log_path}")
        else:
            logger.info("\n✓ All videos processed successfully!")
        
        logger.info("\nPipeline completed!")

