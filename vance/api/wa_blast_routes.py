"""
WhatsApp blast — sends candidate_matched template to all Switch + Jyoti users.
Tracks delivery, reads (via webhook status updates), and link clicks.

POST /api/blast/send          — trigger blast (admin only)
GET  /api/blast/stats         — read/click stats per campaign
GET  /api/blast/w/{token}     — click tracking redirect → app.switchlocally.com
"""

import os
import time
import secrets
import threading

import requests
from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.postgres import get_db
from models.sql_models import WaBlastLog

router = APIRouter(tags=["WA Blast"])

SWITCH_PHONE_NUMBER_ID = os.getenv("SWITCH_PHONE_NUMBER_ID", "990475317490297")
META_TOKEN = os.getenv("META_SYS_USER_TOKEN", "")
WA_URL = f"https://graph.facebook.com/v21.0/{SWITCH_PHONE_NUMBER_ID}/messages"
APP_URL = "https://app.switchlocally.com"
BLAST_ADMIN_KEY = os.getenv("BLAST_ADMIN_KEY", "switch-blast-2026")

# Popular jobs to use as fallback when user has no role preference
FALLBACK_JOBS = [
    ("Security Guard", "Gurgaon"),
    ("Cook / Helper", "Delhi NCR"),
    ("Property Manager", "Gurgaon"),
    ("Kitchen Helper", "Delhi"),
    ("Receptionist", "Delhi NCR"),
]


def _send_wa_template(phone: str, name: str, job_label: str) -> dict:
    """Send candidate_matched template. Returns {wamid, error}."""
    headers = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": "candidate_matched",
            "language": {"code": "hi"},
            "components": [
                {"type": "body", "parameters": [
                    {"type": "text", "text": name},
                    {"type": "text", "text": job_label},
                ]},
            ],
        },
    }
    try:
        r = requests.post(WA_URL, json=payload, headers=headers, timeout=10)
        data = r.json()
        if r.ok and data.get("messages"):
            return {"wamid": data["messages"][0]["id"], "error": None}
        return {"wamid": None, "error": data.get("error", {}).get("message", "unknown")}
    except Exception as e:
        return {"wamid": None, "error": str(e)}


def _match_job(job_role: str, preferred_roles: str, location: str) -> str:
    """Return a human-readable job label for the user."""
    role = (job_role or "").strip().lower()
    prefs = (preferred_roles or "[]").lower()
    loc = (location or "Delhi NCR").strip() or "Delhi NCR"

    if "cook" in role or "cook" in prefs or "chef" in prefs:
        return f"Cook / Helper - {loc}"
    if "security" in role or "security" in prefs or "guard" in prefs:
        return f"Security Guard - {loc}"
    if "receptionist" in role or "receptionist" in prefs:
        return f"Receptionist - {loc}"
    if "manager" in role or "propmanager" in role:
        return f"Property Manager - {loc}"
    if "picker" in role or "packer" in role or "warehouse" in prefs:
        return f"Picker / Packer - {loc}"
    if "delivery" in role or "delivery" in prefs:
        return f"Delivery - {loc}"
    if "caretaker" in role or "caretaker" in prefs:
        return f"Caretaker - {loc}"
    if "kitchen" in role or "kitchen" in prefs:
        return f"Kitchen Helper - {loc}"

    # fallback based on index of phone number (deterministic variety)
    idx = sum(ord(c) for c in (loc or "x")) % len(FALLBACK_JOBS)
    title, area = FALLBACK_JOBS[idx]
    return f"{title} - {area}"


