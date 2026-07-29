"""
Employer Slot Matching Service — matches candidates to interview slots and sends notifications.

Uses switch_caller_memory profiles to find candidates matching an employer's
interview slot by city, role, salary, and availability. Sends WhatsApp messages
to both candidates (interview details) and employer (candidate list).
"""

import os
import time

from twilio.rest import Client as TwilioClient

from utils.db import fs
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


# Reuse matching constants from live_connect_service
CATEGORY_ALIASES: dict[str, list[str]] = {
    "Housekeeping": ["cleaner", "safai", "office boy", "laundry", "housekeeping"],
    "Field Sales": ["sales", "field executive", "field sales"],
    "Warehouse / Logistics": ["packing", "picker", "loader", "warehouse", "logistics", "godown", "storekeeper", "inventory"],
    "Security Guard": ["guard", "security", "watchman", "chowkidar"],
    "Delivery": ["delivery boy", "delivery executive", "delivery", "courier", "rider", "zomato", "swiggy", "blinkit"],
    "Labour/Helper": [
        "helper", "labour", "mazdoor", "labor",
        "waiter", "cook", "chef", "captain", "steward", "kitchen", "restaurant", "hotel",
    ],
    "Manufacturing": ["factory", "welder", "machine operator", "manufacturing", "fitter", "operator", "technician", "mechanic"],
    "Driver": ["driver", "chalak", "chauffeur", "auto"],
    "Sales / Business Development": ["telecaller", "telesales", "sales executive", "bde", "business development", "customer support"],
}

CITY_ALIASES: dict[str, list[str]] = {
    "Delhi": ["delhi", "new delhi", "north delhi", "south delhi", "east delhi", "west delhi", "dilli"],
    "Gurgaon": ["gurgaon", "gurugram", "ggn"],
}


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


def _city_matches(candidate_city: str, slot_city: str) -> bool:
    """Check if candidate city matches slot city (including aliases)."""
    if not candidate_city or not slot_city:
        return False

    c_lower = candidate_city.lower().strip()
    s_lower = slot_city.lower().strip()

    # Direct match
    if c_lower == s_lower:
        return True

    # Check aliases
    for canonical, aliases in CITY_ALIASES.items():
        c_in = c_lower == canonical.lower() or any(a in c_lower for a in aliases)
        s_in = s_lower == canonical.lower() or any(a in s_lower for a in aliases)
        if c_in and s_in:
            return True

    return False


def _role_matches(candidate_role: str, slot_category: str, slot_title: str) -> bool:
    """Check if candidate's desired role matches slot's category or title."""
    if not candidate_role:
        return False

    c_lower = candidate_role.lower().strip()

    # Direct match against title
    if slot_title and (c_lower in slot_title.lower() or slot_title.lower() in c_lower):
        return True

    # Check against category aliases
    if slot_category:
        s_lower = slot_category.lower().strip()
        for category, aliases in CATEGORY_ALIASES.items():
            cat_lower = category.lower()
            # Check if slot category matches this category
            slot_match = s_lower == cat_lower or any(a in s_lower for a in aliases)
            # Check if candidate role matches this category
            cand_match = c_lower == cat_lower or any(a in c_lower for a in aliases)
            if slot_match and cand_match:
                return True

    return False


