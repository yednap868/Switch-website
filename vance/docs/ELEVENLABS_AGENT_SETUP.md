# ElevenLabs Agent Setup for Switch

This guide explains how to configure a new ElevenLabs Conversational AI agent for Switch.

## Prerequisites

1. ElevenLabs account with Conversational AI access
2. Twilio account for phone number
3. Backend deployed at `api.relayy.world`

## Step 1: Create New Agent in ElevenLabs

1. Go to [ElevenLabs Conversational AI](https://elevenlabs.io/conversational-ai)
2. Click "Create Agent"
3. Configure:
   - **Name:** `Switch-Jyoti`
   - **Language:** Hindi (or Multilingual for Hinglish)
   - **Voice:** Choose a friendly female Indian voice

## Step 2: Configure Agent System Prompt

Copy the full prompt from `agent/static/system_prompt_voice.md` into the ElevenLabs agent configuration.

Key sections:
- Identity: Jyoti from Switch
- Three call types: `business_inbound`, `candidate_inbound`, `candidate_pitch`
- Language: Hinglish (Hindi + English mix)
- Personality: Warm, genuine, helpful - like a supportive didi

## Step 3: Configure Dynamic Variables

In ElevenLabs agent settings, add these dynamic variables:

| Variable | Type | Description |
|----------|------|-------------|
| `call_type` | string | `business_inbound` / `candidate_inbound` / `candidate_pitch` |
| `candidate_name` | string | Candidate's name |
| `business_name` | string | Business name |
| `contact_person` | string | Business contact person |
| `registered_via` | string | `app` / `whatsapp` / `referral` |
| `job_role` | string | Job role being pitched |
| `job_location` | string | Job location |
| `job_salary` | string | Salary range (e.g., "₹12,000 - ₹15,000") |
| `job_timing` | string | Shift timing |
| `initial_message` | string | Initial WhatsApp message (for business intake) |

## Step 4: Configure Webhooks

Set up these webhooks in ElevenLabs:

### Post-Call Webhook (Required)
```
URL: https://api.relayy.world/api/webhooks/elevenlabs/webhook/post-call
Method: POST
```
This webhook receives call transcripts and extracted data after each call ends.

### Call Initiation Webhook (Optional)
```
URL: https://api.relayy.world/api/webhooks/elevenlabs/initiation/webhook
Method: POST
```
This webhook is called when a call is initiated.

### Extraction Data Endpoint (For AI Agent Tools)
```
URL: https://api.relayy.world/api/webhooks/tools/log_extraction_data/{user_id}
Method: POST
```
The ElevenLabs agent can call this to log extracted data during the call.

## Step 5: Link Twilio Phone Number

1. In ElevenLabs, go to Phone Numbers
2. Connect your Twilio account
3. Select or purchase an Indian phone number (+91)
4. Link it to the Switch-Jyoti agent

## Step 6: Update Environment Variables

Update these in your `.env` or `env_vars.sh`:

```bash
# Switch ElevenLabs Agent (Jyoti)
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_AGENT_ID=agent_1101kfxtskyve0csns9bh7bedq9h
ELEVENLABS_PHONE_NUMBER_ID=phone_number_id_here  # Same as before

# Twilio (for call management)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

## Step 7: Test the Agent

### Test Candidate Screening Call (candidate_inbound)
```bash
curl -X POST https://api.relayy.world/api/switch/test-screening-call \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "test_candidate_123"}'
```

### Test Business Intake Call (business_inbound)
```bash
curl -X POST https://api.relayy.world/api/switch/business/whatsapp/requirement \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919876543210",
    "message": "Waiter chahiye 2 log"
  }'
```

## Files Using ElevenLabs Agent

These files pass `call_type` to the ElevenLabs agent:

| File | call_type | Purpose |
|------|-----------|---------|
| `services/switch_screening_service.py` | `candidate_inbound` | Candidate screening calls |
| `services/switch_business_intake_service.py` | `business_inbound` | Business requirement calls |
| `services/switch_call_service.py` | `candidate_pitch` | Job pitch calls to candidates |
| `api/switch_practice_routes.py` | N/A | Practice interview calls |

## Voice Settings Recommendations

For Jyoti voice in ElevenLabs:

| Setting | Value |
|---------|-------|
| Stability | 0.5 |
| Clarity | 0.75 |
| Style | 0.3 |
| Speaker Boost | Enabled |

Choose a voice that sounds:
- Female, Indian accent
- Friendly and warm
- Clear pronunciation
- Natural conversational pace

## Data Extraction

The agent should extract and return structured data. Configure the agent to output JSON:

### For candidate_inbound Calls:
```json
{
  "name": "string",
  "area": "string",
  "language_preference": "hindi/english/hinglish",
  "work_history": [{"company": "", "role": "", "duration": "", "why_left": ""}],
  "skills": ["string"],
  "english_level": "none/basic/conversational",
  "preferences": {
    "roles": ["string"],
    "areas": ["string"],
    "salary_expectation": "number",
    "timing_constraints": "string",
    "available_from": "string"
  },
  "reliability_indicators": "string",
  "concerns": "string"
}
```

### For business_inbound Calls:
```json
{
  "business_name": "string",
  "contact_person": "string",
  "type": "restaurant/retail/cafe/other",
  "area": "string",
  "role": "WAITER/HELPER/SALES/KITCHEN/DELIVERY/SECURITY",
  "positions_count": "number",
  "salary_min": "number",
  "salary_max": "number",
  "experience_required": "string",
  "interview_address": "string",
  "interview_timing": "string",
  "specific_requirements": "string"
}
```

### For candidate_pitch Calls:
```json
{
  "outcome": "interested/not_interested/callback/transferred/no_answer",
  "transfer_attempted": true/false,
  "transfer_successful": true/false,
  "follow_up_required": true/false,
  "follow_up_time": "string",
  "objections": "string",
  "notes": "string"
}
```

## Troubleshooting

### Call Not Initiating
1. Check `ELEVENLABS_AGENT_ID` is correct
2. Verify `ELEVENLABS_PHONE_NUMBER_ID` is linked
3. Check Twilio credentials
4. Ensure phone number is in E.164 format (+91...)

### Wrong Voice/Language
1. Re-check agent language settings
2. Verify voice selection in ElevenLabs
3. Test with sample text in ElevenLabs dashboard

### No Data Extraction
1. Check webhook URLs are correct
2. Verify SSL certificate on api.relayy.world
3. Check backend logs for webhook errors

### Wrong call_type Behavior
1. Verify `call_type` is being passed correctly in dynamic_variables
2. Check the backend service is using the correct call_type value
3. Test with ElevenLabs playground to verify prompt behavior

## Migration Checklist

- [ ] Create new agent in ElevenLabs with name "Switch-Jyoti"
- [ ] Copy full prompt from `agent/static/system_prompt_voice.md`
- [ ] Configure all dynamic variables (call_type, candidate_name, etc.)
- [ ] Set up webhooks to api.relayy.world
- [ ] Link Twilio phone number (+91)
- [ ] Update `ELEVENLABS_AGENT_ID` in env
- [ ] Test candidate_inbound call (screening)
- [ ] Test business_inbound call (intake)
- [ ] Test candidate_pitch call (job pitch)
- [ ] Verify data extraction is working
- [ ] Deploy to production
