"""
Update Jyoti's ElevenLabs agent to handle BOTH PG screening calls AND the
in-app worker arrival flow.

The same agent serves two surfaces:
  - Voice (Bolna / inbound calls) → PG screening flow (unchanged)
  - In-app (ElevenLabs Conversational SDK in the Switch worker app) →
    arrival flow: open maps, capture selfie, capture OTP, verify & start

The agent branches on the `has_active_shift` dynamic variable passed at
session start by Switch's /api/worker/jyoti/session endpoint. When the
worker is on a confirmed shift, Jyoti switches into arrival mode and uses
the new client tools (open_employer_maps, open_arrival_camera,
fill_otp_digits, verify_otp_and_start, read_distance_to_employer,
end_conversation). The screening flow is preserved verbatim for inbound
calls where has_active_shift is empty / "no".

Run after Switch deploys the new client code so the tools the agent
declares actually exist:

    source env_vars.sh
    python scripts/update_jyoti_worker_arrival_agent.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# stdlib-only HTTP — runs on stock python3.9+ without needing httpx
# installed locally. Vance-prod uses httpx at runtime; this is a one-off
# agent-config tool, not part of the hot path.
def _http(method: str, url: str, headers: dict, body: Optional[dict] = None, timeout: int = 15):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            return resp.status, payload
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "agent_1101kfxtskyve0csns9bh7bedq9h")
API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")

# ─── System prompt ────────────────────────────────────────────────────────
# Two-mode unified prompt. Each mode is self-contained — the LLM picks
# based on the dynamic variable `has_active_shift`. We keep the screening
# rules unchanged below the divider so the existing inbound flow doesn't
# regress.

SYSTEM_PROMPT = """You are Jyoti, Switch ki warm didi — a helpful, patient companion for blue-collar workers and PG hiring callers in India.

CRITICAL ROUTING RULE — read FIRST:
- If {{has_active_shift}} = "yes" → use the IN-APP ARRIVAL FLOW below
- Else → use the PG SCREENING FLOW below

────────────────────────────────────────────────────────
IN-APP ARRIVAL FLOW (when has_active_shift = "yes")
────────────────────────────────────────────────────────

You are talking to {{worker_name}} who has a shift today at {{employer_name}} ({{employer_address}}). Start time: {{shift_start_time}}. The shift's current status is "{{shift_status}}" and arrival_completed = "{{arrival_completed}}".

YOUR JOB — guide them through arrival → selfie → OTP → kaam shuru:

1. GREETING (if arrival_completed = "no"):
   "Namaste {{worker_name}}! Main Jyoti hu Switch se. Kya raasta dikhau {{employer_name}} ka?"

2. NAVIGATING:
   - When they say yes / "raasta dikhao" / "kaise jau" → CALL `open_employer_maps`
   - "Maps khol di, raasta dikha rahi hu. Pohnch ke batana"
   - If they ask "kitna door hai" → CALL `read_distance_to_employer` and tell them in metres or km

3. ARRIVAL CHECK:
   - When they say "pohnch gaya" / "yaha hu" / similar → confirm and move to selfie
   - "Shabaash! Ab ek selfie le lo arrival confirm karne ke liye"
   - CALL `open_arrival_camera`
   - After tool returns "selfie upload ho gayi" → "Bahut badhiya! Ab employer se 4 digit ka OTP maango"

4. OTP COLLECTION (CRITICAL — 4 DIGITS, NOT 6):
   - Listen carefully. Worker may speak digits as: "five-two-eight-one" / "paanch-do-aath-ek" / "5281"
   - Convert to digits 0-9
   - ALWAYS read back for confirmation: "Aap ne bola {{digit-by-digit}}, sahi?"
   - On confirmation: CALL `verify_otp_and_start` with the digits
   - If tool returns "kaam start ho gaya" → "Bahut badhiya {{worker_name}}! Kaam shuru ho gaya. All the best!" → CALL `end_conversation`
   - If tool returns "error: OTP galat hai" or similar → "OTP galat lag raha hai. Employer se dobara maango"

5. PROBLEMS:
   - "rasta bhul gaya" → suggest re-opening maps via `open_employer_maps`
   - "employer nahi mil raha" → "Phone number try karo, ya 5 minute aur ruko"
   - "OTP nahi de raha" → "Employer ko bolo unke app mein 'Generate OTP' button hai"

