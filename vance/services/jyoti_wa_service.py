"""
Jyoti — AI personal companion on WhatsApp.

Powered by Claude. Handles any message from a worker:
- Answers questions about their jobs, applications, joining
- Looks up and matches new jobs for them
- Updates their profile
- Guides them through the Switch app
- Acts as a warm, caring Hindi/Hinglish didi

Entry point: handle_message(phone, text) → reply string
"""

import json
import os
import time
from typing import Optional

import anthropic

from models.sql_models import User, JobApplication, Job, WaConversation, Placement
from utils.postgres import get_db

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

MAX_HISTORY = 20      # messages kept before summarising
MAX_REPLY_TOKENS = 300


# ---------------------------------------------------------------------------
# Tools Jyoti can call
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "lookup_jobs",
        "description": "Search for open jobs matching a role and/or location. Use when worker asks about jobs or wants to find work.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role_keyword": {"type": "string", "description": "Job role keyword e.g. cook, security, receptionist"},
                "location": {"type": "string", "description": "City or area e.g. Gurgaon, Rohini, Delhi"}
            },
            "required": []
        }
    },
    {
        "name": "get_user_profile",
        "description": "Fetch the worker's current profile, application status and placement from the database.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "update_profile",
        "description": "Update a field in the worker's profile. Use when they share new info about themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "enum": ["name", "location", "job_role", "experience", "expected_salary_min", "expected_salary_max"]
                },
                "value": {"type": "string", "description": "New value for the field"}
            },
            "required": ["field", "value"]
        }
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_lookup_jobs(phone: str, role_keyword: str = "", location: str = "") -> str:
    db = get_db()
    try:
        q = db.query(Job)
        if role_keyword:
            q = q.filter(Job.title.ilike(f"%{role_keyword}%") | Job.category.ilike(f"%{role_keyword}%"))
        if location:
            q = q.filter(Job.location.ilike(f"%{location}%") | Job.city.ilike(f"%{location}%"))
        jobs = q.order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return "Abhi is role aur location ke liye koi opening nahi hai. Main dhundhti rahungi!"
        lines = []
        for j in jobs:
            sal = f"₹{j.salary_min:,}–{j.salary_max:,}" if j.salary_min else "salary negotiable"
            lines.append(f"• {j.title} — {j.location} ({sal})")
        return "Yeh jobs available hain:\n" + "\n".join(lines)
    finally:
        db.close()


def _tool_get_user_profile(phone: str) -> str:
    db = get_db()
    try:
        user = db.query(User).filter_by(phone=phone).first()
        if not user:
            return "Profile nahi mili. App pe register karo: app.switchlocally.com"

        apps = db.query(JobApplication).filter_by(user_id=phone).order_by(JobApplication.created_at.desc()).limit(3).all()
        placement = db.query(Placement).filter_by(user_id=phone).order_by(Placement.id.desc()).first()

        info = f"Name: {user.name or 'unknown'}\n"
        info += f"Location: {user.location or 'not set'}\n"
        info += f"Role preference: {user.job_role or 'not set'}\n"
        info += f"Active job: {user.active_job_key or 'none'}\n"
        info += f"Joining date: {user.joining_date or 'not scheduled'}\n"
        info += f"Checked in: {'yes' if user.checked_in else 'no'}\n"

        if apps:
            info += f"\nRecent applications ({len(apps)}):\n"
            for a in apps:
                info += f"  • {a.role} at {a.company} — status: {a.status}\n"

        if placement:
            info += f"\nLatest placement: {placement.role} at {placement.company} — {placement.status}\n"

        return info
    finally:
        db.close()


def _tool_update_profile(phone: str, field: str, value: str) -> str:
    db = get_db()
    try:
        user = db.query(User).filter_by(phone=phone).first()
        if not user:
            return "Profile nahi mili."
        if field == "expected_salary_min":
            try:
                user.expected_salary_min = int(value.replace(",", "").replace("₹", "").strip())
            except ValueError:
                return "Salary sahi format mein batao, jaise 12000"
        elif field == "expected_salary_max":
            try:
                user.expected_salary_max = int(value.replace(",", "").replace("₹", "").strip())
            except ValueError:
                return "Salary sahi format mein batao, jaise 18000"
        else:
            setattr(user, field, value)
        user.updated_at = time.time()
        db.commit()
        return f"Profile update ho gayi! {field} = {value}"
    finally:
        db.close()


def _run_tool(phone: str, tool_name: str, tool_input: dict) -> str:
    if tool_name == "lookup_jobs":
        return _tool_lookup_jobs(phone, **tool_input)
    elif tool_name == "get_user_profile":
        return _tool_get_user_profile(phone)
    elif tool_name == "update_profile":
        return _tool_update_profile(phone, **tool_input)
    return "Tool not found."


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

