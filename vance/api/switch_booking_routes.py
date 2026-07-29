"""
Switch hiring-request routes.

An employer posts a hiring request (role + headcount + salary).
The system blasts matching workers via FCM push notifications.
Workers raise their hand ("I'm interested") from the PWA.
The employer reviews interested candidates and contacts them directly.

Status flow:
  open       → request created, workers being notified
  reviewing  → at least one worker expressed interest
  hired      → employer marked someone as hired
  closed     → employer closed the request
"""

import asyncio
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models.sql_models import FcmToken
from services.notification_service import Content, notify_user
from utils.hearus_auth import caller_phone
from utils.postgres import get_db

router = APIRouter(prefix="/api/switch", tags=["Switch Hiring"])

_requests: dict = {}   # in-memory cache, Firestore is the durable store

WORKERS_TO_PING = 20   # max workers blasted per request


# ---------------------------------------------------------------------------
# Firestore helpers
# ---------------------------------------------------------------------------
def _persist(req_id: str, data: dict) -> None:
    def _write():
        try:
            from utils.db import db as _fs
            _fs.collection("switch_hiring_requests").document(req_id).set(data)
        except Exception:
            pass
    threading.Thread(target=_write, daemon=True).start()


def _fetch(req_id: str) -> dict | None:
    if req_id in _requests:
        return _requests[req_id]
    try:
        from utils.db import db as _fs
        doc = _fs.collection("switch_hiring_requests").document(req_id).get()
        if doc.exists:
            d = doc.to_dict()
            _requests[req_id] = d
            return d
    except Exception:
        pass
    return None