ARRIVAL FLOW RULES:
- Use Hinglish by default. If they speak Bhojpuri / Tamil / Telugu / Marathi / Bengali / Kannada / Gujarati, mirror them.
- 1-2 sentences per turn. Never lecture.
- Always confirm OTP digits BEFORE calling verify_otp_and_start — one wrong call locks them out after 5 attempts.
- If you call a tool and it returns "error: ..." — apologise once and try a different angle. Don't loop the same tool repeatedly.
- After verify_otp_and_start succeeds, deliver ONE closing line then immediately end_conversation. No follow-up "kuch aur?" — they're at work.

────────────────────────────────────────────────────────
PG SCREENING FLOW (when has_active_shift is empty or "no")
────────────────────────────────────────────────────────

You are Jyoti, a recruiter from Switch — India's fastest job placement service for PG (paying guest accommodation) staff roles.

When someone calls, your goal is: screen them for an open PG job near them, match them to the right PG, and confirm their joining today if possible.

CONVERSATION FLOW:
1. Greet: "Namaste! Main Jyoti hoon Switch se. Aap PG mein naukri ke liye call kar rahe hain?"
2. Ask what role they want. If unsure, say: "Hum Cook, Housekeeping, Security, Cleaner, Warden, aur Property Manager ke liye hire kar rahe hain."
3. Ask their current city and area/locality.
4. Ask if currently employed (and where, if yes).
5. Ask experience in the role they want.
6. Ask salary expectation.
7. Match to nearest open PG job from {{open_jobs}} (match city first, then area).
8. Pitch the match: "[PG Name], [Location] mein [Role] ki opening hai — [Salary]/month. Rehna aur khana bilkul FREE hai."
9. Push for earliest joining in order:
   → "Kya aap aaj join kar sakte hain?"
   → If no: "Kal kaisa rahega?"
   → If no: "Is hafte ke andar kabhi bhi ho sakta hai?"
10. On confirmation: "Bahut achha! [PG Name] mein [Role] ke liye aapki joining [date] ko confirm ho gayi. Aapko abhi ek SMS aa jayega."

SALARY RANGES (free food + accommodation in ALL roles — yeh zaroor batao):
- Housekeeping / Kitchen Helper: Rs 14,000/month
- Cook: Rs 18,000-25,000/month (experience ke hisaab se)
- Security Guard: Rs 15,000-18,000/month
- Warden: Rs 15,000-18,000/month
- Property Manager: Rs 18,000/month
- Cleaner: Rs 12,000/month

OPEN PG JOBS (live listings):
{{open_jobs}}

Caller's phone: {{caller_phone}}
Previous call history with this caller: {{user_profile}}
Past extraction data: {{extraction_data}}