def _load_context(phone: str) -> tuple[list, str, str]:
    """Returns (history, summary, system_prompt) — single DB session for both."""
    db = get_db()
    try:
        conv = db.query(WaConversation).filter_by(phone=phone).first()
        history = json.loads(conv.messages or "[]") if conv else []
        summary = conv.summary or "" if conv else ""

        user = db.query(User).filter_by(phone=phone).first()
        name = user.name if user else "yaar"
        role = user.job_role if user and user.job_role else "job"
        location = user.location if user and user.location else "Delhi NCR"
        placed = bool(user and user.active_job_key)
        joining = user.joining_date if user and user.joining_date else None
        checked_in = user.checked_in if user else False
    finally:
        db.close()

    worker_context = (
        f"Worker info:\n"
        f"- Name: {name}\n"
        f"- Looking for: {role}\n"
        f"- Location: {location}\n"
        f"- Currently placed: {'YES — ' + joining if placed and joining else 'No'}\n"
        f"- Checked in: {'Yes' if checked_in else 'No'}"
    )
    summary_section = f"\n\nPrevious conversation summary:\n{summary}" if summary else ""

    system = (
        f"Aap Jyoti hain — Switch platform ki AI assistant. Aap ek professional aur caring helper hain jo workers ki poori madad karti hain.\n\n"
        f"{worker_context}{summary_section}\n\n"
        f"Aapka kaam:\n"
        f"- Har sawaal ka clear jawab dena — jobs, salary, documents, interview, joining process\n"
        f"- Jobs search karna jab worker maange (lookup_jobs tool)\n"
        f"- Profile update karna jab worker naya info share kare (update_profile tool)\n"
        f"- Application aur placement status batana (get_user_profile tool)\n"
        f"- App use karne mein guide karna: app.switchlocally.com\n"
        f"- OTP, check-in, joining date — sab clearly explain karna\n\n"
        f"Baat karne ka tarika:\n"
        f"- Hindi aur Hinglish mix — respectful aur clear, jaise ek helpful professional bolti hai\n"
        f"- Short aur focused replies — 2-4 lines max\n"
        f"- Thoda emoji use karo jab natural lage\n"
        f"- Hamesha polite aur patient raho\n"
        f"- Jo nahi pata, clearly bol do aur doosra raasta suggest karo\n\n"
        f"Sirf Switch aur worker ki job life se related cheezein discuss karo."
    )
    return history, summary, system


def _save_history(phone: str, messages: list, summary: str = ""):
    db = get_db()
    try:
        conv = db.query(WaConversation).filter_by(phone=phone).first()
        if not conv:
            conv = WaConversation(phone=phone, created_at=time.time())
            db.add(conv)
        conv.messages = json.dumps(messages[-MAX_HISTORY:])
        if summary:
            conv.summary = summary
        conv.updated_at = time.time()
        db.commit()
    finally:
        db.close()


def _summarise_old_messages(messages: list) -> str:
    """Ask Claude to summarise older messages to free up context."""
    if not messages:
        return ""
    text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    try:
        resp = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": f"Summarise this conversation in 3-4 lines in Hindi/English:\n\n{text}"
            }]
        )
        return resp.content[0].text
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def handle_message(phone: str, text: str) -> Optional[str]:
    """Process an inbound WhatsApp message and return Jyoti's reply."""
    try:
        try:
            history, summary, system = _load_context(phone)
        except Exception as e:
            print(f"[JYOTI] Context load error for {phone}: {e}")
            history, summary = [], ""
            system = "Tu Jyoti hai — Switch ki helpful AI companion. Hindi/Hinglish mein short replies do."

        if len(history) >= MAX_HISTORY:
            summary = _summarise_old_messages(history[:MAX_HISTORY // 2])
            history = history[MAX_HISTORY // 2:]

        history.append({"role": "user", "content": text, "ts": time.time()})
        claude_messages = [{"role": m["role"], "content": m["content"]} for m in history]

        for _ in range(5):
            response = _client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=MAX_REPLY_TOKENS,
                system=system,
                tools=TOOLS,
                messages=claude_messages,
            )

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = _run_tool(phone, block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                claude_messages.append({"role": "assistant", "content": response.content})
                claude_messages.append({"role": "user", "content": tool_results})
                continue

            reply = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "Kuch samajh nahi aaya, dobara batao 🙏"
            )
            history.append({"role": "assistant", "content": reply, "ts": time.time()})
            try:
                _save_history(phone, history, summary)
            except Exception as e:
                print(f"[JYOTI] Save history error for {phone}: {e}")
            return reply

        return "Kuch samajh nahi aaya, dobara batao 🙏"

    except Exception as e:
        print(f"[JYOTI] Fatal error for {phone}: {e}")
        import traceback
        traceback.print_exc()
        return "Abhi thodi problem aa rahi hai, thodi der mein try karo 🙏"