def _run_blast(campaign: str, phones_data: list, db_url: str):
    """Background thread: send to all users, log each result."""
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    total = len(phones_data)
    sent = 0
    failed = 0
    rate_limit_pause = 0.05  # 20 msgs/sec — safe for WhatsApp Cloud API

    for i, (phone, name, job_label) in enumerate(phones_data):
        token = secrets.token_urlsafe(12)
        result = _send_wa_template(phone, name, job_label)
        now = time.time()

        cur.execute("""
            INSERT INTO wa_blast_logs
              (campaign, phone, name, wamid, job_label, click_token, sent_at, failed, error, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            campaign, phone, name,
            result["wamid"], job_label, token,
            now if not result["error"] else None,
            bool(result["error"]),
            result["error"],
            now,
        ))
        conn.commit()

        if result["error"]:
            failed += 1
        else:
            sent += 1

        if (i + 1) % 50 == 0:
            print(f"[BLAST] {i+1}/{total} — sent:{sent} failed:{failed}")

        time.sleep(rate_limit_pause)

    print(f"[BLAST] Done. Total:{total} Sent:{sent} Failed:{failed}")
    cur.close()
    conn.close()


@router.post("/api/blast/send")
def trigger_blast(
    campaign: str = Query(default="reengagement_apr26"),
    admin_key: str = Query(default=""),
    limit: int = Query(default=0, description="0 = all users"),
):
    if admin_key != BLAST_ADMIN_KEY:
        return JSONResponse({"error": "unauthorized"}, status_code=403)

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    import psycopg2
    import json as _json

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Postgres users
    cur.execute("""
        SELECT phone, name, job_role, preferred_roles, location
        FROM users
        WHERE phone IS NOT NULL AND phone != '' AND phone != '9999999999'
    """)
    pg_users = cur.fetchall()

    cur.close()
    conn.close()

    # Build send list — deduplicate by phone
    seen = set()
    phones_data = []

    for phone, name, job_role, preferred_roles, location in pg_users:
        if phone in seen:
            continue
        seen.add(phone)
        display_name = (name or "").strip() or "Bhai"
        job_label = _match_job(job_role or "", preferred_roles or "[]", location or "")
        phones_data.append((phone, display_name, job_label))

    # Jyoti Firestore callers
    try:
        import firebase_admin
        from firebase_admin import credentials as fb_creds, firestore as fb_store
        try:
            fb_app = firebase_admin.get_app()
        except ValueError:
            cred_path = os.getenv(
                "FIREBASE_CREDENTIALS_PATH",
                "/app/relay-15824-firebase-adminsdk-fbsvc-bc0efb42d8.json"
            )
            fb_app = firebase_admin.initialize_app(fb_creds.Certificate(cred_path))

        fs_db = fb_store.client()
        docs = []
        last = None
        while True:
            q = fs_db.collection("switch_caller_memory").limit(500)
            if last:
                q = q.start_after(last)
            batch = list(q.stream())
            if not batch:
                break
            docs.extend(batch)
            last = batch[-1]
            if len(batch) < 500:
                break

        for doc in docs:
            d = doc.to_dict()
            phone = str(d.get("phone", "")).strip()
            if not phone or phone in seen:
                continue
            seen.add(phone)
            name = (d.get("name") or "").strip() or "Bhai"
            profile = d.get("profile") or {}
            if isinstance(profile, str):
                try:
                    profile = _json.loads(profile)
                except Exception:
                    profile = {}
            role = profile.get("role", "") or ""
            location = profile.get("location", "") or profile.get("city", "") or ""
            job_label = _match_job(role, "", location)
            phones_data.append((phone, name, job_label))
    except Exception as e:
        print(f"[BLAST] Firestore load error (skipping): {e}")

    if limit > 0:
        phones_data = phones_data[:limit]

    threading.Thread(
        target=_run_blast,
        args=(campaign, phones_data, db_url),
        daemon=True,
    ).start()

    return JSONResponse({
        "status": "started",
        "campaign": campaign,
        "total_queued": len(phones_data),
    })


@router.get("/api/blast/stats")
def blast_stats(campaign: str = Query(default=""), admin_key: str = Query(default="")):
    if admin_key != BLAST_ADMIN_KEY:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    db = get_db()
    try:
        q = db.query(WaBlastLog)
        if campaign:
            q = q.filter(WaBlastLog.campaign == campaign)

        total = q.count()
        sent = q.filter(WaBlastLog.sent_at.isnot(None)).count()
        failed = q.filter(WaBlastLog.failed == True).count()
        delivered = q.filter(WaBlastLog.delivered_at.isnot(None)).count()
        read = q.filter(WaBlastLog.read_at.isnot(None)).count()
        clicked = q.filter(WaBlastLog.clicked_at.isnot(None)).count()

        return JSONResponse({
            "campaign": campaign or "all",
            "total": total,
            "sent": sent,
            "failed": failed,
            "delivered": delivered,
            "read": read,
            "clicked": clicked,
            "read_rate_pct": round(100 * read / sent, 1) if sent else 0,
            "click_rate_pct": round(100 * clicked / sent, 1) if sent else 0,
        })
    finally:
        db.close()


@router.get("/api/blast/stats/all")
def blast_stats_all(admin_key: str = Query(default="")):
    if admin_key != BLAST_ADMIN_KEY:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    db = get_db()
    try:
        from sqlalchemy import func
        rows = (
            db.query(
                WaBlastLog.campaign,
                func.count(WaBlastLog.id).label("total"),
                func.count(WaBlastLog.sent_at).label("sent"),
                func.count(WaBlastLog.delivered_at).label("delivered"),
                func.count(WaBlastLog.read_at).label("read"),
                func.count(WaBlastLog.clicked_at).label("clicked"),
            )
            .group_by(WaBlastLog.campaign)
            .all()
        )
        return JSONResponse([
            {
                "campaign": r.campaign,
                "total": r.total,
                "sent": r.sent,
                "delivered": r.delivered,
                "read": r.read,
                "clicked": r.clicked,
                "read_rate_pct": round(100 * r.read / r.sent, 1) if r.sent else 0,
                "click_rate_pct": round(100 * r.clicked / r.sent, 1) if r.sent else 0,
            }
            for r in rows
        ])
    finally:
        db.close()


@router.get("/wa/{token}")
def wa_click_track(token: str):
    """Log click and redirect to app."""
    db = get_db()
    try:
        log = db.query(WaBlastLog).filter(WaBlastLog.click_token == token).first()
        if log and not log.clicked_at:
            log.clicked_at = time.time()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()
    return RedirectResponse(url=APP_URL, status_code=302)
