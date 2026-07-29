"""
Register WhatsApp AUTHENTICATION template for Switch OTP.

Run on the server where env vars are loaded:
  source env_vars.sh && python scripts/register_switch_otp_template.py

Authentication templates:
- Bypass the 24-hour messaging window
- Auto-approved by Meta (near-instant)
- Body text is Meta-controlled: "{{1}} is your verification code."
"""

import os
import sys
import requests

META_TOKEN = os.environ["META_SYS_USER_TOKEN"]
PHONE_NUMBER_ID = os.environ.get("SWITCH_PHONE_NUMBER_ID", "937143829489912")

HEADERS = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
GQL = "https://graph.facebook.com/v21.0"


def get_waba_id():
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
        print("Response:", data)
        sys.exit("Could not get WABA ID")
    print(f"WABA ID: {waba_id}")
    return waba_id


def register_template(waba_id: str):
    payload = {
        "name": "switch_otp",
        "language": "en",
        "category": "AUTHENTICATION",
        "components": [
            {
                "type": "BODY",
                "add_security_recommendation": True,
            },
            {
                "type": "FOOTER",
                "code_expiration_minutes": 5,
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "OTP",
                        "otp_type": "COPY_CODE",
                        "text": "Copy Code",
                    }
                ],
            },
        ],
    }

    r = requests.post(
        f"{GQL}/{waba_id}/message_templates",
        json=payload,
        headers=HEADERS,
        timeout=15,
    )
    data = r.json()
    print(f"Status: {r.status_code}")
    print(f"Response: {data}")

    if r.status_code in (200, 201) and "id" in data:
        print(f"\nTemplate registered! ID: {data['id']}  Status: {data.get('status')}")
        print("Authentication templates are usually auto-approved within seconds.")
    elif "error" in data:
        code = data["error"].get("code")
        msg = data["error"].get("message", "")
        if code == 100 and "already exists" in msg.lower():
            print("\nTemplate 'switch_otp' already exists — nothing to do.")
        else:
            sys.exit(f"Failed: {data['error']}")


def check_template_status(waba_id: str):
    r = requests.get(
        f"{GQL}/{waba_id}/message_templates",
        params={"name": "switch_otp"},
        headers=HEADERS,
        timeout=10,
    )
    data = r.json()
    templates = data.get("data", [])
    if not templates:
        print("Template not found yet.")
        return
    for t in templates:
        print(f"  name={t['name']}  status={t['status']}  language={t.get('language')}  id={t['id']}")


if __name__ == "__main__":
    print("=== Step 1: Get WABA ID ===")
    waba_id = get_waba_id()

    print("\n=== Step 2: Register template ===")
    register_template(waba_id)

    print("\n=== Step 3: Check status ===")
    check_template_status(waba_id)