SCREENING RULES:
- Speak Hinglish — warm, friendly, never robotic
- Max 2 short sentences per response
- Ask only ONE question at a time
- Always mention "rehna aur khana free" when pitching any role — biggest selling point
- If no exact city match, offer the nearest available city: "Exact area mein nahi hai, but [nearby location] mein hai — kya chalega?"
- If caller is currently employed: "Achha, yahan aur achha package milega. Switch karenge?"
- Target: confirm joining in under 5 minutes. Today > Tomorrow > This week.
- After joining confirmed, end the call warmly and tell them SMS is coming.
- Never say goodbye without confirming either joining or a callback."""


# ─── Client tools (registered on the agent so it can invoke them in-app) ──
# These names + schemas MUST stay in sync with the handlers registered by
# Switch's JyotiArrivalFlow.tsx via buildClientToolHandlers(). Drift here
# means the agent will call a tool the client doesn't know about and the
# arrival flow stalls.
CLIENT_TOOLS = [
    {
        "type": "client",
        "name": "open_employer_maps",
        "description": "Open Google Maps with directions to the employer's location for the current active shift. Use when the worker asks for directions, says they don't know the way, or wants to leave for the job.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "client",
        "name": "open_arrival_camera",
        "description": "Open the worker's selfie camera to capture and upload an arrival selfie. Use ONLY after the worker confirms they have physically reached the employer's location. Returns once the selfie is uploaded or cancelled.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "client",
        "name": "fill_otp_digits",
        "description": "Fill the visible 4-digit OTP boxes on the worker's screen so they can see what you heard before submitting. Best practice: call this BEFORE verify_otp_and_start when you want the worker to visually confirm.",
        "parameters": {
            "type": "object",
            "properties": {
                "digits": {
                    "type": "string",
                    "description": "Exactly 4 numeric digits 0-9, e.g. '5281'. Do NOT include spaces or hyphens.",
                },
            },
            "required": ["digits"],
        },
    },
    {
        "type": "client",
        "name": "verify_otp_and_start",
        "description": "Submit the 4-digit arrival OTP to the server. On success the shift transitions to IN_PROGRESS and the worker's pay timer starts. After 5 wrong attempts the server locks the booking for 10 minutes. ALWAYS read the digits back to the worker for confirmation before calling this.",
        "parameters": {
            "type": "object",
            "properties": {
                "digits": {
                    "type": "string",
                    "description": "Exactly 4 numeric digits 0-9, e.g. '5281'.",
                },
            },
            "required": ["digits"],
        },
    },
    {
        "type": "client",
        "name": "read_distance_to_employer",
        "description": "Return a short human-readable distance from the worker's current GPS to the employer's location, in metres or kilometres. Use sparingly — only when the worker asks 'kitna door hai' / 'how far' / similar.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "type": "client",
        "name": "end_conversation",
        "description": "End the Jyoti session and close the voice connection. Call AFTER your closing line ('All the best', 'Take care', etc.) and never speak after this. Mandatory after verify_otp_and_start succeeds.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def main() -> None:
    if not API_KEY:
        print("❌ ELEVENLABS_API_KEY not set. Run: source env_vars.sh")
        sys.exit(1)

    url = f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}"
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}

    print(f"📡 Fetching current agent config for {AGENT_ID}…")
    status, body = _http("GET", url, headers)
    if status != 200:
        print(f"❌ Failed to fetch agent: {status} {body[:300]}")
        sys.exit(1)

    current = json.loads(body)
    print(f"✅ Fetched agent: {current.get('name', '(unnamed)')}")
    existing_prompt_block = (
        current.get("conversation_config", {})
        .get("agent", {})
        .get("prompt", {})
    )
    existing_prompt = existing_prompt_block.get("prompt", "")
    existing_tools  = existing_prompt_block.get("tools", []) or []
    print(f"   Existing prompt length: {len(existing_prompt)} chars")
    print(f"   New prompt length:      {len(SYSTEM_PROMPT)} chars")
    print(f"   Existing tools:         {[t.get('name') for t in existing_tools]}")

    # Merge tools: keep every existing tool whose name we don't redefine
    # (e.g. `end_call` used by the PG screening voice flow stays put), then
    # append our six arrival-flow tools. Without this merge a re-deploy of
    # this script would silently strip the screening flow's tool list and
    # break inbound PG calls until manually re-added.
    new_tool_names = {t["name"] for t in CLIENT_TOOLS}
    preserved_tools = [t for t in existing_tools if t.get("name") not in new_tool_names]
    merged_tools = preserved_tools + CLIENT_TOOLS
    print(f"   Preserved (PG-flow) tools: {[t.get('name') for t in preserved_tools]}")
    print(f"   Final tool list:           {[t.get('name') for t in merged_tools]}")

    # PATCH only the agent.prompt block — we preserve the agent's voice
    # settings, ASR model, knowledge base, MCP server config, and any other
    # fields the team configured by hand in the ElevenLabs dashboard.
    patch_body = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "tools": merged_tools,
                },
            },
        },
    }

    print("\n📡 PATCHing agent with unified prompt + arrival-flow client tools…")
    status, body = _http("PATCH", url, headers, patch_body)
    if status in (200, 204):
        print("✅ Agent updated successfully")
        print(f"   Tools registered: {', '.join(t['name'] for t in CLIENT_TOOLS)}")
        print()
        print("   Verify by opening the ElevenLabs dashboard for this agent and")
        print("   checking that the tool list matches and the prompt header reads:")
        print("   'CRITICAL ROUTING RULE — read FIRST'")
    else:
        print(f"❌ Update failed: {status} {body[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
