"""
Vimeo API client for fetching video information and subtitles.
"""
import os
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.logger import setup_logger

logger = setup_logger()


class VimeoClient:
    """
    Client for interacting with the Vimeo API.
    """
    
    BASE_URL = "https://api.vimeo.com"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Vimeo client.
        
        Args:
            token: Vimeo API token. If None, reads from VIMEO_TOKEN env var.
        """
        self.token = token or os.getenv("VIMEO_TOKEN")
        if not self.token:
            raise ValueError("Vimeo token is required. Set VIMEO_TOKEN in .env file.")
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.vimeo.*+json;version=3.4"
        })
    
    def get_text_tracks(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch text tracks (subtitles) for a video.
        
        Args:
            video_id: Vimeo video ID
            
        Returns:
            Dictionary with text tracks data, or None if error
        """
        url = f"{self.BASE_URL}/videos/{video_id}/texttracks"
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Fetching text tracks for video {video_id} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    tracks = data.get("data", [])
                    
                    if not tracks:
                        logger.warning(f"No text tracks found for video {video_id}")
                        return None
                    
                    # Find the first active track (preferably English)
                    # Priority: active English > active any > first track
                    active_tracks = [t for t in tracks if t.get("active", False)]
                    english_tracks = [t for t in active_tracks if t.get("language", "").startswith("en")]
                    
                    if english_tracks:
                        track = english_tracks[0]
                    elif active_tracks:
                        track = active_tracks[0]
                    else:
                        track = tracks[0]
                    
                    logger.info(f"Found text track for video {video_id}: {track.get('language', 'unknown')}")
                    return track
                
                elif response.status_code == 404:
                    logger.error(f"Video {video_id} not found")
                    return None
                
                elif response.status_code == 403:
                    logger.error(f"Access forbidden for video {video_id}. Check token permissions.")
                    return None
                
                else:
                    logger.warning(
                        f"Unexpected status code {response.status_code} for video {video_id}. "
                        f"Response: {response.text[:200]}"
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for video {video_id} (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                return None
        
        return None
    
    def download_vtt(self, vtt_url: str, save_path: str) -> bool:
        """
        Download a VTT subtitle file.
        
        Args:
            vtt_url: URL to the VTT file
            save_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Downloading VTT from {vtt_url} (attempt {attempt + 1})")
                response = self.session.get(vtt_url, timeout=30)
                
                if response.status_code == 200:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    # Save file
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Successfully downloaded VTT to {save_path}")
                    return True
                
                else:
                    logger.warning(
                        f"Failed to download VTT. Status code: {response.status_code}. "
                        f"URL: {vtt_url}"
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error downloading VTT (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                return False
        
        return False

