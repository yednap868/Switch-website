# MyOperator Configuration Guide

## Problem: Calls Going to IVR Instead of Twilio

If you're hearing "Press 1 for sales, press 2 for support" when calling your MyOperator number, it means calls are not being forwarded to Twilio. The polling system can detect calls, but by then it's too late - the IVR has already started.

## Solution: Configure Call Forwarding in MyOperator Dashboard

### Step 1: Access MyOperator Dashboard
1. Go to https://app.myoperator.co
2. Log in with your credentials
3. Select your number: **+918041295402**

### Step 2: Configure Call Routing
1. Navigate to **Settings** → **Call Routing** or **IVR Settings**
2. Find the section for **Incoming Call Handling**
3. Set **Forward To**: Your Twilio number (e.g., `+15625260001`)
4. **Disable** the default IVR menu (press 1/2 options)
5. Set routing to **Immediate Forward** or **Direct Forward**

### Step 3: Alternative - Use Webhooks (Recommended)
1. Go to **Settings** → **APIs & Webhooks** → **Webhooks**
2. Add a new webhook:
   - **URL**: `https://your-server.com/api/myoperator/webhook`
   - **Events**: Select "Incoming Call" or "Call Started"
   - **Method**: POST
3. Save the webhook

### Step 4: Verify Configuration
1. Make a test call to your MyOperator number: **+918041295402**
2. The call should immediately forward to your Twilio number
3. You should hear the ElevenLabs AI agent, not the IVR menu

## Current Status

- ✅ API authentication working
- ✅ Polling system detecting calls
- ⚠️  Call forwarding needs to be configured in MyOperator dashboard
- ⚠️  Without forwarding, calls go through default IVR

## Testing

After configuring forwarding:
1. Call **+918041295402**
2. Call should forward to Twilio immediately
3. ElevenLabs AI should answer and collect job requirements
4. Check server logs: `tail -f /tmp/switch-polling.log`

## Troubleshooting

**Issue**: Still hearing IVR menu
- **Fix**: Check MyOperator dashboard call routing settings
- Ensure forwarding is enabled and IVR is disabled

**Issue**: Calls not reaching Twilio
- **Fix**: Verify Twilio number is correct in MyOperator settings
- Check Twilio webhook URL is accessible

**Issue**: Webhook not receiving events
- **Fix**: Ensure webhook URL is publicly accessible (use ngrok for local testing)
- Verify webhook is enabled in MyOperator dashboard
