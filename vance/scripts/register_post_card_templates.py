"""
Register all WhatsApp templates for the post-card automated placement pipeline.

Run once (idempotent — skips already-existing templates):
    source env_vars.sh && python -m scripts.register_post_card_templates

All templates are UTILITY — Meta requires verified display name for MARKETING.
Utility templates approve within minutes.

After approval, run with --status to check all template statuses.
"""

import os
import sys
import time
import argparse
import requests

META_TOKEN = os.environ.get("META_SYS_USER_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("SWITCH_PHONE_NUMBER_ID", "990475317490297")
WABA_ID_ENV = os.environ.get("SWITCH_WABA_ID", "")
GQL = "https://graph.facebook.com/v21.0"
HEADERS = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}

if not META_TOKEN:
    sys.exit("META_SYS_USER_TOKEN not set — source env_vars.sh first")


# ── Template definitions ──────────────────────────────────────────────────────
#
# Button payloads are ALL_CAPS fixed strings. The webhook receives these in
# button_reply.id. Placement is found by the sender's phone, not by ID in payload.
#
# Variable examples must be realistic — Meta reviewers read them.

TEMPLATES = [

    # ── Step 1: Job confirmed ─────────────────────────────────────────────────
    # NOTE: Step 1 now uses a WhatsApp TEXT message (not a template).
    # Workers are always in the 24-hour session window at placement time.
    # The text message contains all details + OTP. No template needed here.

    # ── Step 2: Evening confirmation ──────────────────────────────────────────
    {
        "name": "switch_evening_confirm",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Joining reminder: {{1}} ji, कल सुबह {{2}} बजे {{3}} में join करना है 🟢\n\n"
                    "कल आ रहे हो?"
                ),
                "example": {
                    "body_text": [["Rahul", "09:00 AM", "Reliance Mart"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "हाँ"},
                    {"type": "QUICK_REPLY", "text": "Cancel"},
                ],
            },
        ],
    },

    # ── Step 3: Morning nudge ─────────────────────────────────────────────────
    {
        "name": "sw_report_today",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "Switch reminder: {{1}} ji, aaj {{2}} baje {{3}} pahunchna hai 🟢\n\nNikal gaye?",
                "example": {
                    "body_text": [["Rahul", "09:00 AM", "Reliance Mart"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Haan nikal gaya"},
                    {"type": "QUICK_REPLY", "text": "Thodi der mein"},
                    {"type": "QUICK_REPLY", "text": "Nahi aa sakta"},
                ],
            },
        ],
    },

    # ── Step 4: En-route check ────────────────────────────────────────────────
    {
        "name": "switch_enroute_check",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "⏰ {{1}} ji, {{2}} बजे {{3}} पहुँचना है\n\nनिकल गए?",
                "example": {
                    "body_text": [["Rahul", "09:00 AM", "Reliance Mart"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "हाँ, निकल गया"},
                    {"type": "QUICK_REPLY", "text": "अभी निकलूँगा"},
                    {"type": "QUICK_REPLY", "text": "नहीं आऊँगा"},
                ],
            },
        ],
    },

    # ── Step 5: Employer notification (worker en route) ───────────────────────
    {
        "name": "sw_employer_eta",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "Worker update: {{1}} is heading to your location.\n\nETA: {{2}}\n\nAll set to receive?",
                "example": {
                    "body_text": [["Rahul Kumar", "09:00 AM"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Ready"},
                    {"type": "QUICK_REPLY", "text": "Need help"},
                ],
            },
        ],
    },

    # ── Step 6a: Worker check-in confirmed ───────────────────────────────────
    {
        "name": "sw_checkin_done",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Check-in confirmed: {{1}} ji, aapka check-in ho gaya hai.\n\n"
                    "Travel reimbursement: Rs.200 aapke account mein bheja jayega.\n\n"
                    "Koi samasya ho toh yahan reply karein."
                ),
                "example": {
                    "body_text": [["Rahul"]]
                },
            }
        ],
    },

    # ── Step 6b: Employer placement fee ──────────────────────────────────────
    {
        "name": "switch_placement_fee",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "✅ {{1}} check-in confirmed at {{2}}!\n\n"
                    "Placement fee ₹2,000:\n"
                    "👉 {{3}}\n\n"
                    "Cash payment? Reply: *cash paid*"
                ),
                "example": {
                    "body_text": [[
                        "Rahul Kumar",
                        "Reliance Mart",
                        "https://app.switchlocally.com/pay/123",
                    ]]
                },
            }
        ],
    },

    # ── Step 7: Replacement urgent offer ─────────────────────────────────────
    {
        "name": "switch_replacement_urgent_u",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Job opening: {{1}} mein {{2}} ki zaroorat hai.\n\n"
                    "Salary: Rs.{{3}}/month\n"
                    "Location: {{4}} ({{5}} km)\n"
                    "Joining time: Aaj {{6}}\n\n"
                    "Kya aap join kar sakte hain?"
                ),
                "example": {
                    "body_text": [[
                        "Reliance Mart",
                        "Store Helper",
                        "12000",
                        "Sector 29, Gurugram",
                        "2.3",
                        "11:00 AM",
                    ]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "हाँ, आऊँगा"},
                    {"type": "QUICK_REPLY", "text": "नहीं"},
                ],
            },
        ],
    },

    # ── Step 8 Day 1: First day feedback ─────────────────────────────────────
    {
        "name": "switch_retention_day1",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "Pehla din: {{1}} ji, {{2}} mein kaisa raha? 😊",
                "example": {
                    "body_text": [["Rahul", "Reliance Mart"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Accha raha"},
                    {"type": "QUICK_REPLY", "text": "Theek tha"},
                    {"type": "QUICK_REPLY", "text": "Accha nahi"},
                ],
            },
        ],
    },

    # ── Step 8 Day 1: Employer feedback ──────────────────────────────────────
    {
        "name": "switch_employer_day1",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "Worker update: {{1}}'s first day at {{2}} is done. How did it go?",
                "example": {
                    "body_text": [["Rahul Kumar", "Reliance Mart"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Went well"},
                    {"type": "QUICK_REPLY", "text": "Had issues"},
                ],
            },
        ],
    },

    # ── Step 8 Day 3 ─────────────────────────────────────────────────────────
    {
        "name": "sw_attendance_day3",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Attendance confirmation: {{1}} ji, {{2}} mein aapka 3rd din complete hua.\n\n"
                    "Koi samasya ho toh yahan reply karein."
                ),
                "example": {
                    "body_text": [["Rahul", "Reliance Mart"]]
                },
            }
        ],
    },

    # ── Step 8 Day 7 ─────────────────────────────────────────────────────────
    {
        "name": "sw_attendance_week1",
        "language": "hi",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Week 1 update: {{1}} ji, {{2}} mein pehla hafta complete hua.\n\n"
                    "Kaam jaari hai?"
                ),
                "example": {
                    "body_text": [["Rahul", "Reliance Mart"]]
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Haan, jaari hai"},
                    {"type": "QUICK_REPLY", "text": "Theek hai"},
                    {"type": "QUICK_REPLY", "text": "Chhod diya"},
                ],
            },
        ],
    },
]