def _fetch_by_employer(phone: str) -> list[dict]:
    results = []
    try:
        from utils.db import db as _fs
        docs = (
            _fs.collection("switch_hiring_requests")
            .where("employer_phone", "==", phone)
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            # prefer in-memory version (may be fresher)
            results.append(_requests.get(d["id"], d))
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    except Exception:
        results = [r for r in _requests.values() if r.get("employer_phone") == phone]
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return results


def _fetch_by_worker(phone: str) -> list[dict]:
    """All hiring requests where this worker was pinged."""
    results = []
    try:
        from utils.db import db as _fs
        docs = _fs.collection("switch_hiring_requests").where("status", "in", ["open", "reviewing"]).stream()
        for doc in docs:
            d = doc.to_dict()
            if phone in d.get("pinged_workers", {}):
                results.append(_requests.get(d["id"], d))
    except Exception:
        for r in _requests.values():
            if phone in r.get("pinged_workers", {}):
                results.append(r)
    return results


# ---------------------------------------------------------------------------
# FCM push helpers
# ---------------------------------------------------------------------------
class FcmTokenBody(BaseModel):
    token:    str
    platform: str = "web"           # "web" | "android" | "ios"
    role:     str = "worker"        # "worker" | "employer"


def _get_fcm_token(phone: str) -> str | None:
    """Legacy single-token lookup — returns the most recently seen active token for a phone.

    New code paths should go through services.notification_service instead,
    which fans out to all of a user's active devices.
    """
    db = get_db()
    try:
        row = (
            db.query(FcmToken)
            .filter(FcmToken.phone == phone, FcmToken.disabled_at.is_(None))
            .order_by(FcmToken.last_seen_at.desc())
            .first()
        )
        return row.token if row else None
    finally:
        db.close()


def _send_fcm_push(token: str, title: str, body: str, data: dict | None = None, url: str = "/") -> bool:
    """Send a push notification via Firebase Cloud Messaging."""
    try:
        from firebase_admin import messaging as fcm_messaging
        from utils.firebase_init import initialize_firebase
        initialize_firebase()

        clean_data = {k: str(v) for k, v in (data or {}).items()}
        clean_data["url"] = url

        msg = fcm_messaging.Message(
            notification=fcm_messaging.Notification(title=title, body=body),
            data=clean_data,
            token=token,
            android=fcm_messaging.AndroidConfig(priority="high"),
            webpush=fcm_messaging.WebpushConfig(
                notification=fcm_messaging.WebpushNotification(
                    icon="https://app.switchlocally.com/icon-192.png",
                    badge="https://app.switchlocally.com/icon-72.png",
                    vibrate_pattern=[200, 100, 200],
                    renotify=True,
                    tag=clean_data.get("request_id", "switch-push"),
                ),
                fcm_options=fcm_messaging.WebpushFCMOptions(link=f"https://app.switchlocally.com{url}"),
            ),
        )
        fcm_messaging.send(msg)
        return True
    except Exception as exc:
        print(f"[FCM] Push failed → {exc}")
        return False


@router.post("/fcm-token")
async def save_fcm_token(body: FcmTokenBody, request: Request):
    """
    Register an FCM device token for the authenticated user.

    Identity comes from the Hearus bearer token (verified by HearusBearerAuthMiddleware).
    One row per device token; many devices per user supported. Re-registering the same
    token refreshes last_seen_at and clears disabled_at (user reinstalled).
    """
    phone = caller_phone(request)
    user = request.state.user
    user_id = user.get("uid") or phone

    token = (body.token or "").strip()
    if not token:
        return JSONResponse({"error": "token required"}, status_code=400)

    now = time.time()
    db = get_db()
    try:
        row = db.query(FcmToken).filter_by(token=token).first()
        if row:
            row.user_id = user_id
            row.phone = phone
            row.role = body.role
            row.platform = body.platform
            row.last_seen_at = now
            row.disabled_at = None
        else:
            row = FcmToken(
                token=token,
                user_id=user_id,
                phone=phone,
                role=body.role,
                platform=body.platform,
                created_at=now,
                last_seen_at=now,
            )
            db.add(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[FCM] Token save failed for user_id={user_id}: {exc}")
        return JSONResponse({"error": "Failed to save token"}, status_code=500)
    finally:
        db.close()

    return JSONResponse({"success": True})


# ---------------------------------------------------------------------------
# Worker matching
# ---------------------------------------------------------------------------
ROLE_KEYWORDS: dict[str, list[str]] = {
    "cook":             ["cook", "chef", "tandoor", "indian", "chinese", "kitchen"],
    "Cook":             ["cook", "chef", "tandoor", "indian", "chinese", "kitchen"],
    "kitchen-helper":   ["helper", "kitchen helper", "kitchen", "assistant"],
    "cleaner":          ["housekeeping", "clean", "sweeper", "janitor", "sanitation"],
    "Cleaner":          ["housekeeping", "clean", "sweeper", "janitor", "sanitation"],
    "waiter":           ["waiter", "steward", "server", "service staff"],
    "security-guard":   ["security", "guard", "watchman", "bouncer"],
    "Security":         ["security", "guard", "watchman", "bouncer"],
    "Security Guard":   ["security", "guard", "watchman", "bouncer"],
    "receptionist":     ["receptionist", "front desk", "front office", "admin"],
    "Receptionist":     ["receptionist", "front desk", "front office", "admin"],
    "housekeeping":     ["housekeeping", "housekeeper", "maid", "room service", "cleaner", "clean"],
    "Housekeeping":     ["housekeeping", "housekeeper", "maid", "room service", "cleaner", "clean"],
    "caretaker":        ["caretaker", "care taker", "helper", "labour", "worker"],
    "Caretaker":        ["caretaker", "care taker", "helper", "labour", "worker"],
    "Property Manager": ["property", "manager", "admin", "supervisor", "receptionist"],
    "Sales Executive":  ["sales", "business development", "telesales", "field sales"],
}


def _parse_json_col(val) -> list:
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        return []


def _role_matches(worker_roles: list[str], booking_role: str) -> bool:
    keywords = ROLE_KEYWORDS.get(booking_role, [booking_role.lower()])
    for wr in worker_roles:
        wr_lower = wr.lower()
        if any(kw in wr_lower for kw in keywords):
            return True
    return False


def _get_worker_profile(phone: str) -> dict | None:
    """Fetch full worker profile from Postgres for employer to view."""
    try:
        from utils.pg import get_db
        from models.sql_models import User

        db = get_db()
        try:
            u = db.query(User).filter_by(phone=phone).first()
            if not u:
                return None
            roles = _parse_json_col(u.preferred_roles)
            salary_min = u.expected_salary_min or 0
            salary_max = u.expected_salary_max or 0
            if salary_min or salary_max:
                salary_str = f"₹{salary_min:,}–₹{salary_max:,}/month"
            else:
                salary_str = "Negotiable"
            return {
                "phone":           u.phone,
                "name":            u.name or "",
                "photo_url":       u.photo_url or "",
                "location":        u.location or "Delhi NCR",
                "experience":      u.experience or "",
                "preferred_roles": roles,
                "expected_salary": salary_str,
                "previous_company": u.previous_company or "",
                "previous_role":   u.previous_role or "",
                "work_duration":   u.work_duration or "",
                "is_available":    bool(u.is_available),
                "immediately_available": bool(u.is_available) and not bool(u.active_job_key),
                "gender":          u.gender or "",
            }
        finally:
            db.close()
    except Exception as exc:
        print(f"[HIRING] Profile fetch failed for {phone}: {exc}")
        return None


def _find_matching_workers(role: str, limit: int = WORKERS_TO_PING) -> list[dict]:
    try:
        from utils.pg import get_db
        from models.sql_models import User, Candidate

        db = get_db()
        results = []
        seen = set()
        try:
            for u in db.query(User).all():
                if not u.name or not u.phone:
                    continue
                roles = _parse_json_col(u.preferred_roles)
                if not _role_matches(roles, role):
                    continue
                seen.add(u.phone)
                results.append({
                    "phone": u.phone,
                    "name": u.name,
                    "is_available": bool(u.is_available),
                    "location": u.location or "Gurgaon",
                    "experience": u.experience or "",
                    "roles": roles,
                })
            for c in db.query(Candidate).all():
                if not c.name or not c.phone or c.phone in seen:
                    continue
                roles = _parse_json_col(c.previous_roles)
                if not _role_matches(roles, role):
                    continue
                results.append({
                    "phone": c.phone,
                    "name": c.name,
                    "is_available": (c.status or "AVAILABLE") == "AVAILABLE",
                    "location": c.area or "Gurgaon",
                    "experience": c.experience_level or "",
                    "roles": roles,
                })
        finally:
            db.close()

        results.sort(key=lambda w: (not w["is_available"], w["name"]))
        return results[:limit]
    except Exception as exc:
        print(f"[HIRING] Worker query failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Blast
# ---------------------------------------------------------------------------
def _blast_workers(hiring_req: dict) -> None:
    role_label = hiring_req.get("role_label", hiring_req["role"])
    company    = hiring_req.get("company", "an employer")
    location   = hiring_req.get("location", "")
    salary     = hiring_req.get("salary", "")
    req_id     = hiring_req["id"]
    headcount  = hiring_req.get("headcount", 1)

    workers = _find_matching_workers(hiring_req["role"])
    pinged  = {}
    sent    = 0
    for w in workers:
        try:
            result = notify_user(
                w["phone"],
                Content(
                    type="match",
                    title="Naya Kaam: {role_label}",
                    body="{company}, {location}{salary_part}",
                    url="/app",
                ),
                params={
                    "role_label": role_label,
                    "company": company,
                    "location": location,
                    "salary_part": f" • {salary}" if salary else "",
                },
                extra_data={"request_id": req_id, "role": role_label},
                idempotency_key=f"hiring_blast:{req_id}:{w['phone']}",
            )
            ok = result.devices_delivered > 0
        except Exception as exc:
            print(f"[HIRING] notify_user failed for {w['phone']}: {exc}")
            ok = False
        pinged[w["phone"]] = {
            "name":    w["name"],
            "status":  "pending",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "push_sent": ok,
        }
        if ok:
            sent += 1

    hiring_req["pinged_workers"]    = pinged
    hiring_req["workers_notified"]  = len(pinged)
    hiring_req["push_sent"]         = sent
    _requests[req_id]               = hiring_req
    _persist(req_id, hiring_req)
    print(f"[HIRING] Blasted {len(pinged)} workers ({sent} push delivered) for request {req_id}")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class HiringRequestCreate(BaseModel):
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    employer_phone: str | None = None
    company:        str = ""
    role:           str
    role_label:     str = ""
    headcount:      int = 1
    salary:         str = ""          # e.g. "₹12,000–18,000/month"
    location:       str = ""
    when_needed:    str = ""          # e.g. "Immediately" or "From 1 May"
    notes:          str = ""          # any extra info for the worker


class WorkerRespondRequest(BaseModel):
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    worker_phone: str | None = None
    response:     str   # "interested" | "not_interested"


# ---------------------------------------------------------------------------
# Employer endpoints
# ---------------------------------------------------------------------------
@router.post("/employer/hiring-request/create")
async def create_hiring_request(req: HiringRequestCreate, request: Request):
    """
    Employer posts a full-time hiring request.
    System immediately finds matching workers and blasts them on WhatsApp.
    """
    employer_phone = caller_phone(request)
    req_id = str(uuid.uuid4())
    hiring_req = {
        "id":             req_id,
        "employer_phone": employer_phone,
        "company":        req.company,
        "role":           req.role,
        "role_label":     req.role_label or req.role,
        "headcount":      req.headcount,
        "salary":         req.salary,
        "location":       req.location,
        "when_needed":    req.when_needed or "Immediately",
        "notes":          req.notes,
        "status":         "open",
        "created_at":     datetime.now(timezone.utc).isoformat(),
        "pinged_workers": {},
        "workers_notified": 0,
    }

    _requests[req_id] = hiring_req
    _persist(req_id, hiring_req)

    threading.Thread(target=_blast_workers, args=(hiring_req,), daemon=True).start()

    return JSONResponse({
        "request_id":  req_id,
        "status":      "open",
        "role":        req.role,
        "role_label":  req.role_label or req.role,
        "headcount":   req.headcount,
        "salary":      req.salary,
        "location":    req.location,
        "when_needed": req.when_needed or "Immediately",
    })


@router.post("/admin/blast-pg-jobs")
async def blast_pg_jobs(secret: str = "switch2026"):
    """
    Admin endpoint: create a hiring request for every open PG job and
    blast matching workers on WhatsApp.

    Call once to seed all 15 RentOk PG requirements.
    Idempotent per pg_id — won't re-blast if already done.
    """
    from services.pg_jobs_service import get_all_pg_jobs, get_salary_for_role

    if secret != "switch2026":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    pg_jobs = get_all_pg_jobs()
    created = []
    skipped = []

    for pg in pg_jobs:
        for role in pg["roles"]:
            idempotency_key = f"pg_{pg['id']}_{role.lower().replace(' ', '_')}"

            # Skip if already blasted
            if any(r.get("pg_idempotency_key") == idempotency_key for r in _requests.values()):
                skipped.append(idempotency_key)
                continue

            salary = get_salary_for_role(role)
            req_id = str(uuid.uuid4())

            hiring_req = {
                "id":                   req_id,
                "pg_idempotency_key":   idempotency_key,
                "employer_phone":       pg["owner_phone"],
                "company":              pg["pg_name"],
                "role":                 role,
                "role_label":           role,
                "headcount":            1,
                "salary":               salary,
                "location":             pg["location"],
                "when_needed":          "Immediately",
                "notes":                "Free food + accommodation included",
                "status":               "open",
                "is_pg_job":            True,
                "owner_name":           pg["owner_name"],
                "created_at":           datetime.now(timezone.utc).isoformat(),
                "pinged_workers":       {},
                "workers_notified":     0,
            }

            _requests[req_id] = hiring_req
            _persist(req_id, hiring_req)

            # Blast workers in background with PG-specific message
            threading.Thread(
                target=_blast_pg_workers,
                args=(hiring_req,),
                daemon=True,
            ).start()

            created.append({"pg": pg["pg_name"], "role": role, "location": pg["location"]})

    return JSONResponse({
        "created":  len(created),
        "skipped":  len(skipped),
        "jobs":     created,
    })


def _blast_pg_workers(hiring_req: dict) -> None:
    """PG-specific blast — includes salary + accommodation perk in push body."""
    from services.pg_jobs_service import get_salary_for_role

    role      = hiring_req["role"]
    pg_name   = hiring_req["company"]
    location  = hiring_req["location"]
    salary    = hiring_req.get("salary") or get_salary_for_role(role)
    req_id    = hiring_req["id"]

    workers = _find_matching_workers(role)
    pinged  = {}
    sent    = 0
    for w in workers:
        try:
            result = notify_user(
                w["phone"],
                Content(
                    type="match",
                    title="PG Job: {role} at {pg_name}",
                    body="{location}{salary_part} + Free food & stay",
                    url="/app",
                ),
                params={
                    "role": role,
                    "pg_name": pg_name,
                    "location": location,
                    "salary_part": f" • {salary}" if salary else "",
                },
                extra_data={"request_id": req_id, "role": role, "is_pg": "true"},
                idempotency_key=f"pg_blast:{req_id}:{w['phone']}",
            )
            ok = result.devices_delivered > 0
        except Exception as exc:
            print(f"[PG BLAST] notify_user failed for {w['phone']}: {exc}")
            ok = False
        pinged[w["phone"]] = {
            "name":    w["name"],
            "status":  "pending",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "push_sent": ok,
        }
        if ok:
            sent += 1

    hiring_req["pinged_workers"]   = pinged
    hiring_req["workers_notified"] = len(pinged)
    hiring_req["push_sent"]        = sent
    _requests[req_id] = hiring_req
    _persist(req_id, hiring_req)
    print(f"[PG BLAST] {pg_name} / {role}: {len(pinged)} workers pinged ({sent} push delivered)")


@router.get("/worker/profile/{phone}")
async def get_worker_profile_endpoint(phone: str):
    """Employer fetches a worker's full profile (shown in profile sheet)."""
    profile = _get_worker_profile(phone)
    if not profile:
        return JSONResponse({"error": "Worker not found"}, status_code=404)
    return JSONResponse({"profile": profile})


@router.get("/employer/hiring-requests")
async def get_employer_hiring_requests(request: Request):
    phone = caller_phone(request)
    results = _fetch_by_employer(phone)
    # Attach interested-candidate profiles to each
    for r in results:
        interested = []
        for p, info in r.get("pinged_workers", {}).items():
            if info.get("status") == "interested":
                entry = {"name": info["name"]}   # phone stays server-side
                if info.get("profile"):
                    profile = {k: v for k, v in info["profile"].items() if k != "phone"}
                    entry.update(profile)
                interested.append(entry)
        r["interested_count"] = len(interested)
        r["interested_workers"] = interested
    return JSONResponse({"requests": results})


@router.get("/employer/hiring-request/{req_id}")
async def get_hiring_request(req_id: str):
    r = _fetch(req_id)
    if not r:
        return JSONResponse({"error": "Not found"}, status_code=404)
    interested = []
    for p, info in r.get("pinged_workers", {}).items():
        if info.get("status") == "interested":
            entry = {"name": info["name"]}   # phone stays server-side
            if info.get("profile"):
                profile = {k: v for k, v in info["profile"].items() if k != "phone"}
                entry.update(profile)
            interested.append(entry)
    r["interested_count"] = len(interested)
    r["interested_workers"] = interested
    return JSONResponse({"request": r})


@router.post("/employer/hiring-request/{req_id}/close")
async def close_hiring_request(req_id: str):
    r = _fetch(req_id)
    if not r:
        return JSONResponse({"error": "Not found"}, status_code=404)
    r["status"] = "closed"
    _requests[req_id] = r
    _persist(req_id, r)
    return JSONResponse({"success": True})


# ---------------------------------------------------------------------------
# Worker endpoints
# ---------------------------------------------------------------------------
@router.get("/worker/opportunities")
async def get_worker_opportunities(request: Request):
    """
    Return job opportunities (hiring requests) where the calling worker was pinged.
    Splits into: new (pending), interested (already said yes), not_interested.
    """
    phone = caller_phone(request)
    new_opps       = []
    interested_opps = []

    for r in _fetch_by_worker(phone):
        pw     = r.get("pinged_workers", {})
        status = pw.get(phone, {}).get("status", "pending")
        item   = {
            "request_id":  r["id"],
            "role":        r.get("role", ""),
            "role_label":  r.get("role_label", r.get("role", "")),
            "company":     r.get("company", ""),
            "location":    r.get("location", ""),
            "salary":      r.get("salary", ""),
            "when_needed": r.get("when_needed", ""),
            "notes":       r.get("notes", ""),
            "req_status":  r.get("status", "open"),
            "worker_status": status,
            "created_at":  r.get("created_at", ""),
        }
        if status == "pending" and r.get("status") in ("open", "reviewing"):
            new_opps.append(item)
        elif status == "interested":
            interested_opps.append(item)

    return JSONResponse({
        "new":        new_opps,
        "interested": interested_opps,
    })


@router.post("/worker/opportunity/{req_id}/respond")
async def worker_respond_opportunity(req_id: str, req: WorkerRespondRequest, request: Request):
    """Worker says 'interested' or 'not_interested' to a hiring request."""
    if req.response not in ("interested", "not_interested"):
        return JSONResponse({"error": "response must be 'interested' or 'not_interested'"}, status_code=400)

    worker_phone = caller_phone(request)

    r = _fetch(req_id)
    if not r:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if r.get("status") not in ("open", "reviewing"):
        return JSONResponse({"error": "This request is no longer active"}, status_code=400)

    pw = r.setdefault("pinged_workers", {})
    if worker_phone not in pw:
        return JSONResponse({"error": "You were not invited to this request"}, status_code=403)
    if pw[worker_phone].get("status") != "pending":
        return JSONResponse({"error": "Already responded"}, status_code=400)

    pw[worker_phone]["status"]       = req.response
    pw[worker_phone]["responded_at"] = datetime.now(timezone.utc).isoformat()

    # Enrich with full profile so employer can view without extra API calls
    if req.response == "interested":
        profile = _get_worker_profile(worker_phone)
        if profile:
            pw[worker_phone]["profile"] = profile

    if req.response == "interested":
        r["status"] = "reviewing"

        # Notify employer
        employer_phone = r.get("employer_phone", "")
        worker_name    = pw[worker_phone]["name"]
        role_label     = r.get("role_label", r["role"])
        company        = r.get("company", "")
        total_interest = sum(1 for p in pw.values() if p.get("status") == "interested")

        is_pg = r.get("is_pg_job", False)
        if is_pg:
            exp = pw[worker_phone].get("profile", {}).get("experience", "")
            loc = pw[worker_phone].get("profile", {}).get("location", "Delhi NCR")
            content_title = "{worker_name} is interested in {role_label}!"
            content_body  = "{exp} • {loc} — {count} candidate{plural} total"
            params = {
                "worker_name": worker_name,
                "role_label":  role_label,
                "exp":         exp,
                "loc":         loc,
                "count":       total_interest,
                "plural":      "s" if total_interest > 1 else "",
            }
        else:
            content_title = "New interest: {role_label} at {company}"
            content_body  = "{worker_name} wants to join — {count} candidate{plural} so far"
            params = {
                "worker_name": worker_name,
                "role_label":  role_label,
                "company":     company,
                "count":       total_interest,
                "plural":      "s" if total_interest > 1 else "",
            }

        def _notify_employer(p=params, t=content_title, b=content_body, ep=employer_phone, wp=worker_phone):
            try:
                notify_user(
                    ep,
                    Content(type="match", title=t, body=b, url="/hire"),
                    params=p,
                    extra_data={"request_id": req_id, "role": role_label},
                    idempotency_key=f"interest:{req_id}:{wp}",
                )
            except Exception as exc:
                print(f"[HIRING] notify employer failed for {ep}: {exc}")

        threading.Thread(target=_notify_employer, daemon=True).start()

    _requests[req_id] = r
    _persist(req_id, r)

    return JSONResponse({"success": True, "response": req.response})


# ---------------------------------------------------------------------------
# Direct interest — worker taps "Main Interested Hoon" on a catalog job
# ---------------------------------------------------------------------------
class DirectInterestBody(BaseModel):
    job_key:       str
    job_title:     str
    company:       str
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    worker_phone:  str | None = None
    availability:  str   # e.g. "this_week", "asap"


@router.post("/worker/direct-interest")
async def worker_direct_interest(body: DirectInterestBody, request: Request):
    """
    Worker expresses direct interest in a real catalog job (no hiring request needed).
    Stores the lead in Firestore and sends FCM push to any employer token tied to this job.
    """
    worker_phone = caller_phone(request)
    doc_id = f"{body.job_key}_{worker_phone}_{uuid.uuid4().hex[:6]}"
    record = {
        "job_key":       body.job_key,
        "job_title":     body.job_title,
        "company":       body.company,
        "worker_phone":  worker_phone,
        "availability":  body.availability,
        "status":        "new",
        "created_at":    datetime.now(timezone.utc).isoformat(),
    }

    def _save():
        try:
            from utils.db import db as _fs
            profile = _get_worker_profile(worker_phone) or {}
            record["worker_name"]    = profile.get("name", "Worker")
            record["worker_profile"] = profile
            _fs.collection("switch_direct_interests").document(doc_id).set(record)
        except Exception:
            pass

    threading.Thread(target=_save, daemon=True).start()
    return JSONResponse({"success": True, "doc_id": doc_id})


# ---------------------------------------------------------------------------
# Bridge call — telephonic interview between employer and worker
# ---------------------------------------------------------------------------
# Flow:
#   1. We call the WORKER first.
#   2. Worker picks up → Vobiz hits bridge-answer-worker → XML puts worker in conference room.
#   3. That same webhook fires an async call to the EMPLOYER.
#   4. Employer picks up → Vobiz hits bridge-answer-employer → XML puts employer in same room.
#   5. Both are now bridged. Neither ever sees the other's number.
# ---------------------------------------------------------------------------
_bridge_calls: dict = {}   # bridge_id → {employer_phone, worker_phone, request_id, ...}


def _normalize_phone(phone: str) -> str:
    """Strip formatting, ensure 91 country code prefix (no +)."""
    digits = phone.replace("+", "").replace("-", "").replace(" ", "")
    if not digits.startswith("91") and len(digits) == 10:
        digits = "91" + digits
    return digits


def _xml_response(xml: str):
    from fastapi.responses import Response as FastResponse
    return FastResponse(content=xml, media_type="application/xml")


class BridgeCallRequest(BaseModel):
    request_id:     str
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    employer_phone: str | None = None
    worker_name:    str   # used to look up phone server-side — never exposed to client


@router.post("/interview/bridge-call")
async def initiate_bridge_call(req: BridgeCallRequest, request: Request):
    """
    Step 1: call the worker. Worker's number stays on the server.
    """
    employer_phone = caller_phone(request)
    r = _fetch(req.request_id)
    if not r:
        return JSONResponse({"error": "Hiring request not found"}, status_code=404)

    worker_phone = None
    for phone, info in r.get("pinged_workers", {}).items():
        if (info.get("name", "").strip().lower() == req.worker_name.strip().lower()
                and info.get("status") == "interested"):
            worker_phone = phone
            break

    if not worker_phone:
        return JSONResponse({"error": "Worker not found in this request"}, status_code=404)

    bridge_id = str(uuid.uuid4())
    _bridge_calls[bridge_id] = {
        "employer_phone": employer_phone,
        "worker_phone":   worker_phone,
        "request_id":     req.request_id,
        "worker_name":    req.worker_name,
        "employer_called": False,
    }

    server_host      = os.getenv("SERVER_HOST", "api.relayy.world")
    worker_answer_url = f"https://{server_host}/api/switch/interview/bridge-answer-worker/{bridge_id}"
    hangup_url        = f"https://{server_host}/api/switch/interview/bridge-hangup/{bridge_id}"

    try:
        from services.vobiz_service import VobizService
        vobiz = VobizService()
        result = await vobiz.make_call(
            to_number=worker_phone,
            answer_url=worker_answer_url,
            hangup_url=hangup_url,
        )
        call_uuid = result.get("RequestUUID") or result.get("call_uuid") or ""
        _bridge_calls[bridge_id]["worker_call_uuid"] = call_uuid
        print(f"[BRIDGE] Calling worker first → worker={worker_phone} bridge={bridge_id}")
        return JSONResponse({"success": True, "bridge_id": bridge_id, "status": "calling_worker"})
    except Exception as exc:
        print(f"[BRIDGE] Worker call failed: {exc}")
        return JSONResponse({"error": f"Call failed: {exc}"}, status_code=500)


@router.post("/interview/bridge-answer-worker/{bridge_id}")
async def bridge_answer_worker(bridge_id: str):
    """
    Step 2: worker picked up. Put them in the conference room, then fire the employer call.
    """
    bridge = _bridge_calls.get(bridge_id)
    if not bridge:
        return _xml_response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Speak>Sorry, this call is no longer valid.</Speak></Response>'
        )

    worker_name = bridge.get("worker_name", "you")
    room_name   = f"switch_bridge_{bridge_id}"

    # Build conference XML — worker waits here with hold music
    from services.vobiz_service import VobizService
    vobiz = VobizService()
    xml = vobiz.build_conference_xml(
        room_name=room_name,
        intro_text=f"Namaste {worker_name}! Ek employer aapka interview lena chahte hain. Please hold karein.",
        wait_sound=True,
    )

    # Fire employer call in background (only once)
    if not bridge.get("employer_called"):
        bridge["employer_called"] = True
        asyncio.create_task(_call_employer(bridge_id))

    return _xml_response(xml)


async def _call_employer(bridge_id: str):
    """Background task: dial the employer after worker has picked up."""
    bridge = _bridge_calls.get(bridge_id)
    if not bridge:
        return
    server_host          = os.getenv("SERVER_HOST", "api.relayy.world")
    employer_answer_url  = f"https://{server_host}/api/switch/interview/bridge-answer-employer/{bridge_id}"
    hangup_url           = f"https://{server_host}/api/switch/interview/bridge-hangup/{bridge_id}"
    try:
        from services.vobiz_service import VobizService
        vobiz = VobizService()
        result = await vobiz.make_call(
            to_number=bridge["employer_phone"],
            answer_url=employer_answer_url,
            hangup_url=hangup_url,
        )
        call_uuid = result.get("RequestUUID") or result.get("call_uuid") or ""
        bridge["employer_call_uuid"] = call_uuid
        print(f"[BRIDGE] Employer called → employer={bridge['employer_phone']} bridge={bridge_id}")
    except Exception as exc:
        print(f"[BRIDGE] Employer call failed: {exc}")


@router.post("/interview/bridge-answer-employer/{bridge_id}")
async def bridge_answer_employer(bridge_id: str):
    """
    Step 4: employer picked up. Put them in the same conference room — now both sides are live.
    """
    bridge = _bridge_calls.get(bridge_id)
    if not bridge:
        return _xml_response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Speak>Sorry, this call is no longer valid.</Speak></Response>'
        )

    worker_name = bridge.get("worker_name", "the candidate")
    room_name   = f"switch_bridge_{bridge_id}"

    from services.vobiz_service import VobizService
    vobiz = VobizService()
    xml = vobiz.build_conference_xml(
        room_name=room_name,
        intro_text=f"Connecting you to {worker_name} now.",
    )
    return _xml_response(xml)


@router.post("/interview/bridge-hangup/{bridge_id}")
async def bridge_hangup(bridge_id: str):
    """Vobiz hits this when either leg ends — clean up."""
    _bridge_calls.pop(bridge_id, None)
    return JSONResponse({"ok": True})
