# Deploying to Vercel

This guide will help you deploy the Vimeo Subtitle Automation application to Vercel.

## Prerequisites

1. A Vercel account (sign up at https://vercel.com)
2. Vercel CLI installed (optional, for CLI deployment)
3. Your Vimeo API token

## Important Notes

⚠️ **Execution Time Limits:**
- Vercel Hobby plan: 10 seconds max execution time
- Vercel Pro plan: 60 seconds max execution time
- Video processing can take much longer than this

**Recommendation:** For production use with many videos, consider:
- Using Vercel's Background Functions (if available)
- Using a queue system (e.g., Redis Queue, Celery)
- Deploying to a platform with longer execution times (Railway, Render, Fly.io)

## Deployment Steps

### Method 1: Using Vercel Dashboard (Recommended)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Import Project on Vercel**
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Vercel will auto-detect Python

3. **Configure Environment Variables**
   - In Vercel dashboard, go to Project Settings → Environment Variables
   - Add the following:
     - `VIMEO_TOKEN`: Your Vimeo API token
     - `SECRET_KEY`: A random secret key for Flask sessions (optional)

4. **Deploy**
   - Click "Deploy"
   - Wait for build to complete

### Method 2: Using Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel
   ```

4. **Set Environment Variables**
   ```bash
   vercel env add VIMEO_TOKEN
   vercel env add SECRET_KEY
   ```

5. **Redeploy with environment variables**
   ```bash
   vercel --prod
   ```

## Configuration Files

The following files are configured for Vercel:

- **`vercel.json`**: Vercel configuration
- **`api/index.py`**: Serverless function entry point
- **`.vercelignore`**: Files to exclude from deployment

## Environment Variables

Set these in Vercel Dashboard → Settings → Environment Variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `VIMEO_TOKEN` | Your Vimeo API access token | Yes |
| `SECRET_KEY` | Flask session secret key | No (has default) |

## File System Considerations

- Vercel uses `/tmp` for writable files
- All file operations are automatically routed to `/tmp` when `VERCEL` environment variable is set
- Files in `/tmp` are ephemeral and cleared between function invocations

## Limitations

1. **Execution Time**: Limited to 10s (Hobby) or 60s (Pro)
2. **File Persistence**: Files in `/tmp` are not persistent across invocations
3. **Background Processing**: Threading works but may be interrupted if function times out
4. **Memory**: Limited by Vercel plan

## Troubleshooting

### Build Fails

- Check that all dependencies are in `requirements.txt`
- Ensure Python version is compatible (3.10+)
- Check build logs in Vercel dashboard

### Function Timeout

- Processing too many videos at once
- Consider processing videos in batches
- Use a queue system for long-running tasks

### Files Not Found

- Ensure paths use `/tmp` on Vercel
- Check that directories are created before use
- Verify file permissions

### Environment Variables Not Working

- Redeploy after adding environment variables
- Check variable names match exactly
- Use Vercel CLI to verify: `vercel env ls`

## Testing Locally with Vercel

You can test the Vercel configuration locally:

```bash
vercel dev
```

This will simulate the Vercel environment locally.

## Production Recommendations

For production use, consider:

1. **Use a Queue System**: Process videos asynchronously
2. **Use External Storage**: Store files in S3, Cloudinary, or similar
3. **Use a Database**: Store job status in a database instead of in-memory
4. **Monitor Execution Time**: Add logging to track processing times
5. **Error Handling**: Implement retry logic for failed videos

## Alternative Deployment Options

If Vercel's limitations are too restrictive:

- **Railway**: No execution time limits, easy deployment
- **Render**: Similar to Heroku, supports long-running processes
- **Fly.io**: Good for Python apps with file operations
- **AWS Lambda + S3**: Serverless with external storage
- **Google Cloud Run**: Container-based, flexible execution time

