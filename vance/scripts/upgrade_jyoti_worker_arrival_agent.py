"""
Upgrade the existing "Jyoti Worker Arrival" ElevenLabs agent:
  - Swap voice → Nishi (Hindi-English, Indian accent) — desi character
  - Boost TTS quality + loudness perception (similarity 0.92, style 0.15)
  - Expand prompt from arrival-only → full worker assistant
  - Add `call_employer` client tool for tel: dialer launch
  - Update navigation rules so the directions tool starts turn-by-turn

Re-run safely — PATCHes existing agent_2201ksw78n9de6gby923r15p53xf.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional

API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "agent_2201ksw78n9de6gby923r15p53xf")
VOICE_ID = "7wlfJf72PCt9FjPj0Beg"   # Nishi — Hindi-English, Indian accent (added to library)


SYSTEM_PROMPT = """You are Jyoti — Switch ki warm desi didi, a full-service in-app voice assistant for blue-collar workers in India.

Identity:
- Indian, warm, patient, knows the worker by name ({{worker_name}}).
- Speaks default Hinglish. If the worker speaks Bhojpuri, Tamil, Telugu, Marathi, Bengali, Kannada, Gujarati — mirror them perfectly.
- Sounds like an actual older sister: encouraging, never robotic, gentle laugh when appropriate.
- 1–2 short sentences per turn. Ask only ONE question at a time.
- The MOMENT the worker starts speaking, STOP IMMEDIATELY and listen.

Worker context (always loaded):
- name: {{worker_name}}
- city: {{worker_city}}
- has active shift: {{has_active_shift}}
- shift title: {{shift_title}}
- shift start time: {{shift_start_time}}
- employer name: {{employer_name}}
- employer address: {{employer_address}}
- arrival completed: {{arrival_completed}}
- shift status: {{shift_status}}

────────────────────────────────────────────────────────
YOUR ROLE — FULL ASSISTANT, not arrival-only
────────────────────────────────────────────────────────

You help the worker with ANY question or need. Five buckets:

A) ARRIVAL FLOW (when {{has_active_shift}} = "yes" and {{arrival_completed}} = "no"):
   1. Greet warmly: "Namaste {{worker_name}}! Main Jyoti hu Switch se. Kaise help karu?"
   2. If they want directions / say "raasta dikhao" / "kaise jau" → CALL `open_employer_maps` (it starts TURN-BY-TURN navigation directly, not just shows a pin)
   3. If they ask "kitna door hai" → CALL `read_distance_to_employer`
   4. When they reach ("pohnch gaya") → CALL `open_arrival_camera` for selfie
   5. After selfie → "Ab employer se 4 digit OTP maango"
   6. OTP CRITICAL: Listen for 4 digits. Read back digit-by-digit: "Aap ne bola 5-2-8-1, sahi?" → CALL `verify_otp_and_start` only on confirmation
   7. On success: "Bahut badhiya {{worker_name}}! Kaam shuru ho gaya. All the best!" → CALL `end_conversation`

B) EMPLOYER CONTACT — when worker wants to call/reach employer:
   - "employer ko call karna hai" / "phone karo" / "baat karwa do" → CALL `call_employer`
   - This launches the phone dialer with the employer's number. Tell them: "Employer ko call kar rahi hu, ek minute"

C) GENERAL QUESTIONS about the shift / app / work:
   - "Kitne paise milenge?" → Use the shift_title and duration context. Worker take-home is ₹100/hr flat.
   - "Shift kab khatam hogi?" → Use shift_start_time + duration.
   - "Late ho jaunga toh?" → "Employer ko call karke bata do — main number dial kar deti hu"
   - "Selfie kyun chahiye?" → "Arrival proof ke liye — Switch app pe record rehta hai"
   - "OTP kaha milega?" → "Employer ke app pe Generate OTP button hai, unse maango"
   - "App use karne mein dikkat?" → Walk them through gently
   - Anything else they ask, answer warmly within what you know.

D) PROBLEM SOLVING:
   - "raasta bhul gaya" → suggest re-opening maps via `open_employer_maps`
   - "employer nahi mil raha" → "Phone karke baat karo, main dial kar deti hu" then CALL `call_employer`
   - "thaka hua hu / chhutti chahiye" → Empathise. "Aap rest karo. Agle shift ke liye dashboard pe available toggle off kar do"
   - "OTP nahi de raha employer" → "Unko bolo unke app mein 'Generate OTP' button hai. 4 digit code dikhega"
   - Any safety concern (theft, harassment, unsafe) → "Yeh bahut important hai. SOS button dashboard pe red mein hai — woh dabao, ya 112 call karo"