# ── API helpers ───────────────────────────────────────────────────────────────

def get_waba_id() -> str:
    r = requests.get(
        f"{GQL}/{PHONE_NUMBER_ID}",
        params={"fields": "whatsapp_business_account_id"},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    waba_id = data.get("whatsapp_business_account_id")
    if not waba_id:
        sys.exit(f"Could not get WABA ID — response: {data}")
    return waba_id


def register_one(waba_id: str, tpl: dict) -> dict:
    """Submit one template. Returns {name, status, id, error}."""
    name = tpl["name"]
    for attempt in range(3):
        try:
            r = requests.post(
                f"{GQL}/{waba_id}/message_templates",
                json=tpl,
                headers=HEADERS,
                timeout=30,
            )
            break
        except requests.exceptions.Timeout:
            if attempt == 2:
                return {"name": name, "id": None, "status": "FAILED", "error": "Request timed out after 3 attempts"}
            time.sleep(5)
    else:
        return {"name": name, "id": None, "status": "FAILED", "error": "Request timed out"}

    data = r.json()

    if r.status_code in (200, 201) and "id" in data:
        return {"name": name, "id": data["id"], "status": data.get("status", "PENDING"), "error": None}

    err = data.get("error", {})
    code = err.get("code")
    msg = err.get("message", str(data))
    user_title = err.get("error_user_title", "")
    user_msg = err.get("error_user_msg", "")
    combined = f"{msg} {user_title} {user_msg}".lower()

    if code == 100 and "already exists" in combined:
        return {"name": name, "id": None, "status": "ALREADY_EXISTS", "error": None}

    detail = user_msg or user_title or msg
    return {"name": name, "id": None, "status": "FAILED", "error": detail}


def check_all_statuses(waba_id: str):
    template_names = {t["name"] for t in TEMPLATES}
    r = requests.get(
        f"{GQL}/{waba_id}/message_templates",
        params={"limit": 100},
        headers=HEADERS,
        timeout=10,
    )
    data = r.json().get("data", [])
    rows = [t for t in data if t["name"] in template_names]

    print(f"\n{'NAME':<35} {'STATUS':<15} {'CATEGORY':<12} {'LANG'}")
    print("-" * 72)
    for t in sorted(rows, key=lambda x: x["name"]):
        print(f"{t['name']:<35} {t['status']:<15} {t.get('category',''):<12} {t.get('language','')}")

    found = {t["name"] for t in rows}
    missing = template_names - found
    if missing:
        print(f"\nNot found yet: {', '.join(sorted(missing))}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="Only check statuses, skip registration")
    parser.add_argument("--waba-id", default="", help="WhatsApp Business Account ID (overrides SWITCH_WABA_ID env var)")
    args = parser.parse_args()

    waba_id = args.waba_id or WABA_ID_ENV
    if not waba_id:
        print("Getting WABA ID via API…")
        try:
            waba_id = get_waba_id()
        except Exception as e:
            print(f"Could not auto-fetch WABA ID: {e}")
            print("\nSet it manually:")
            print("  export SWITCH_WABA_ID=<your-waba-id>")
            print("  python -m scripts.register_post_card_templates")
            print("\nFind your WABA ID at: Meta Business Manager → WhatsApp Manager → Account")
            sys.exit(1)
    print(f"WABA ID: {waba_id}\n")

    if args.status:
        check_all_statuses(waba_id)
        return

    results = []
    for tpl in TEMPLATES:
        print(f"  Registering {tpl['name']} ({tpl['category']})…", end=" ", flush=True)
        result = register_one(waba_id, tpl)
        results.append(result)
        if result["error"]:
            print(f"FAILED — {result['error']}")
        else:
            print(result["status"])
        time.sleep(0.3)

    print(f"\n{'NAME':<35} {'RESULT':<15} {'ID'}")
    print("-" * 65)
    for r in results:
        tid = r["id"] or "-"
        err = f"  ← {r['error']}" if r["error"] else ""
        print(f"{r['name']:<35} {r['status']:<15} {tid}{err}")

    failed = [r for r in results if r["error"]]
    if failed:
        print(f"\n{len(failed)} template(s) failed. Check errors above.")
    else:
        print(f"\nAll {len(results)} templates submitted.")
        print("All templates are UTILITY — should approve within minutes.")
        print("\nCheck status: python -m scripts.register_post_card_templates --status")


if __name__ == "__main__":
    main()
