# Vercel Deployment Trigger Guide

## 🚨 Issue: Deployment Not Triggering

If deployments are not being triggered automatically, follow these steps:

## Step 1: Check Vercel Project Settings

1. Go to **Vercel Dashboard** → Your Project → **Settings** → **Git**

2. Verify the following:
   - ✅ **Repository** is connected to: `KDigitalAi/video-to-pdf`
   - ✅ **Production Branch** is set correctly (usually `main` or `dev`)
   - ✅ **Git Integration** shows "Connected"

3. Check **Deploy Hooks**:
   - Go to **Settings** → **Git** → Scroll to **Deploy Hooks**
   - Verify webhook is active
   - If missing, you may need to reconnect the repository

## Step 2: Configure Branch Deployments

### Option A: Deploy from `dev` branch

1. In Vercel Dashboard → **Settings** → **Git**
2. Under **Production Branch**, you can:
   - Change it to `dev` if you want `dev` as production
   - OR enable **Preview Deployments** for `dev` branch

3. For Preview Deployments:
   - Go to **Settings** → **Git**
   - Ensure **Automatic deployments from Git** is enabled
   - All branches will create preview deployments

### Option B: Push to `main` branch (if Vercel watches `main`)

```bash
# Merge dev into main
git checkout main
git merge dev
git push origin main
```

## Step 3: Verify GitHub Webhook

1. Go to **GitHub** → Your Repository → **Settings** → **Webhooks**
2. Look for a Vercel webhook
3. If missing:
   - Go back to Vercel Dashboard
   - **Settings** → **Git** → Click **Disconnect**
   - Then **Connect Git Repository** again
   - This will recreate the webhook

## Step 4: Trigger Manual Deployment

### Method 1: Via Vercel Dashboard
1. Go to **Deployments** tab
2. Click **Redeploy** on the latest deployment
3. Or click **Create Deployment** → Select branch → Deploy

### Method 2: Via Vercel CLI
```bash
# Install Vercel CLI (if not installed)
npm i -g vercel

# Login
vercel login

# Deploy from current directory
vercel --prod
```

## Step 5: Make a Change to Trigger Deployment

If automatic deployments still don't work, make a small change:

```bash
# Make a small change to trigger deployment
echo "# Deployment trigger" >> README.md
git add README.md
git commit -m "Trigger deployment"
git push origin dev
```

## Step 6: Check Deployment Logs

1. Go to **Vercel Dashboard** → **Deployments**
2. Check if there are any failed deployments
3. Click on a deployment to see:
   - Build logs
   - Runtime logs
   - Error messages

## Common Issues & Solutions

### Issue: "No deployments found"
**Solution**: 
- Check if the repository is properly connected
- Verify you're looking at the correct project
- Try creating a manual deployment first

### Issue: "Webhook not receiving events"
**Solution**:
- Reconnect the Git repository in Vercel
- Check GitHub webhook settings
- Verify repository permissions

### Issue: "Branch not configured"
**Solution**:
- Go to **Settings** → **Git** → **Production Branch**
- Set it to the branch you're pushing to (`dev` or `main`)
- Enable preview deployments for other branches

## Quick Fix: Force New Deployment

Run these commands to trigger a new deployment:

```bash
# Make sure you're on the right branch
git checkout dev

# Make a small change
echo "/* Deployment update */" >> static/style.css

# Commit and push
git add static/style.css
git commit -m "Trigger Vercel deployment"
git push origin dev
```

## Verify Deployment Status

After pushing, check:
1. **Vercel Dashboard** → **Deployments** (should show new deployment)
2. **GitHub** → **Actions** (if using GitHub Actions)
3. Wait 1-2 minutes for deployment to start

## Need Help?

If deployments still don't trigger:
1. Check Vercel status page: https://www.vercel-status.com
2. Review Vercel logs in dashboard
3. Contact Vercel support with your project URL

