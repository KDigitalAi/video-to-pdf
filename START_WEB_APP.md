# 🚀 Quick Start - Web Application

## Step 1: Install Flask

```bash
pip install flask werkzeug
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

## Step 2: Ensure .env is Configured

Make sure your `.env` file has:
```
VIMEO_TOKEN=your_vimeo_token_here
```

## Step 3: Run the Web Application

```bash
python app.py
```

## Step 4: Open Browser

Navigate to: **http://localhost:5000**

## Usage

1. Click "Choose CSV File" and select your manifest CSV
2. Click "Upload & Process"
3. Wait for processing (progress bar will update)
4. Click "Download PDF" when ready

## Features

✅ Simple drag-and-drop interface  
✅ Real-time progress updates  
✅ Background processing  
✅ Automatic PDF generation  
✅ One-click download  

## Troubleshooting

- **Port 5000 in use?** Edit `app.py` last line to change port
- **Upload fails?** Check CSV format and file size (max 16MB)
- **Processing fails?** Check Vimeo token in `.env` file

