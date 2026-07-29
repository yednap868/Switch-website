# Verify Twilio Configuration

## Quick Test Script

Run this on your server to verify Twilio credentials are loaded:

```bash
cd /Users/alt/Vance-1  # or your server path
source env_vars.sh
python3 -c "
import os
print('TWILIO_ACCOUNT_SID:', os.getenv('TWILIO_ACCOUNT_SID', 'NOT SET'))
print('TWILIO_AUTH_TOKEN:', os.getenv('TWILIO_AUTH_TOKEN', 'NOT SET')[:10] + '...' if os.getenv('TWILIO_AUTH_TOKEN') else 'NOT SET')
print('TWILIO_PHONE_NUMBER:', os.getenv('TWILIO_PHONE_NUMBER', 'NOT SET'))
"
```

## Expected Output
```
TWILIO_ACCOUNT_SID: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN: xxxxxxxx...
TWILIO_PHONE_NUMBER: +1XXXXXXXXXX
```

## If Variables Are NOT SET

1. **Check env_vars.sh exists:**
   ```bash
   ls -la env_vars.sh
   ```

2. **Check if variables are exported:**
   ```bash
   source env_vars.sh
   echo $TWILIO_ACCOUNT_SID
   ```

3. **Verify deploy.sh sources env_vars.sh:**
   - Check line 10 and 14 in deploy.sh
   - Both should have `source env_vars.sh`

## Test OTP Endpoint Directly

```bash
# After sourcing env_vars.sh
curl -X POST http://localhost:8000/api/candidate-onboarding/signup \
  -H "Content-Type: application/json" \
  -d '{"country_code": "91", "phone": "9876543210"}'
```

Check the response and server logs for errors.

