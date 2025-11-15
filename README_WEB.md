# Web Application - Vimeo Subtitle Automation

A simple web interface for the Vimeo Subtitle Automation Pipeline.

## Features

- 📤 **Upload CSV File**: Drag and drop or select your manifest CSV file
- ⚙️ **Automatic Processing**: Background processing of all videos
- 📊 **Real-time Progress**: Live progress updates during processing
- 📥 **Download PDF**: Download the generated PDF when ready

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Make sure your `.env` file has the Vimeo token:

```env
VIMEO_TOKEN=your_vimeo_token_here
```

### 3. Run the Web Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### 4. Open in Browser

Navigate to: **http://localhost:5000**

## Usage

1. **Upload CSV**: Click "Choose CSV File" and select your manifest CSV
2. **Process**: Click "Upload & Process" to start
3. **Wait**: The application will process all videos (this may take several minutes)
4. **Download**: Once complete, click "Download PDF" to get your file

## CSV Format

Your CSV file must have these columns:

- `course` - Course name
- `module` - Module name  
- `module_index` - Module number (for ordering)
- `video_title` - Video title
- `video_url` - Full Vimeo URL
- `video_index` - Video number within module

## Architecture

- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Backend**: Flask (Python)
- **Processing**: Background threads for async processing
- **Status**: Polling-based status updates

## API Endpoints

- `GET /` - Main page
- `POST /upload` - Upload CSV file
- `GET /status/<job_id>` - Get processing status
- `GET /download/<job_id>` - Download generated PDF
- `GET /health` - Health check

## Production Deployment

For production, use a proper WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or use Docker, or deploy to platforms like Heroku, AWS, etc.

## Troubleshooting

- **Upload fails**: Check file size (max 16MB) and CSV format
- **Processing fails**: Check Vimeo token in `.env` file
- **PDF not generated**: Check logs in `logs/` directory
- **Port already in use**: Change port in `app.py` (last line)

