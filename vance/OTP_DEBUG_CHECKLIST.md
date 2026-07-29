# OTP Debugging Checklist

## ✅ Code Status
- ✅ `api/candidate_onboarding_routes.py` - OTP endpoint exists
- ✅ `api/routers.py` - Router is included
- ✅ `api/app.py` - Router is registered
- ✅ `requirements.txt` - Twilio is listed (twilio==9.3.0)
- ✅ Code is pushed to `prod` branch

## 🔍 Debugging Steps

### 1. Check Backend Logs
Look for these log messages when OTP is requested:

**Success indicators:**
```
📞 [ONBOARDING] Attempting to send OTP to +91****3210
📱 [ONBOARDING] Twilio message created for +919876543210
   Status: queued, SID: SMxxxxx
```

**Failure indicators:**
```
⚠️ [ONBOARDING] Twilio not configured - check TWILIO_ACCOUNT_SID...
❌ [ONBOARDING] SMS OTP failed to send: ...
```

### 2. Check Environment Variables
Make sure these are set in your production environment:
- `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token  
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number (format: +1234567890)

### 3. Check Twilio Package Installation
Verify Twilio is installed:
```bash
# On your server
pip list | grep twilio
# Should show: twilio 9.3.0
```

### 4. Test Endpoint Directly
Test the endpoint with curl:
```bash
curl -X POST https://your-backend-url/api/candidate-onboarding/signup \
  -H "Content-Type: application/json" \
  -d '{"country_code": "91", "phone": "9876543210"}'
```

### 5. Check API Docs
Visit: `https://your-backend-url/api/docs`
- Look for `/api/candidate-onboarding/signup` endpoint
- Try it from Swagger UI

### 6. Check CORS
If frontend can't reach backend:
- Check browser console for CORS errors
- Verify backend CORS settings in `api/app.py`

## 🐛 Common Issues

### Issue 1: "SMS service not configured"
**Cause:** Environment variables not set
**Fix:** Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

### Issue 2: "Twilio not available"
**Cause:** Twilio package not installed
**Fix:** Run `pip install twilio` or `pip install -r requirements.txt`

### Issue 3: "Invalid phone number format"
**Cause:** Phone number normalization issue
**Fix:** Check phone format - should be 10 digits for India (91 country code)

### Issue 4: Network/CORS errors
**Cause:** Backend not accessible or CORS misconfigured
**Fix:** Check backend URL and CORS settings

## 📋 Quick Test

Run this Python script to test OTP sending:

```python
import os
from twilio.rest import Client

# Set these
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")

if not all([account_sid, auth_token, twilio_phone]):
    print("❌ Twilio credentials not set")
else:
    client = Client(account_sid, auth_token)
    try:
        message = client.messages.create(
            body="Test OTP: 123456",
            from_=twilio_phone,
            to="+919876543210"  # Replace with test number
        )
        print(f"✅ Message sent! SID: {message.sid}, Status: {message.status}")
    except Exception as e:
        print(f"❌ Error: {e}")
```

