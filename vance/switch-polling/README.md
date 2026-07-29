# Switch Voice AI - Polling-Based Job Matching System

## Overview

This system automatically matches employers with job candidates using voice AI:
1. **Detects** incoming calls to MyOperator number via polling
2. **Connects** employer to ElevenLabs AI via Twilio
3. **Collects** job requirements through conversation
4. **Calls** matching candidates in batch
5. **Connects** first candidate who picks up to employer

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `MYOPERATOR_X_API_KEY` - Your MyOperator API key
- `MYOPERATOR_NUMBER` - Your MyOperator phone number
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token
- `TWILIO_US_NUMBER` - Your Twilio US phone number
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `ELEVENLABS_AGENT_ID` - ElevenLabs agent ID
- `SERVER_URL` - Your public server URL (use ngrok for testing)

### 3. Start Server

```bash
npm start
```

For development with auto-reload:
```bash
npm run dev
```

### 4. Configure MyOperator Call Forwarding

**CRITICAL:** You must configure MyOperator to forward incoming calls directly to your Twilio number, bypassing the IVR:

1. Log in to MyOperator dashboard: https://app.myoperator.co
2. Go to **Settings** → **Call Routing** or **IVR Settings**
3. Configure incoming calls to forward to: `YOUR_TWILIO_US_NUMBER` (e.g., +15625260001)
4. **Disable or bypass the default IVR** (press 1 for sales, press 2 for support)
5. Set calls to forward immediately to the Twilio number

**Alternative:** Set up MyOperator webhook to notify your server in real-time:
- Webhook URL: `https://your-server.com/api/myoperator/webhook`
- Event: "Incoming Call" or "Call Started"

Without this configuration, calls will go through MyOperator's default IVR and won't reach Twilio/ElevenLabs AI.

### 5. Set Up ngrok (for local testing)

```bash
# Install ngrok
npm install -g ngrok

# Start ngrok
ngrok http 3000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Update SERVER_URL in .env
# Restart server
```

### 5. Configure Twilio Webhooks

In Twilio Console → Phone Numbers → Your Number:
- **Voice & Fax → A CALL COMES IN:** 
  ```
  https://your-ngrok-url.com/api/twilio/incoming
  ```
- **HTTP Method:** POST

### 6. Configure ElevenLabs Agent

In ElevenLabs Dashboard → Your Agent:
- **Custom Tool → Webhook URL:**
  ```
  https://your-ngrok-url.com/api/elevenlabs/requirements
  ```

## How It Works

### Polling Flow

1. **Polling Loop** (every 2 seconds):
   - Fetches call logs from MyOperator API
   - Detects new incoming calls
   - Triggers Click2Call to connect employer to Twilio

2. **Employer Call**:
   - Employer calls MyOperator number
   - System detects call within 2-4 seconds
   - MyOperator calls Twilio number
   - Twilio connects to ElevenLabs AI

3. **AI Collection**:
   - ElevenLabs AI asks employer about job requirements
   - Collects: job type, location, salary, experience
   - Sends requirements to webhook

4. **Candidate Matching**:
   - System finds matching candidates
   - Calls top 10 candidates via MyOperator Click2Call
   - Each candidate call goes to Twilio

5. **Connection**:
   - First candidate who picks up hears intro
   - Joins conference call with employer
   - Conversation begins!

## API Endpoints

### Health Check
```
GET /health
```

### Status
```
GET /api/status
```
Returns active calls and system status

### Twilio Webhooks
```
POST /api/twilio/incoming
POST /api/twilio/candidate-connected
POST /api/twilio/employer-to-conference
POST /api/conference-status
POST /api/recording-complete
```

### ElevenLabs Webhook
```
POST /api/elevenlabs/requirements
Body: { job_type, location, salary, experience, call_sid }
```

## Testing

### Test 1: Polling Detection
1. Start server: `npm start`
2. Call MyOperator number: +918041295402
3. Check logs - should see "New employer call detected"
4. MyOperator should call you back immediately
5. You should hear ElevenLabs AI

### Test 2: End-to-End
1. Call MyOperator number
2. Talk to ElevenLabs: "I need a security guard in Udyog Vihar"
3. ElevenLabs collects requirements
4. Check logs - should see "Calling 10 candidates"
5. Your test phone should ring (if in candidates list)
6. Pick up - should hear intro message
7. Should be connected to employer in conference

## Troubleshooting

**Polling not detecting calls:**
- Check MyOperator API credentials
- Verify call logs API is returning data
- Check time range in polling
- Ensure call status is 'ringing', 'in-progress', or 'answered'

**Click2Call not working:**
- Verify x-api-key is correct
- Check phone number format (+91XXXXXXXXXX)
- Ensure Twilio US number is correct
- Check MyOperator API response for errors

**ElevenLabs not connecting:**
- Check Twilio webhook URL is public (use ngrok)
- Verify ElevenLabs agent ID and API key
- Check Twilio console for error logs
- Ensure SERVER_URL is set correctly

**Candidates not being called:**
- Check candidate phone numbers are correct
- Verify MyOperator Click2Call API is working
- Check rate limiting (300ms delay between calls)
- Review candidate matching logic

## Next Steps

1. **Add Database:** Replace in-memory storage with PostgreSQL
2. **Add Authentication:** Protect endpoints
3. **Add WhatsApp:** Send confirmations after calls
4. **Add Analytics:** Track success rates
5. **Optimize Polling:** Use webhooks if MyOperator adds them
6. **Add Call Recording:** Download and store recordings
7. **Add Follow-ups:** Automated post-call messages

## Success Criteria

✅ Employer calls MyOperator number
✅ Within 2-4 seconds, connected to ElevenLabs AI
✅ AI collects requirements
✅ System calls 10 candidates
✅ First candidate to pick up gets connected
✅ Employer and candidate have conversation
✅ Total time from employer call to candidate connection: <60 seconds
