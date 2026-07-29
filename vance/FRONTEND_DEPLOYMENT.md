# Frontend Deployment Guide

## Current Setup

You have **TWO separate things** to deploy:

1. **Switch-website** (Landing Page) - Static HTML
   - Repo: `https://github.com/yednap868/Switch-website.git`
   - Status: ✅ Fixed and ready for Netlify
   - Deploy to: `switchlocally.com` (main domain)

2. **Switch** (React App) - Frontend Application
   - Location: `/Users/alt/Vance-1/Switch/`
   - Status: ⚠️ Needs to be pushed to a repo and deployed
   - Deploy to: `app.switchlocally.com` or `switchlocally.com/app`

---

## Option 1: Deploy Switch App to Same Repo (Recommended)

### Step 1: Push Switch App to Switch-website Repo

```bash
cd /Users/alt/Vance-1/Switch-website
git checkout -b app  # Create new branch for app
cd ..
cp -r Switch/* Switch-website/app/  # Copy Switch app
cd Switch-website
git add app/
git commit -m "Add Switch React app"
git push origin app
```

### Step 2: Deploy on Netlify

1. Go to Netlify Dashboard
2. Add new site → Import from Git
3. Select `Switch-website` repo
4. Configure:
   - **Base directory**: `app` (for React app)
   - **Build command**: `npm install && npm run build`
   - **Publish directory**: `app/dist`
   - **Branch**: `app`
5. Add environment variable:
   - `VITE_API_BASE_URL` = `https://your-backend-api.com`
6. Deploy!

---

## Option 2: Create Separate Repo for Switch App (Cleaner)

### Step 1: Create New Repo

1. Go to GitHub
2. Create new repo: `Switch-app` or `Switch-frontend`

### Step 2: Push Switch App

```bash
cd /Users/alt/Vance-1/Switch
git init
git add .
git commit -m "Initial commit: Switch React app"
git remote add origin https://github.com/yednap868/Switch-app.git
git push -u origin main
```

### Step 3: Deploy on Netlify/Vercel

**Netlify:**
1. Add new site → Import from Git
2. Select `Switch-app` repo
3. Configure:
   - Build command: `npm install && npm run build`
   - Publish directory: `dist`
4. Add environment variable:
   - `VITE_API_BASE_URL` = `https://your-backend-api.com`

**Vercel (Recommended for React):**
```bash
cd /Users/alt/Vance-1/Switch
npm install -g vercel
vercel --prod
# Follow prompts, add VITE_API_BASE_URL when asked
```

---

## Option 3: Deploy Both from Same Netlify Site (Advanced)

Use Netlify's routing to serve both:

1. Deploy Switch-website as main site
2. Add `_redirects` file in root:
   ```
   /app/*  /app/index.html  200
   ```
3. Build and deploy Switch app to `/app` directory
4. Configure Netlify to build both

---

## Recommended Approach

**I recommend Option 2** (separate repos):
- Cleaner separation
- Easier to manage
- Better for CI/CD
- Can deploy independently

---

## Quick Fix for Landing Page

The landing page issue is fixed:
- ✅ Added `index.html` (Netlify needs this)
- ✅ Added `netlify.toml` (Netlify config)
- ✅ Pushed to repo

**After push, Netlify will auto-redeploy and the site should work!**

---

## Environment Variables Needed

For the React app (Switch/), you need:

```
VITE_API_BASE_URL=https://your-backend-api.com
```

Replace `your-backend-api.com` with your actual backend URL.

