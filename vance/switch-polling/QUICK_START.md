# Quick Start Guide - Switch Voice AI

## 🚀 Get Running in 5 Minutes

### Step 1: Install & Setup

```bash
cd /Users/alt/Vance-1/switch-polling
./setup.sh
```

### Step 2: Configure .env

Edit `.env` file and add your credentials:

```bash
# MyOperator
MYOPERATOR_X_API_KEY=your_myoperator_api_key
MYOPERATOR_NUMBER=+91XXXXXXXXXX

# Twilio (from env_vars.sh)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_US_NUMBER=+1XXXXXXXXXX

# ElevenLabs (from env_vars.sh)
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_elevenlabs_agent_id

# Server (use ngrok for testing)
PORT=3000
SERVER_URL=https://your-ngrok-url.ngrok.io
```

### Step 3: Start ngrok

```bash
# Install ngrok if not installed
npm install -g ngrok

# Start ngrok
ngrok http 3000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Update SERVER_URL in .env
```

### Step 4: Configure Webhooks

#### Twilio Console
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Click on your number: `+15625260001`
3. Under "Voice & Fax":
   - **A CALL COMES IN:** `https://your-ngrok-url.ngrok.io/api/twilio/incoming`
   - **HTTP Method:** POST
4. Save

#### ElevenLabs Dashboard
1. Go to your agent settings
2. Set webhook URL: `https://your-ngrok-url.ngrok.io/api/elevenlabs/requirements`

### Step 5: Start Server

```bash
npm start
```

You should see:
```
🚀 Switch AI Server running on port 3000
📊 Polling MyOperator every 2 seconds...
🔗 Server URL: https://your-ngrok-url.ngrok.io
📞 MyOperator Number: +918041295402
📞 Twilio Number: +15625260001
```

### Step 6: Test It!

1. **Call MyOperator number:** +918041295402
2. **Watch logs** - should see:
   ```
   📞 New employer call detected: +91XXXXXXXXXX
   🔄 Connecting employer to Twilio...
   ✅ Employer connected to AI!
   ```
3. **Talk to AI:** "I need a security guard in Udyog Vihar"
4. **AI collects requirements** and sends to webhook
5. **System calls candidates** (if you're in the list, your phone will ring)
6. **Pick up** - you'll be connected to employer!

## 🧪 Test Endpoints

### Health Check
```bash
curl http://localhost:3000/health
```

### Status
```bash
curl http://localhost:3000/api/status
```

## 📊 Monitoring

Watch the logs for:
- `📞 New employer call detected` - Polling working
- `✅ Employer connected to AI!` - Click2Call working
- `📋 Requirements received` - ElevenLabs working
- `👥 Found X matching candidates` - Matching working
- `📱 Called X candidates` - Batch calling working
- `✅ Candidate connected` - Connection working

## 🐛 Troubleshooting

**No calls detected?**
- Check MyOperator API key is correct
- Verify polling is running (check logs)
- Test MyOperator API directly

**Click2Call not working?**
- Check phone number format (+91XXXXXXXXXX)
- Verify Twilio number is correct
- Check MyOperator API response

**ElevenLabs not connecting?**
- Verify webhook URL is public (ngrok)
- Check agent ID and API key
- Review Twilio console logs

**Candidates not called?**
- Check candidate phone numbers
- Verify matching logic
- Review MyOperator API responses

## ✅ Success Indicators

- ✅ Server starts without errors
- ✅ Polling logs show every 2 seconds
- ✅ Calling MyOperator number triggers detection
- ✅ Employer hears ElevenLabs AI
- ✅ Requirements are collected
- ✅ Candidates are called
- ✅ Connection is established