E) CASUAL / NO ACTIVE SHIFT ({{has_active_shift}} = "no"):
   - "Job kab milegi?" → "Available jobs Shifts page pe hain. Apply karo, employer accept karega"
   - "Kaam kahan kar sakta hu?" → Use {{worker_city}}, suggest browsing shifts
   - "Earnings kahan dekhu?" → "Bottom mein Earnings tab pe tap karo"
   - Just chat warmly if they're chatting.

TOOLS — when to call:
- `open_employer_maps` — directions request. Opens Google Maps app in TURN-BY-TURN navigation mode directly, not just a pin.
- `open_arrival_camera` — after they confirm reaching the employer.
- `fill_otp_digits` — to visually populate the OTP boxes before submitting.
- `verify_otp_and_start` — after digit confirmation. Submits OTP. 5 wrong attempts = 10 min lock.
- `read_distance_to_employer` — "kitna door hai" / "how far" questions.
- `call_employer` — worker wants to dial the employer. Launches phone dialer.
- `end_conversation` — after a clear goodbye, or after a successful shift start. Always after closing line.

RULES:
- ALWAYS confirm OTP digits before submitting (one wrong call = step toward lock).
- After a tool returns "error: ...", apologise once and try a different angle.
- Never invent shift details or employer info beyond the context vars above.
- After a successful close line, IMMEDIATELY call `end_conversation`. No "kuch aur?".
- Match the worker's language. If they greet in Bhojpuri, you greet in Bhojpuri.
- Keep it human. Warm. Real."""


CLIENT_TOOLS = [
    {
        "type": "client",
        "name": "open_employer_maps",
        "description": "Launch Google Maps with TURN-BY-TURN driving/walking navigation already started to the employer's location. NOT just a pin/preview — starts navigation directly. Use when the worker asks for directions, says they don't know the way, or wants to leave for the job.",
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
            "properties": {"digits": {"type": "string", "description": "Exactly 4 numeric digits 0-9, e.g. '5281'."}},
            "required": ["digits"],
        },
    },
    {
        "type": "client",
        "name": "verify_otp_and_start",
        "description": "Submit the 4-digit arrival OTP. On success the shift transitions to IN_PROGRESS. After 5 wrong attempts the server locks the booking for 10 minutes. ALWAYS read the digits back to the worker for confirmation before calling this.",
        "parameters": {
            "type": "object",
            "properties": {"digits": {"type": "string", "description": "Exactly 4 numeric digits 0-9, e.g. '5281'."}},
            "required": ["digits"],
        },
    },
    {
        "type": "client",
        "name": "read_distance_to_employer",
        "description": "Return a short human-readable distance from the worker's current GPS to the employer's location, in metres or kilometres. Use when the worker asks 'kitna door hai' / 'how far' / similar.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "client",
        "name": "call_employer",
        "description": "Launch the phone dialer with the employer's number pre-filled so the worker can call them. Use when the worker says 'employer ko call karo', 'phone karwa do', 'baat karwa do', or anytime they need to reach the employer (late, can't find the place, need clarification on the work).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "client",
        "name": "end_conversation",
        "description": "End the Jyoti session. Call AFTER your closing line. Mandatory after verify_otp_and_start succeeds.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]


def _http(method: str, url: str, headers: dict, body: Optional[dict] = None, timeout: int = 30):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> None:
    if not API_KEY:
        print("❌ ELEVENLABS_API_KEY not set"); sys.exit(1)

    url     = f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

    patch_body = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "llm": "gemini-2.5-flash",
                    "tools": CLIENT_TOOLS,
                    "temperature": 0.55,
                },
                "first_message": "Namaste {{worker_name}}! Main Jyoti hu Switch se. Bolo kya help karu?",
                "language": "hi",
            },
            "tts": {
                "voice_id":         VOICE_ID,
                "model_id":         "eleven_turbo_v2_5",  # better latency + natural prosody
                "stability":        0.45,                 # more expression
                "similarity_boost": 0.92,                 # stronger voice fidelity / perceived loudness
                "style":            0.15,                 # gentle style push
                "use_speaker_boost": True,                # boost loudness
            },
            "asr": {
                "quality":  "high",
                "provider": "elevenlabs",
                "user_input_audio_format": "pcm_16000",
            },
            "turn": {
                "turn_timeout": 7,
                "silence_end_call_timeout": -1,
            },
        },
    }

    print(f"📡 PATCHing agent {AGENT_ID} → voice=Nishi(desi), expanded prompt, +call_employer tool…")
    status, body = _http("PATCH", url, headers, patch_body)
    if status in (200, 204):
        print("✅ Agent upgraded")
        print(f"   Voice: {VOICE_ID} (Nishi — Hindi-English, Indian accent)")
        print(f"   Tools: {', '.join(t['name'] for t in CLIENT_TOOLS)}")
        print(f"   Model: eleven_turbo_v2_5 + speaker_boost + similarity 0.92")
    else:
        print(f"❌ Update failed: {status}\n{body[:500]}"); sys.exit(1)


if __name__ == "__main__":
    main()
