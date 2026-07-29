"""
Fast2SMS integration for sending SMS notifications.

Used for PG joining confirmation SMS to candidates and admin alerts.
API key: FAST2SMS_API_KEY env var
"""

import os

import httpx

FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"


def _normalize_number(phone: str) -> str:
    """Return 10-digit Indian mobile number (no country code) for Fast2SMS."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    return cleaned


def send_sms(phone: str, message: str) -> bool:
    """
    Send SMS via Fast2SMS quick route.

    Args:
        phone: Indian mobile number (any format — +91, 91, or 10-digit)
        message: SMS text (keep under 160 chars for single SMS)

    Returns:
        True if Fast2SMS accepted the message, False otherwise.
    """
    api_key = os.getenv("FAST2SMS_API_KEY", "")
    if not api_key:
        print("❌ [FAST2SMS] No FAST2SMS_API_KEY configured")
        return False

    number = _normalize_number(phone)
    if len(number) != 10:
        print(f"❌ [FAST2SMS] Invalid phone number: {phone!r} → {number!r}")
        return False

    try:
        resp = httpx.post(
            FAST2SMS_URL,
            headers={"authorization": api_key},
            json={
                "route": "q",
                "numbers": number,
                "message": message,
                "language": "english",
                "flash": 0,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("return") is True:
            print(f"✅ [FAST2SMS] SMS sent to {number}")
            return True
        else:
            print(f"❌ [FAST2SMS] Rejected: {data}")
            return False
    except Exception as e:
        print(f"❌ [FAST2SMS] Error sending to {number}: {e}")
        return False
