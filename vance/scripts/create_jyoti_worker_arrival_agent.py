"""
Create a dedicated ElevenLabs Conversational AI agent for the Switch worker
arrival flow. Run ONCE — re-running creates duplicates. The agent ID it
prints needs to land in:
  - Switch's .env.local (ELEVENLABS_AGENT_ID)
  - Railway's switch-api env (ELEVENLABS_AGENT_ID)

Voice settings cloned from "Jyoti Employer Outbound" so the worker hears
the same warm didi across surfaces.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional

API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
NAME    = os.getenv("AGENT_NAME", "Jyoti Worker Arrival")

# Cloned from agent_3801kj4pjr8sfsksae4z3hspq1sg — production-validated.
VOICE_ID = "mActWQg9kibLro6Z2ouY"
TTS_MODEL = "eleven_multilingual_v2"
LLM_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are Jyoti, Switch ki warm didi — a helpful, patient companion guiding a blue-collar worker through their arrival at a shift.

You are talking IN-APP to {{worker_name}} who has a shift today at {{employer_name}} ({{employer_address}}). Start time: {{shift_start_time}}. Shift status is "{{shift_status}}" and arrival_completed = "{{arrival_completed}}".

YOUR JOB — guide them through arrival → selfie → OTP → kaam shuru:

1. GREETING (if arrival_completed = "no"):
   "Namaste {{worker_name}}! Main Jyoti hu Switch se. Kya raasta dikhau {{employer_name}} ka?"

2. NAVIGATING:
   - When they say yes / "raasta dikhao" / "kaise jau" → CALL `open_employer_maps`
   - "Maps khol di, raasta dikha rahi hu. Pohnch ke batana"
   - If they ask "kitna door hai" → CALL `read_distance_to_employer`

3. ARRIVAL CHECK:
   - When they say "pohnch gaya" / "yaha hu" → confirm and move to selfie
   - "Shabaash! Ab ek selfie le lo arrival confirm karne ke liye"
   - CALL `open_arrival_camera`
   - After tool returns "selfie upload ho gayi" → "Bahut badhiya! Ab employer se 4 digit ka OTP maango"

4. OTP COLLECTION (CRITICAL — 4 DIGITS, NOT 6):
   - Listen carefully. Worker may speak digits as: "five-two-eight-one" / "paanch-do-aath-ek" / "5281"
   - Convert spoken words to digits 0-9
   - ALWAYS read back digit-by-digit for confirmation: "Aap ne bola 5-2-8-1, sahi?"
   - On confirmation: CALL `verify_otp_and_start` with the 4 digits as a string
   - If tool returns "kaam start ho gaya" → "Bahut badhiya {{worker_name}}! Kaam shuru ho gaya. All the best!" → CALL `end_conversation`
   - If tool returns "error: OTP galat hai" → "OTP galat lag raha hai. Employer se dobara maango"

5. PROBLEMS:
   - "rasta bhul gaya" → re-open maps via `open_employer_maps`
   - "employer nahi mil raha" → "Phone number try karo, ya 5 minute aur ruko"
   - "OTP nahi de raha" → "Employer ko bolo unke app mein 'Generate OTP' button hai"

RULES:
- Default Hinglish. If worker speaks Bhojpuri / Tamil / Telugu / Marathi / Bengali / Kannada / Gujarati, mirror them.
- 1-2 sentences per turn. Never lecture. Ask ONE question at a time.
- The MOMENT the worker starts speaking, STOP IMMEDIATELY and listen.
- Always confirm OTP digits BEFORE calling verify_otp_and_start — one wrong call brings them closer to a 10-minute lock after 5 wrong attempts.
- If a tool returns "error: …" — apologise once and try a different angle. Don't loop the same tool.
- After verify_otp_and_start succeeds: deliver ONE closing line, then end_conversation. No follow-up.
- Never invent shift details. If you don't know something, say so."""

CLIENT_TOOLS = [
    {
        "type": "client",
        "name": "open_employer_maps",
        "description": "Open Google Maps with directions to the employer's location for the current active shift. Use when the worker asks for directions, says they don't know the way, or wants to leave for the job.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "client",
        "name": "open_arrival_camera",
        "description": "Open the worker's selfie camera to capture and upload an arrival selfie. Use ONLY after the worker confirms they have physically reached the employer's location.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "client",
        "name": "fill_otp_digits",
        "description": "Fill the visible 4-digit OTP boxes on the worker's screen so they can see what you heard before submitting.",
        "parameters": {
            "type": "object",
            "properties": {
                "digits": {"type": "string", "description": "Exactly 4 numeric digits 0-9, e.g. '5281'."},
            },
            "required": ["digits"],
        },
    },
    {
        "type": "client",
        "name": "verify_otp_and_start",
        "description": "Submit the 4-digit arrival OTP. On success the shift transitions to IN_PROGRESS. After 5 wrong attempts the server locks the booking for 10 minutes. ALWAYS read the digits back to the worker for confirmation before calling this.",
        "parameters": {
            "type": "object",
            "properties": {
                "digits": {"type": "string", "description": "Exactly 4 numeric digits 0-9, e.g. '5281'."},
            },
            "required": ["digits"],
        },
    },
    {
        "type": "client",
        "name": "read_distance_to_employer",
        "description": "Return a short human-readable distance from the worker's current GPS to the employer's location, in metres or kilometres. Use only when the worker asks 'kitna door hai' / 'how far' / similar.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "client",
        "name": "end_conversation",
        "description": "End the Jyoti session. Call AFTER your closing line. Mandatory after verify_otp_and_start succeeds.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

FIRST_MESSAGE = "Namaste {{worker_name}}! Main Jyoti hu Switch se. Kya raasta dikhau {{employer_name}} ka?"


def _http(method: str, url: str, headers: dict, body: Optional[dict] = None, timeout: int = 30):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> None:
    if not API_KEY:
        print("❌ ELEVENLABS_API_KEY not set")
        sys.exit(1)

    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

    body = {
        "name": NAME,
        "conversation_config": {
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": "hi",
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "llm": LLM_MODEL,
                    "tools": CLIENT_TOOLS,
                    "temperature": 0.4,
                },
            },
            "tts": {
                "voice_id": VOICE_ID,
                "model_id": TTS_MODEL,
                "stability": 0.5,
                "similarity_boost": 0.8,
            },
            "asr": {
                "quality": "high",
                "provider": "elevenlabs",
                "user_input_audio_format": "pcm_16000",
            },
            "turn": {
                "turn_timeout": 7,
                "silence_end_call_timeout": -1,
            },
        },
        "platform_settings": {
            # Allow worker arrival from in-app web origin. Restrict in
            # production by setting the actual app domain.
            "auth": {"enable_auth": True, "shareable_token_count": 0},
        },
    }

    print(f"📡 Creating agent '{NAME}'…")
    status, resp_body = _http(
        "POST",
        "https://api.elevenlabs.io/v1/convai/agents/create",
        headers,
        body,
    )
    if status not in (200, 201):
        print(f"❌ Create failed: {status}\n{resp_body[:600]}")
        sys.exit(1)

    data = json.loads(resp_body)
    agent_id = data.get("agent_id") or data.get("id")
    print(f"✅ Agent created: {agent_id}")
    print()
    print("Add this to your .env.local and Railway env:")
    print(f"  ELEVENLABS_AGENT_ID={agent_id}")


if __name__ == "__main__":
    main()
