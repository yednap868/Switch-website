# WhatsApp Template Registration: Interview Confirmation

This document covers the two interview-related WhatsApp templates used in Vance.

---

## Template 1: `interview_confirmation` (Switch / Blue-collar Flow)

**Template Name:** `interview_confirmation`
**Category:** UTILITY
**Language:** English (en)

### Template Content

**Message Body:**
```
✅ Interview Confirmed!

🏢 {{1}}
💼 Role: {{2}}
🗓️ {{3}}
📍 {{4}}
💰 Salary: {{5}}

Reply YES to confirm attendance.
```

### Parameters

| # | Placeholder | Description | Example |
|---|-------------|-------------|---------|
| 1 | `{{1}}` | Business name | "Zomato" |
| 2 | `{{2}}` | Job role | "Delivery Partner" |
| 3 | `{{3}}` | Interview date & time | "Monday, 3 Feb 2025, 10:00 AM" |
| 4 | `{{4}}` | Interview address | "Sec 24, Gurgaon" |
| 5 | `{{5}}` | Salary range | "₹15,000 - ₹25,000" |

### Example Message (filled)
```
✅ Interview Confirmed!

🏢 Zomato
💼 Role: Delivery Partner
🗓️ Monday, 3 Feb 2025, 10:00 AM
📍 Sec 24, Gurgaon
💰 Salary: ₹15,000 - ₹25,000

Reply YES to confirm attendance.
```

### Registration Steps

1. Go to [Meta Business Suite](https://business.facebook.com)
2. Navigate to **WhatsApp Manager** → **Message Templates**
3. Click **"Create Template"**
4. Select **Category:** UTILITY
5. **Template Name:** `interview_confirmation` (must match exactly, case-sensitive)
6. **Language:** English
7. **Message Body:** Paste the template content above with `{{1}}` through `{{5}}` placeholders
8. **Add Variables:**
   - Variable 1 (`{{1}}`): Text — Business name
   - Variable 2 (`{{2}}`): Text — Job role
   - Variable 3 (`{{3}}`): Text — Interview date & time
   - Variable 4 (`{{4}}`): Text — Interview address
   - Variable 5 (`{{5}}`): Text — Salary range
9. **Submit** for approval (usually 24–48 hours)

### Usage in Code

Used in `services/switch_whatsapp_service.py` → `send_interview_confirmation()`:

```python
template_payload = MsgComponents.template_scaffold(
    to=wa_phone,
    template_name="interview_confirmation",
    language_code="en",
    body_parameters=[
        business_name,
        role,
        interview_timing,
        interview_address,
        salary,
    ],
)
```

### Fallback Behavior

If the template is not approved or fails, the system automatically falls back to a regular text message with the same content.

---

## Template 2: `interview_notif` (Main Vance / White-collar Flow)

**Template Name:** `interview_notif`
**Category:** UTILITY
**Language:** English (en)

### Template Content

**Message Body:**
```
Great news! {{1}} wants to interview you!

Interview scheduled for {{2}}
Google Meet: {{3}}

A calendar invite has been sent to your email. Good luck!
```

### Parameters

| # | Placeholder | Description | Example |
|---|-------------|-------------|---------|
| 1 | `{{1}}` | Hiring manager name | "John from Acme Corp" |
| 2 | `{{2}}` | Interview date & time (RFC 850 format) | "Monday, 03-Feb-25 10:00:00 IST" |
| 3 | `{{3}}` | Google Meet link | "https://meet.google.com/abc-defg-hij" |

### Example Message (filled)
```
Great news! John from Acme Corp wants to interview you!

Interview scheduled for Monday, 03-Feb-25 10:00:00 IST
Google Meet: https://meet.google.com/abc-defg-hij

A calendar invite has been sent to your email. Good luck!
```

### Registration Steps

1. Go to [Meta Business Suite](https://business.facebook.com)
2. Navigate to **WhatsApp Manager** → **Message Templates**
3. Click **"Create Template"**
4. Select **Category:** UTILITY
5. **Template Name:** `interview_notif` (must match exactly, case-sensitive)
6. **Language:** English
7. **Message Body:** Paste the template content above with `{{1}}` through `{{3}}` placeholders
8. **Add Variables:**
   - Variable 1 (`{{1}}`): Text — Hiring manager name
   - Variable 2 (`{{2}}`): Text — Interview date & time
   - Variable 3 (`{{3}}`): Text — Google Meet link
9. **Submit** for approval (usually 24–48 hours)

### Usage in Code

Used in `services/interview_scheduling_service.py` → `notify_candidate_interview_scheduled()`:

```python
template_payload = MsgComponents.template_scaffold(
    to=candidate_wa_id,
    template_name="interview_notif",
    language_code="en",
    body_parameters=[hiring_user_name, time_str, meet_link],
)
```

---

## Important Notes

- Template names are **case-sensitive** — they must match exactly as specified above
- Both templates require **UTILITY** category for best approval rates
- Approval typically takes **24–48 hours** from Meta
- The `interview_confirmation` template has a text fallback; `interview_notif` does not (ensure it is approved before use)
- Make sure your WhatsApp Business Account has permission to send template messages