def match_candidates_to_slot(slot: dict, limit: int = 10) -> list[dict]:
    """
    Find candidates matching an interview slot.
    Scores candidates by city, role, salary, availability, and profile completeness.

    Returns top `limit` candidates with score >= 30.
    """
    slot_city = slot.get("city", "")
    slot_category = slot.get("job_category", "")
    slot_title = slot.get("job_title", "")
    slot_salary_max = slot.get("salary_max", 0) or 0

    candidates = []
    docs = fs.collection("switch_caller_memory").stream()

    for doc in docs:
        data = doc.to_dict()
        profile = data.get("profile")
        if not profile:
            continue

        phone = data.get("phone", doc.id)
        score = 0

        # City match: +30
        candidate_city = profile.get("city", "")
        if _city_matches(candidate_city, slot_city):
            score += 30

        # Role match: +30
        candidate_role = profile.get("desired_role", "")
        candidate_roles = profile.get("desired_roles", [])
        role_matched = _role_matches(candidate_role, slot_category, slot_title)
        if not role_matched and candidate_roles:
            for r in candidate_roles:
                if _role_matches(r, slot_category, slot_title):
                    role_matched = True
                    break
        if role_matched:
            score += 30

        # Salary compatible: +20
        candidate_salary_min = profile.get("salary_min", 0) or 0
        if slot_salary_max > 0:
            if candidate_salary_min == 0 or candidate_salary_min <= slot_salary_max:
                score += 20
        else:
            score += 10

        # Availability: +10
        availability = (profile.get("availability", "") or "").lower()
        if availability in ("immediate", "1 week"):
            score += 10

        # Profile completeness: +10 scaled
        completeness = profile.get("profile_completeness", 0) or 0
        score += int(10 * completeness / 100)

        if score >= 30:
            candidates.append({
                "phone": phone,
                "name": profile.get("name", ""),
                "city": candidate_city,
                "desired_role": candidate_role,
                "experience_level": profile.get("experience_level", ""),
                "salary_min": candidate_salary_min,
                "availability": availability,
                "profile_completeness": completeness,
                "score": score,
            })

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:limit]


