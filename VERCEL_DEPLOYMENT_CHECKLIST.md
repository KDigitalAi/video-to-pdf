# Vercel Deployment Checklist

## ✅ Files Required for Vercel Deployment

### 1. **api/index.py** (Entry Point)
- ✅ Must import and expose Flask `app` variable
- ✅ Current structure: Imports `app` from `app.py` in parent directory
- ✅ Location: `api/index.py`

### 2. **vercel.json** (Configuration)
- ✅ Specifies Python runtime (python3.10)
- ✅ Configures function settings (maxDuration, memory)
- ✅ Sets up routes for static files and API
- ✅ Location: Root directory

### 3. **requirements.txt** (Dependencies)
- ✅ Lists all Python dependencies
- ✅ Must be at root directory
- ✅ Current location: ✅ Root directory

### 4. **app.py** (Flask Application)
- ✅ Contains Flask app instance
- ✅ Location: Root directory
- ✅ Current structure: ✅ Correct

## 🔍 What Vercel Looks For

1. **Python Detection**: 
   - Looks for `requirements.txt` at root
   - Detects Python files in `api/` directory
   - Uses `vercel.json` for configuration

2. **Flask App Detection**:
   - Looks for `app` variable in entry point (`api/index.py`)
   - Can auto-detect from `app.py`, `index.py`, or `server.py` at root
   - Our setup: `api/index.py` imports from `app.py` ✅

3. **Static Files**:
   - `static/` folder for CSS/JS
   - `templates/` folder for HTML
   - Both are configured in `vercel.json` routes ✅

## 📋 Current Configuration Status

### vercel.json
```json
{
  "functions": {
    "api/index.py": {
      "runtime": "python3.10",
      "maxDuration": 60,
      "memory": 1024
    }
  },
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/api/index.py"
    }
  ]
}
```

### api/index.py
- ✅ Imports Flask app from parent directory
- ✅ Sets VERCEL environment variable
- ✅ Adds parent directory to Python path
- ✅ Exports `app` variable (via import)

## 🚨 Common Deployment Issues

### Issue 1: Deployment Not Triggering
**Possible Causes:**
- GitHub webhook not configured
- Wrong branch configured in Vercel
- Vercel project not connected to GitHub repo

**Solution:**
1. Go to Vercel Dashboard → Project Settings → Git
2. Verify GitHub integration is connected
3. Check which branch triggers deployments
4. Ensure you're pushing to the correct branch

### Issue 2: Build Fails
**Possible Causes:**
- Missing dependencies in requirements.txt
- Python version mismatch
- Import errors

**Solution:**
1. Check build logs in Vercel dashboard
2. Verify all dependencies are in requirements.txt
3. Test locally: `vercel dev`

### Issue 3: Runtime Errors
**Possible Causes:**
- Missing environment variables
- File path issues
- Module import errors

**Solution:**
1. Set environment variables in Vercel dashboard
2. Check that paths use `/tmp` on Vercel
3. Verify all imports work correctly

## ✅ Verification Steps

1. **Local Test**:
   ```bash
   vercel dev
   ```
   This simulates Vercel environment locally

2. **Check File Structure**:
   ```
   project-root/
   ├── api/
   │   └── index.py          ✅ Entry point
   ├── app.py                ✅ Flask app
   ├── requirements.txt       ✅ Dependencies
   ├── vercel.json           ✅ Configuration
   ├── static/               ✅ Static files
   └── templates/            ✅ HTML templates
   ```

3. **Verify Git Integration**:
   - Check Vercel dashboard → Settings → Git
   - Ensure repository is connected
   - Verify branch configuration

4. **Check Deployment Logs**:
   - Go to Vercel dashboard → Deployments
   - Click on latest deployment
   - Review build and runtime logs

## 🎯 Next Steps

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Fix Vercel deployment configuration"
   git push origin main  # or your configured branch
   ```

2. **Check Vercel Dashboard**:
   - Go to https://vercel.com/dashboard
   - Check if deployment is triggered
   - Review build logs for errors

3. **Manual Deploy (if needed)**:
   ```bash
   vercel --prod
   ```

## 📝 Notes

- Vercel auto-detects Python from `requirements.txt`
- Flask apps need `app` variable exposed in entry point
- Static files must be in `static/` folder
- Templates must be in `templates/` folder
- Environment variables must be set in Vercel dashboard

