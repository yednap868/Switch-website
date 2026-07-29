# Switch Deployment Guide for switchlocally.com

This guide covers deploying all components of the Switch platform to switchlocally.com.

## Architecture Overview

1. **Backend API** (FastAPI) - `https://api.switchlocally.com` or `https://switchlocally.com/api`
2. **Frontend App** (React) - `https://app.switchlocally.com` or `https://switchlocally.com/app`
3. **Landing Page** (Static HTML) - `https://switchlocally.com`

## Prerequisites

- Domain: `switchlocally.com` (and subdomains if using)
- Firebase project with Firestore enabled
- Twilio account for SMS OTP
- GitHub repository (optional, for CI/CD)

---

## Option 1: Railway (Recommended for Backend)

### Backend Deployment on Railway

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo" (or upload code)

3. **Configure Environment Variables**
   Add these in Railway dashboard → Variables:
   ```
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=+1234567890
   GOOGLE_APPLICATION_CREDENTIALS_JSON={...your firebase credentials...}
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=secure_password
   DOMAIN=https://api.switchlocally.com
   ```

4. **Configure Build**
   - Railway auto-detects Python
   - Uses `requirements.txt` automatically
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

5. **Custom Domain**
   - Railway → Settings → Domains
   - Add `api.switchlocally.com`
   - Update DNS records as instructed

---

## Option 2: Render (Alternative for Backend)

### Backend Deployment on Render

1. **Create Render Account**
   - Go to https://render.com
   - Sign up

2. **Create New Web Service**
   - Connect GitHub repo
   - Select Python environment
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables**
   - Add all required env vars in Render dashboard

4. **Custom Domain**
   - Render → Settings → Custom Domains
   - Add `api.switchlocally.com`

---

## Frontend Deployment (Vercel - Recommended)

### Deploy React App to Vercel

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Navigate to Switch Directory**
   ```bash
   cd Switch
   ```

3. **Create `.env.production`**
   ```bash
   VITE_API_BASE_URL=https://api.switchlocally.com
   ```

4. **Deploy**
   ```bash
   vercel --prod
   ```

5. **Configure Custom Domain**
   - Vercel Dashboard → Project → Settings → Domains
   - Add `app.switchlocally.com` or `switchlocally.com/app`

### Alternative: Netlify

1. **Create `netlify.toml`** in Switch directory:
   ```toml
   [build]
     command = "npm run build"
     publish = "dist"
   
   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```

2. **Deploy via Netlify Dashboard**
   - Connect GitHub repo
   - Build command: `npm run build`
   - Publish directory: `dist`
   - Add environment variable: `VITE_API_BASE_URL=https://api.switchlocally.com`

---

## Landing Page Deployment

### Deploy Landing Page to Vercel/Netlify

1. **Option A: Same domain as app**
   - Deploy `Switch-website/landing.html` as `index.html` to root domain
   - Update links in landing page to point to `/app`

2. **Option B: Separate deployment**
   - Deploy `Switch-website` folder to Vercel/Netlify
   - Point `switchlocally.com` to this deployment

---

## DNS Configuration

Configure your DNS records:

```
# If using subdomains:
api.switchlocally.com    →  Railway/Render IP (or CNAME)
app.switchlocally.com    →  Vercel/Netlify IP (or CNAME)
switchlocally.com        →  Landing page (Vercel/Netlify)

# If using path-based routing:
switchlocally.com        →  Landing page
switchlocally.com/app    →  React app (Vercel/Netlify)
switchlocally.com/api    →  Backend (Railway/Render with reverse proxy)
```

---

## Environment Variables Checklist

### Backend (Railway/Render)
- [ ] `TWILIO_ACCOUNT_SID`
- [ ] `TWILIO_AUTH_TOKEN`
- [ ] `TWILIO_PHONE_NUMBER`
- [ ] `GOOGLE_APPLICATION_CREDENTIALS_JSON` (Firebase credentials as JSON string)
- [ ] `ADMIN_USERNAME`
- [ ] `ADMIN_PASSWORD`
- [ ] `DOMAIN` (e.g., `https://api.switchlocally.com`)
- [ ] `VANCE_CALENDAR_CLIENT_ID` (if using calendar features)
- [ ] `VANCE_CALENDAR_CLIENT_SECRET`
- [ ] `VANCE_CALENDAR_REDIRECT_URI`

### Frontend (Vercel/Netlify)
- [ ] `VITE_API_BASE_URL` = `https://api.switchlocally.com`

---

## Post-Deployment Checklist

1. **Test Backend**
   - Visit `https://api.switchlocally.com/api/docs`
   - Test OTP endpoint: `POST /api/candidate-onboarding/signup`

2. **Test Frontend**
   - Visit `https://app.switchlocally.com`
   - Verify API calls work (check browser console)

3. **Update Landing Page**
   - Update CTA buttons to point to app URL
   - Test all links

4. **CORS Configuration**
   - Update `api/app.py` CORS origins to include production domains
   - Remove `"*"` wildcard in production

5. **SSL/HTTPS**
   - Ensure all services use HTTPS
   - Railway/Render/Vercel provide SSL automatically

---

## Monitoring & Maintenance

1. **Logs**
   - Railway: Dashboard → Deployments → View Logs
   - Vercel: Dashboard → Deployments → View Logs
   - Render: Dashboard → Logs

2. **Error Tracking**
   - Consider adding Sentry for error tracking

3. **Backups**
   - Firebase Firestore has automatic backups
   - Consider setting up scheduled exports

---

## Troubleshooting

### Backend Issues
- Check environment variables are set correctly
- Verify Firebase credentials format (JSON string)
- Check logs for specific errors

### Frontend Issues
- Verify `VITE_API_BASE_URL` is set correctly
- Check browser console for CORS errors
- Ensure backend is accessible from frontend domain

### CORS Errors
- Update `api/app.py` to include frontend domain in `allow_origins`
- Remove wildcard `"*"` in production

---

## Quick Deploy Commands

### Backend (Railway)
```bash
railway login
railway init
railway up
```

### Frontend (Vercel)
```bash
cd Switch
vercel --prod
```

---

## Support

For issues, check:
1. Service logs (Railway/Vercel/Render dashboards)
2. Browser console (for frontend issues)
3. Network tab (for API call issues)