def _send_sms(to_phone: str, body: str) -> bool:
    """Send an SMS via Twilio. Returns True on success."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not from_number:
        print(f"❌ [EMP_MATCH] Twilio not configured, skipping SMS")
        return False

    phone = to_phone
    if not phone.startswith("+"):
        phone = "+91" + phone if not phone.startswith("91") else "+" + phone

    try:
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(body=body, from_=from_number, to=phone)
        print(f"✅ [EMP_MATCH] SMS sent to {phone} — SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ [EMP_MATCH] Failed to send SMS to {phone}: {e}")
        return False


def notify_candidate_whatsapp(candidate: dict, slot: dict) -> bool:
    """Send interview details to a candidate via WhatsApp (SMS fallback)."""
    phone = candidate.get("phone", "")
    if not phone:
        return False

    company = slot.get("company", "")
    job_title = slot.get("job_title", "")
    interview_date = slot.get("interview_date", "")
    interview_time = slot.get("interview_time", "")
    interview_address = slot.get("interview_address", "")
    contact_person = slot.get("contact_person", "")
    requirements = slot.get("requirements", "")

    msg_parts = [
        "Switch - Interview Details!\n",
        f"{company} mein {job_title} ke liye interview:",
    ]
    if interview_date:
        msg_parts.append(f"Date: {interview_date}")
    if interview_time:
        msg_parts.append(f"Time: {interview_time}")
    if interview_address:
        msg_parts.append(f"Address: {interview_address}")
    if contact_person:
        msg_parts.append(f"Contact: {contact_person}")
    if requirements:
        msg_parts.append(f"\n{requirements}")
    msg_parts.append("\n- Jyoti, Switch")

    msg = "\n".join(msg_parts)

    try:
        sender = WhatsAppSender()
        result = sender.send(data=MsgComponents.text_scaffold(to=phone, text=msg))
        if isinstance(result, dict) and result.get("status") == "success":
            print(f"✅ [EMP_MATCH] WhatsApp sent to candidate {phone}")
            return True
        else:
            print(f"⚠️ [EMP_MATCH] WhatsApp failed for {phone}, trying SMS")
            return _send_sms(phone, msg)
    except Exception as e:
        print(f"⚠️ [EMP_MATCH] WhatsApp error for {phone}: {e}, trying SMS")
        return _send_sms(phone, msg)


def notify_employer_whatsapp(slot: dict, candidates: list[dict]) -> bool:
    """Send candidate list to employer via WhatsApp (SMS fallback)."""
    phone = slot.get("employer_phone", "")
    if not phone:
        return False

    job_title = slot.get("job_title", "")
    interview_date = slot.get("interview_date", "")
    interview_time = slot.get("interview_time", "")

    msg_parts = [
        "Switch - Candidates aa rahe hain!\n",
        f"{job_title} ke liye {len(candidates)} candidates:",
    ]

    for i, c in enumerate(candidates, 1):
        name = c.get("name", "Candidate")
        exp = c.get("experience_level", "")
        c_phone = c.get("phone", "")
        exp_text = f" - {exp}" if exp else ""
        msg_parts.append(f"{i}. {name}{exp_text} - Phone: {c_phone}")

    if interview_date or interview_time:
        time_parts = []
        if interview_date:
            time_parts.append(interview_date)
        if interview_time:
            time_parts.append(interview_time)
        msg_parts.append(f"\nYe log {' '.join(time_parts)} ko aayenge.")

    msg_parts.append("\n- Jyoti, Switch")
    msg = "\n".join(msg_parts)

    try:
        sender = WhatsAppSender()
        result = sender.send(data=MsgComponents.text_scaffold(to=phone, text=msg))
        if isinstance(result, dict) and result.get("status") == "success":
            print(f"✅ [EMP_MATCH] WhatsApp sent to employer {phone}")
            return True
        else:
            print(f"⚠️ [EMP_MATCH] WhatsApp failed for employer {phone}, trying SMS")
            return _send_sms(phone, msg)
    except Exception as e:
        print(f"⚠️ [EMP_MATCH] WhatsApp error for employer {phone}: {e}, trying SMS")
        return _send_sms(phone, msg)


def match_and_notify(slot_id: str) -> dict:
    """
    Full matching + notification pipeline for an interview slot.

    1. Read slot from Firestore
    2. Validate status is "pending" and employer_agreed
    3. Match candidates
    4. Send WhatsApp to each candidate and employer
    5. Update slot status to "notified"
    """
    doc_ref = fs.collection("interview_slots").document(slot_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError(f"Slot {slot_id} not found")

    slot = doc.to_dict()

    if slot.get("status") != "pending":
        raise ValueError(f"Slot {slot_id} status is '{slot.get('status')}', expected 'pending'")

    if not slot.get("employer_agreed", True):
        raise ValueError(f"Slot {slot_id}: employer did not agree to receive candidates")

    # Match candidates
    candidates = match_candidates_to_slot(slot)
    print(f"📋 [EMP_MATCH] Matched {len(candidates)} candidates for slot {slot_id}")

    if not candidates:
        doc_ref.update({
            "status": "no_matches",
            "matched_at": time.time(),
            "matched_candidates": [],
        })
        return {"slot_id": slot_id, "matched": 0, "notified_candidates": 0, "notified_employer": False}

    # Notify candidates
    notified_count = 0
    for candidate in candidates:
        if notify_candidate_whatsapp(candidate, slot):
            notified_count += 1

    # Notify employer
    employer_notified = notify_employer_whatsapp(slot, candidates)

    # Update slot in Firestore
    matched_data = []
    for c in candidates:
        matched_data.append({
            "phone": c["phone"],
            "name": c["name"],
            "score": c["score"],
            "experience_level": c.get("experience_level", ""),
        })

    doc_ref.update({
        "status": "notified",
        "matched_candidates": matched_data,
        "matched_count": len(candidates),
        "notified_candidates_count": notified_count,
        "employer_notified": employer_notified,
        "matched_at": time.time(),
    })

    print(f"✅ [EMP_MATCH] Slot {slot_id}: {len(candidates)} matched, {notified_count} candidates notified, employer={'yes' if employer_notified else 'no'}")

    return {
        "slot_id": slot_id,
        "matched": len(candidates),
        "notified_candidates": notified_count,
        "notified_employer": employer_notified,
        "candidates": matched_data,
    }
