# 🚀 Simple Deployment Steps for Switch Backend

## Step 1: Push Code to GitHub (You're almost done!)

Your code is committed. Just push it:

```bash
cd /Users/alt/Vance-1
git push origin prod
```

If you get authentication errors, you might need to:
- Use a personal access token instead of password
- Or use SSH: `git remote set-url origin git@github.com:Vance-2025/Vance.git`

---

## Step 2: Deploy to Railway (Easiest Option)

### Option A: Using Railway Dashboard (Recommended - No CLI needed!)

1. **Go to Railway**
   - Visit: https://railway.app
   - Sign up/Login with GitHub

2. **Create New Project**
   - Click the big **"New Project"** button
   - Select **"Deploy from GitHub repo"**
   - Authorize Railway to access your GitHub
   - Select repository: **Vance-2025/Vance**
   - Select branch: **prod**

3. **Railway Auto-Detects Everything**
   - Railway will automatically:
     - Detect it's a Python project
     - Find `requirements.txt`
     - Set up the build

4. **Add Environment Variables**
   - Click on your project
   - Go to **"Variables"** tab
   - Click **"New Variable"**
   - Add these one by one:

   ```
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project",...}
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_secure_password
   DOMAIN=https://api.switchlocally.com
   ```

   **Important:** For `GOOGLE_APPLICATION_CREDENTIALS_JSON`, you need to:
   - Get your Firebase service account JSON file
   - Copy the ENTIRE JSON content
   - Paste it as a single-line string (remove all line breaks)

5. **Configure Start Command**
   - Go to **"Settings"** tab
   - Under **"Deploy"** section
   - Set **Start Command** to:
     ```
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```

6. **Deploy!**
   - Railway will automatically deploy
   - Watch the logs in the **"Deployments"** tab
   - Wait for "Deploy successful" ✅

7. **Get Your Backend URL**
   - Railway gives you a URL like: `https://your-app-name.up.railway.app`
   - This is your backend API URL!

8. **Add Custom Domain (Optional)**
   - Go to **"Settings"** → **"Domains"**
   - Click **"Generate Domain"** or **"Custom Domain"**
   - Add: `api.switchlocally.com`
   - Railway will give you DNS instructions
   - Update your DNS records as instructed

---

### Option B: Using Railway CLI (If you prefer command line)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Link to existing project or create new
railway link

# Add environment variables
railway variables set TWILIO_ACCOUNT_SID=your_value
railway variables set TWILIO_AUTH_TOKEN=your_value
# ... add all other variables

# Deploy
railway up
```

---

## Step 3: Test Your Backend

Once deployed, test it:

1. **Check API Docs**
   - Visit: `https://your-railway-url.up.railway.app/api/docs`
   - You should see Swagger UI with all your endpoints

2. **Test OTP Endpoint**
   - Go to `/api/candidate-onboarding/signup`
   - Try sending a test request
   - Check if it works!

---

## Step 4: Update Frontend to Use Production API

Once your backend is deployed:

1. **Get your Railway URL**
   - Example: `https://switch-api.up.railway.app`

2. **Update Frontend Environment**
   - In `Switch/` directory
   - Create `.env.production`:
     ```
     VITE_API_BASE_URL=https://switch-api.up.railway.app
     ```
   - Or if you set up custom domain:
     ```
     VITE_API_BASE_URL=https://api.switchlocally.com
     ```

---

## 🎯 Quick Checklist

- [ ] Code pushed to GitHub
- [ ] Railway account created
- [ ] Project deployed from GitHub
- [ ] Environment variables added
- [ ] Backend URL working (check `/api/docs`)
- [ ] Custom domain configured (optional)
- [ ] Frontend updated with production API URL

---

## 🆘 Troubleshooting

### "Build Failed"
- Check Railway logs
- Make sure `requirements.txt` exists
- Verify Python version (Railway auto-detects)

### "Environment Variable Error"
- Make sure all required variables are set
- Check for typos in variable names
- Verify JSON format for `GOOGLE_APPLICATION_CREDENTIALS_JSON`

### "Port Error"
- Railway automatically sets `$PORT` environment variable
- Make sure start command uses `$PORT` not hardcoded `8000`

### "CORS Errors"
- Update `api/app.py` to include your frontend domain
- Already added switchlocally.com domains ✅

---

## 📞 Need Help?

1. Check Railway logs: Dashboard → Deployments → View Logs
2. Check API docs: `https://your-url/api/docs`
3. Test endpoints manually in Swagger UI

---

## 🎉 You're Done!

Once backend is deployed:
- You'll get a URL like: `https://xxx.up.railway.app`
- Use this URL in your frontend
- Test everything works
- Then deploy frontend to Vercel!

