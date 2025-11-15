# Vimeo Subtitle Automation Pipeline

A complete, production-ready Python project that automates the entire workflow of downloading Vimeo video subtitles, cleaning the text, organizing by course/module/video, and generating PDF documents.

## Features

- ✅ Automatic Vimeo subtitle download via API
- ✅ VTT file parsing and text extraction
- ✅ Advanced text cleaning (removes timestamps, speaker labels, metadata)
- ✅ Organized markdown output per video/module/course
- ✅ PDF generation with clean formatting
- ✅ Retry logic and error handling
- ✅ Progress tracking with tqdm
- ✅ Comprehensive logging

## Project Structure

```
vimeo-subtitle-automation/
├── run_pipeline.py          # Main entry point
├── manifest.csv             # Input CSV with video information
├── README.md               # This file
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
│
├── src/
│   ├── api/
│   │   └── vimeo_client.py      # Vimeo API client
│   ├── processing/
│   │   ├── vtt_parser.py        # VTT file parser
│   │   ├── text_cleaner.py      # Text cleaning utilities
│   │   └── pdf_generator.py     # PDF generation
│   ├── workflow/
│   │   └── pipeline.py          # Main pipeline logic
│   └── utils/
│       ├── file_utils.py        # File operations
│       ├── logger.py            # Logging setup
│       └── helpers.py           # Helper functions
│
└── output/
    ├── raw_vtt/            # Downloaded VTT files
    ├── cleaned_markdown/   # Processed markdown files
    └── final_pdfs/         # Generated PDF files
```

## Installation

### 1. Prerequisites

- Python 3.10 or higher
- Pandoc (required for PDF generation)

#### Install Pandoc:

**Windows:**
```bash
choco install pandoc
```
Or download from: https://pandoc.org/installing.html

**macOS:**
```bash
brew install pandoc
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install pandoc
```

**Note:** You may also need LaTeX for PDF generation:
- Windows: Install MiKTeX or TeX Live
- macOS: `brew install --cask mactex`
- Ubuntu: `sudo apt-get install texlive-xetex`

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Vimeo API token:
```
VIMEO_TOKEN=your_vimeo_token_here
```

#### Getting a Vimeo API Token

1. Go to https://developer.vimeo.com/apps
2. Create a new app or use an existing one
3. Generate an access token with the following scopes:
   - `video` (read access to video information)
   - `private` (if videos are private)
4. Copy the token to your `.env` file

## Usage

### 1. Prepare Manifest CSV

Create a CSV file (`manifest.csv`) with the following columns:

- `course`: Course name
- `module`: Module name
- `module_index`: Module number (for ordering)
- `video_title`: Video title
- `video_url`: Full Vimeo URL (e.g., `https://vimeo.com/123456789`)
- `video_index`: Video number within module (for ordering)

**Example:**
```csv
course,module,module_index,video_title,video_url,video_index
Introduction to Python,Getting Started,1,Welcome to Python,https://vimeo.com/123456789,1
Introduction to Python,Getting Started,1,Installing Python,https://vimeo.com/123456790,2
Introduction to Python,Variables and Data Types,2,Understanding Variables,https://vimeo.com/123456791,1
```

### 2. Run the Pipeline

```bash
python run_pipeline.py manifest.csv
```

The pipeline will:
1. Process each video in the manifest
2. Download subtitles from Vimeo
3. Clean and organize the text
4. Generate one PDF per course

### 3. Output

- **Raw VTT files**: `output/raw_vtt/<course>/<module>/<video_id>.vtt`
- **Cleaned Markdown**: `output/cleaned_markdown/<course>/<module>/<video_title>.md`
- **Final PDFs**: `output/final_pdfs/<CourseName>.pdf`
- **Logs**: `logs/pipeline_YYYYMMDD_HHMMSS.log`
- **Failed videos**: `failed_videos.log` (if any)

## How It Works

### 1. Video Processing
- Extracts video ID from Vimeo URL
- Fetches text tracks via Vimeo API
- Downloads the VTT subtitle file
- Parses VTT to extract text content

### 2. Text Cleaning
- Removes timestamps
- Removes cue identifiers
- Removes speaker names (e.g., "John:")
- Removes bracketed labels (e.g., "[Music]", "[Applause]")
- Normalizes whitespace
- Collapses multiple empty lines

### 3. Organization
- Creates markdown files per video
- Combines videos into module sections
- Combines modules into course documents

### 4. PDF Generation
- Converts markdown to PDF using Pandoc
- Applies clean formatting with proper headers
- Generates one PDF per course

## Troubleshooting

### Vimeo API Issues

**Error: "Access forbidden" or "403"**
- Check that your Vimeo token has the correct permissions
- Ensure the token has access to the videos you're trying to process
- For private videos, make sure the token has `private` scope

**Error: "Video not found" or "404"**
- Verify the video URL is correct
- Check that the video exists and is accessible
- Ensure the video has subtitles/captions enabled

**Error: "No text tracks found"**
- The video may not have subtitles/captions
- Check the video settings on Vimeo to enable captions
- Some videos may only have auto-generated captions (may need to be enabled)

### Pandoc Issues

**Error: "Pandoc is not installed"**
- Install Pandoc following the instructions in the Installation section
- Verify installation: `pandoc --version`

**Error: PDF generation fails**
- Ensure LaTeX is installed (XeLaTeX is used for better Unicode support)
- Check that the markdown file is valid
- Review the logs for specific error messages

### General Issues

**Import errors**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using Python 3.10+

**File permission errors**
- Check that you have write permissions in the project directory
- Ensure output directories can be created

**Network/timeout errors**
- The pipeline includes retry logic (3 attempts)
- Check your internet connection
- Verify Vimeo API is accessible

## Configuration

### Retry Settings
Retry logic is built into the Vimeo client:
- Maximum 3 retry attempts
- Exponential backoff between retries
- Automatic retry on network errors and 5xx status codes

### Logging
Logs are written to:
- Console (stdout)
- File: `logs/pipeline_YYYYMMDD_HHMMSS.log`

Log level: INFO (can be modified in `src/utils/logger.py`)

## Development

### Project Structure
- **Modular design**: Each component is in its own module
- **Error handling**: Comprehensive try/except blocks
- **Logging**: Detailed logging throughout the pipeline
- **Type hints**: Type annotations for better code clarity

### Extending the Pipeline

To add new features:
1. Add new modules in `src/processing/` for new processing steps
2. Modify `src/workflow/pipeline.py` to integrate new steps
3. Update `requirements.txt` if new dependencies are needed

## License

This project is provided as-is for automation purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `logs/` directory
3. Check `failed_videos.log` for specific video errors

## Example Workflow

```bash
# 1. Setup
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Vimeo token

# 2. Prepare manifest
# Edit manifest.csv with your course data

# 3. Run pipeline
python run_pipeline.py manifest.csv

# 4. Check output
ls output/final_pdfs/  # Your PDFs are here!
```

---

**Note:** This pipeline processes videos sequentially. For large batches (100+ videos), processing may take several hours depending on network speed and API rate limits.

