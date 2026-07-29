# Backend Deployment Status ✅

## Code Status
- ✅ All Switch backend code is pushed to `prod` branch
- ✅ `api/switch_routes.py` - Created and included
- ✅ `api/candidate_onboarding_routes.py` - OTP endpoint exists
- ✅ `api/routers.py` - Switch router is included
- ✅ `api/app.py` - All routers are registered
- ✅ `requirements.txt` - Twilio is listed (twilio==9.3.0)

## What Was Pushed
Commit: `0aff2dd` - "Add Switch backend routes and deployment configuration"

Files included:
- `api/switch_routes.py` (new)
- `api/routers.py` (updated - includes switch_router)
- `api/app.py` (updated - CORS for switchlocally.com)
- `api/candidate_onboarding_routes.py` (updated - isAvailable field)
- `DEPLOYMENT_GUIDE.md` (new)
- `QUICK_DEPLOY.md` (new)

## 🔍 If OTP is Not Working - Check These:

### 1. Environment Variables (MOST COMMON ISSUE)
Your production server needs these environment variables:
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

**How to check:**
- SSH into your server
- Run: `echo $TWILIO_ACCOUNT_SID`
- If empty, variables are not set!

### 2. Twilio Package Installation
```bash
# On your server
pip list | grep twilio
# Should show: twilio 9.3.0

# If not installed:
pip install twilio
# OR
pip install -r requirements.txt
```

### 3. Backend Restart
After deploying new code, restart your backend:
```bash
# If using your deploy.sh script:
./deploy.sh

# OR manually:
pkill -f "uvicorn main:app"
source env_vars.sh
uv run uvicorn main:app --port 8000 --workers 4
```

### 4. Check Backend Logs
When you try to send OTP, check logs for:
- `📞 [ONBOARDING] Attempting to send OTP...` - Request received
- `⚠️ [ONBOARDING] Twilio not configured...` - Environment variables missing
- `❌ [ONBOARDING] Failed to send SMS OTP...` - Twilio error
- `✅ [ONBOARDING] SMS OTP queued/sent...` - Success!

### 5. Test Endpoint
Test directly:
```bash
curl -X POST https://your-backend-url/api/candidate-onboarding/signup \
  -H "Content-Type: application/json" \
  -d '{"country_code": "91", "phone": "9876543210"}'
```

### 6. Check API Docs
Visit: `https://your-backend-url/api/docs`
- Find `/api/candidate-onboarding/signup`
- Try it from Swagger UI
- See what error you get

## 🚨 Most Likely Issues

1. **Environment variables not set** (90% of cases)
   - Fix: Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

2. **Backend not restarted after deployment**
   - Fix: Restart backend server

3. **Twilio package not installed**
   - Fix: `pip install twilio` or `pip install -r requirements.txt`

4. **Wrong backend URL in frontend**
   - Fix: Check `VITE_API_BASE_URL` in frontend

## ✅ Verification Checklist

- [ ] Code pulled from GitHub (`git pull origin prod`)
- [ ] Environment variables set (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`)
- [ ] Twilio package installed (`pip list | grep twilio`)
- [ ] Backend restarted after deployment
- [ ] Backend logs show OTP requests
- [ ] API docs accessible (`/api/docs`)
- [ ] Frontend has correct backend URL

## 📞 Next Steps

1. **Check your server logs** - Look for OTP-related messages
2. **Verify environment variables** - Make sure Twilio credentials are set
3. **Test endpoint directly** - Use curl or Swagger UI
4. **Check Twilio console** - See if messages are being sent

The code is correct and pushed. The issue is likely configuration (env vars) or deployment (restart needed).

