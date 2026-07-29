# Quick Deployment Steps for switchlocally.com

## 🚀 Fastest Way to Deploy

### Step 1: Deploy Backend (Railway - 5 minutes)

1. Go to https://railway.app and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Python
5. Add environment variables (see checklist below)
6. Deploy!
7. Add custom domain: `api.switchlocally.com`

**Required Environment Variables:**
```
TWILIO_ACCOUNT_SID=your_value
TWILIO_AUTH_TOKEN=your_value
TWILIO_PHONE_NUMBER=+1234567890
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
DOMAIN=https://api.switchlocally.com
```

### Step 2: Deploy Frontend (Vercel - 3 minutes)

1. Install Vercel CLI: `npm i -g vercel`
2. Go to Switch directory: `cd Switch`
3. Create `.env.production`:
   ```
   VITE_API_BASE_URL=https://api.switchlocally.com
   ```
4. Deploy: `vercel --prod`
5. Add custom domain: `app.switchlocally.com`

### Step 3: Deploy Landing Page (Vercel - 2 minutes)

1. Go to Switch-website directory: `cd Switch-website`
2. Deploy: `vercel --prod`
3. Add custom domain: `switchlocally.com`

### Step 4: Configure DNS

Add these DNS records:
- `api.switchlocally.com` → Railway IP (or CNAME)
- `app.switchlocally.com` → Vercel IP (or CNAME)
- `switchlocally.com` → Vercel IP (or CNAME)

---

## ✅ Test Checklist

- [ ] Backend: Visit `https://api.switchlocally.com/api/docs`
- [ ] Frontend: Visit `https://app.switchlocally.com`
- [ ] Landing: Visit `https://switchlocally.com`
- [ ] Test OTP: Try signing up on frontend
- [ ] Test API: Check browser console for errors

---

## 🔧 Troubleshooting

**CORS Errors?**
- Update `api/app.py` to include your domains in `origins` list
- Remove `"*"` wildcard in production

**API Not Working?**
- Check environment variables are set
- Verify Firebase credentials format
- Check Railway logs

**Frontend Can't Connect?**
- Verify `VITE_API_BASE_URL` is set correctly
- Check browser console for errors
- Ensure backend is accessible

---

## 📝 Notes

- All services provide free SSL/HTTPS
- Railway gives $5 free credit monthly
- Vercel has generous free tier
- Update CORS origins in production!

