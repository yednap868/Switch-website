"""
Service for sending employer WhatsApp notifications when a candidate swipes right,
and notifying candidates when an employer approves the match.

Uses the Switch WhatsApp Business Account (WABA) for employer messages
and the Vance number for candidate messages.
"""

import json
import os

import requests

from models.sql_models import Job, User
from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents


FRONTEND_HOST = "app.switchlocally.com"

EMPLOYER_TEMPLATE_NAME = "employer_candidate_match"
CANDIDATE_TEMPLATE_NAME = "candidate_matched"
INTERVIEW_TEMPLATE_NAME = "interview_scheduled"  # Not yet registered — will fall back to text

# Switch WABA phone number ID (separate from Vance's PHONE_NUMBER_ID)
SWITCH_PHONE_NUMBER_ID = os.getenv("SWITCH_PHONE_NUMBER_ID", "990475317490297")
SWITCH_WA_URL = f"https://graph.facebook.com/v21.0/{SWITCH_PHONE_NUMBER_ID}/messages"


def _get_switch_headers() -> dict:
    """Get auth headers for Switch WABA API calls."""
    token = os.getenv("META_SYS_USER_TOKEN")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def _send_via_switch(payload: dict) -> dict:
    """Send a WhatsApp message via the Switch phone number."""
    try:
        res = requests.post(
            SWITCH_WA_URL,
            headers=_get_switch_headers(),
            json=payload,
            timeout=30,
        )
        data = res.json()
        if res.status_code == 200 and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            return {"status": "success", "message_id": msg_id}
        error = data.get("error", {}).get("message", str(data))
        return {"status": "failed", "error": error}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _normalize_wa_phone(phone: str) -> str:
    """Normalize phone to WhatsApp format (digits only, with country code)."""
    phone = phone.strip().lstrip("+")
    if not phone.startswith("91"):
        phone = "91" + phone
    return phone


def send_employer_whatsapp(match_token: str, job: Job, candidate_user: User):
    """Send WhatsApp template to employer with candidate details and approval link.

    Sends via the Switch WABA (not Vance) so the message comes from the Switch number.
    """
    employer_phone = (job.phone or "").strip()
    if not employer_phone:
        print(f"[EMPLOYER_MATCH] No employer phone for job {job.job_id}, skipping WhatsApp")
        return

    wa_phone = _normalize_wa_phone(employer_phone)

    candidate_name = candidate_user.name or "Candidate"
    candidate_exp = candidate_user.experience or "Not specified"
    candidate_location = candidate_user.location or "NCR"

    approval_url = f"https://{FRONTEND_HOST}/hire/{match_token}"

    candidate_summary = f"{candidate_name} | {candidate_exp} | {candidate_location}"

    # Try template first (requires template to be approved on Switch WABA)
    template_payload = MsgComponents.template_scaffold(
        to=wa_phone,
        template_name=EMPLOYER_TEMPLATE_NAME,
        language_code="en",
        body_parameters=[
            job.title or "Open Position",
            candidate_summary,
            approval_url,
        ],
    )
    result = _send_via_switch(template_payload)

    if result.get("status") == "success":
        print(f"[EMPLOYER_MATCH] Template sent to employer {wa_phone} via Switch: {result}")
        return

    print(f"[EMPLOYER_MATCH] Template failed ({result.get('error')}), trying text fallback")

    # Fallback to text (only works if employer has messaged Switch within 24h)
    candidate_roles = json.loads(candidate_user.preferred_roles) if candidate_user.preferred_roles else []
    roles_str = ", ".join(candidate_roles[:3]) if candidate_roles else "Not specified"

    message = (
        f"New candidate for {job.title}!\n"
        f"\n"
        f"Name: {candidate_name}\n"
        f"Experience: {candidate_exp}\n"
        f"Location: {candidate_location}\n"
        f"Roles: {roles_str}\n"
        f"\n"
        f"View profile & approve:\n"
        f"{approval_url}"
    )
    fallback = MsgComponents.text_scaffold(to=wa_phone, text=message)
    result = _send_via_switch(fallback)
    print(f"[EMPLOYER_MATCH] Text fallback to employer {wa_phone} via Switch: {result}")


def notify_employer_kyc_complete(employer_phone: str, worker_name: str, job_title: str, company: str, joining_date: str = "", application_id: int = 0):
    """Notify employer via WhatsApp that a worker completed Video KYC for their job.

    Sends via the Switch WABA as a plain text message. Relies on the 24h customer-service
    window being open — which it typically is, since the employer received the initial
    employer_candidate_match template earlier in the flow.
    """
    if not employer_phone:
        print(f"[KYC_COMPLETE] No employer phone, skipping WhatsApp")
        return {"status": "skipped", "reason": "no_phone"}

    wa_phone = _normalize_wa_phone(employer_phone)
    worker_display = worker_name or "Worker"
    role_display = job_title or "the role"
    company_display = company or "your opening"
    joining_line = f"\nJoining: {joining_date}" if joining_date else ""
    link_suffix = f"?app={application_id}" if application_id else ""

    message = (
        f"✅ KYC verified!\n\n"
        f"{worker_display} has completed Video KYC for {role_display} at {company_display}.{joining_line}\n\n"
        f"View profile & details:\n"
        f"https://{FRONTEND_HOST}/employer{link_suffix}"
    )
    payload = MsgComponents.text_scaffold(to=wa_phone, text=message)
    result = _send_via_switch(payload)
    print(f"[KYC_COMPLETE] Employer {wa_phone} notified: {result}")
    return result


def notify_candidate_matched(user_phone: str, job: Job, application_id: int = 0):
    """Send WhatsApp to candidate informing them the employer is interested.

    Sends via the Switch WABA (not Vance) so the message comes from the Switch number.
    Includes a deep link to trigger the match moment in the app.
    """
    wa_phone = _normalize_wa_phone(user_phone)

    job_title = job.title or "a position"
    company = job.company or "the company"

    deep_link = f"https://{FRONTEND_HOST}/?match={application_id}" if application_id else f"https://{FRONTEND_HOST}/"

    # Template parameters (Hindi): {{1}}=job_title, {{2}}=company_name
    try:
        payload = MsgComponents.template_scaffold(
            to=wa_phone,
            template_name=CANDIDATE_TEMPLATE_NAME,
            language_code="hi",
            body_parameters=[job_title, company],
        )
        result = _send_via_switch(payload)
        print(f"[EMPLOYER_MATCH] Template sent to candidate {wa_phone} via Switch: {result}")
    except Exception as template_err:
        print(f"[EMPLOYER_MATCH] Template '{CANDIDATE_TEMPLATE_NAME}' failed, falling back to text: {template_err}")
        message = (
            f"बधाई हो! {job_title} की {company} में नौकरी के लिए employer को "
            f"आपकी profile पसंद आई है!\n"
            f"\n"
            f"ऐप खोलो: {deep_link}\n"
            f"\n"
            f"वो जल्द ही आपसे संपर्क करेंगे। कृपया अपना फ़ोन पास रखें।"
        )
        fallback = MsgComponents.text_scaffold(to=wa_phone, text=message)
        result = _send_via_switch(fallback)
        print(f"[EMPLOYER_MATCH] Text fallback sent to candidate {wa_phone} via Switch: {result}")


def notify_candidate_interview(user_phone: str, job: Job, interview_datetime: str, interview_location: str):
    """Send WhatsApp to candidate informing them about the scheduled interview."""
    wa_phone = _normalize_wa_phone(user_phone)

    company = job.company or "the company"
    job_title = job.title or "a position"
    location = interview_location or job.location or "TBD"
    salary = ""
    if job.salary_min and job.salary_max:
        salary = f"₹{job.salary_min:,} - ₹{job.salary_max:,}"
    elif job.salary_min:
        salary = f"₹{job.salary_min:,}+"
    else:
        salary = "As discussed"

    # Template: interview_confirmation — {{1}}=company, {{2}}=role, {{3}}=datetime, {{4}}=location, {{5}}=salary
    try:
        payload = MsgComponents.template_scaffold(
            to=wa_phone,
            template_name=INTERVIEW_TEMPLATE_NAME,
            language_code="en",
            body_parameters=[company, job_title, interview_datetime, location, salary],
        )
        result = _send_via_switch(payload)
        print(f"[EMPLOYER_MATCH] Interview template sent to candidate {wa_phone}: {result}")
    except Exception as template_err:
        print(f"[EMPLOYER_MATCH] Interview template failed, falling back to text: {template_err}")
        message = (
            f"Interview scheduled!\n"
            f"\n"
            f"{company}\n"
            f"Role: {job_title}\n"
            f"{interview_datetime}\n"
            f"{location}\n"
            f"Salary: {salary}\n"
            f"\n"
            f"Please be on time. Good luck!"
        )
        fallback = MsgComponents.text_scaffold(to=wa_phone, text=message)
        result = _send_via_switch(fallback)
        print(f"[EMPLOYER_MATCH] Interview text sent to candidate {wa_phone}: {result}")


def send_blast_to_worker(worker_phone: str, role: str, location: str, time_str: str):
    """Send a WhatsApp message to a worker notifying them of a new job blast."""
    wa_phone = _normalize_wa_phone(worker_phone)
    message = (
        f"🔔 *Nayi Job!*\n\n"
        f"*{role}* chahiye — {location}\n"
        f"Joining: Kal {time_str or '9:00 AM'} tak\n\n"
        f"App kholo aur Accept karo:\n"
        f"https://app.switchlocally.com"
    )
    payload = MsgComponents.text_scaffold(to=wa_phone, text=message)
    result = _send_via_switch(payload)
    print(f"[BLAST] WhatsApp sent to worker {wa_phone}: {result}")
    return result


def notify_employer_blast_accepted(employer_phone: str, worker_name: str, worker_phone: str, role: str, location: str):
    """Notify employer via WhatsApp when a worker accepts their blast."""
    wa_phone = _normalize_wa_phone(employer_phone)
    message = (
        f"✅ *Worker ne Accept kiya!*\n\n"
        f"*{worker_name or 'Worker'}* aapki job ke liye ready hai.\n"
        f"Role: {role}\n"
        f"Location: {location}\n\n"
        f"Contact: +{worker_phone.lstrip('+')}"
    )
    payload = MsgComponents.text_scaffold(to=wa_phone, text=message)
    result = _send_via_switch(payload)
    print(f"[BLAST] Employer notified {wa_phone}: {result}")
    return result


def send_blast_confirmation_to_worker(worker_phone: str, role: str, location: str, time_str: str):
    """Send confirmation WhatsApp to worker after they accept a blast."""
    wa_phone = _normalize_wa_phone(worker_phone)
    message = (
        f"✅ *Confirmed!*\n\n"
        f"Kal *{time_str or '9:00 AM'}* tak *{location}* pahunch jaana.\n"
        f"Role: {role}\n\n"
        f"Koi problem ho toh reply karo."
    )
    payload = MsgComponents.text_scaffold(to=wa_phone, text=message)
    result = _send_via_switch(payload)
    print(f"[BLAST] Confirmation sent to worker {wa_phone}: {result}")
    return result
