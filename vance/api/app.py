import json
import os
import threading
import time

import fastapi
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from api.admin_routes import router as admin_router
from api.calendar_routes import router as calendar_router
from api.routers import routers as API_ROUTERS
from models.sql_models import JobApplication
from utils.hearus_auth_middleware import HearusBearerAuthMiddleware
from utils.postgres import get_db

origins = [
    "https://profiles.vance.so",
    "https://live.vance.so",
    "http://localhost:5173",
    "http://localhost:3000",
    # Relayy domains (production)
    "https://relayy.world",
    "https://www.relayy.world",
    "https://app.relayy.world",
    "https://api.relayy.world",
    # Legacy switchlocally domains
    "https://switchlocally.com",
    "https://www.switchlocally.com",
    "https://app.switchlocally.com",
    "https://api.switchlocally.com",
    "*",  # Allow all origins for development - restrict in production
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all for now - fix CORS properly
        allow_credentials=False,  # Set to False when using *
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],
        expose_headers=["*"],
    ),
    Middleware(
        SessionMiddleware,
        secret_key="your-secret-key-here",
        https_only=True,  # required since you're on HTTPS
        same_site="none",  # allows cross-origin cookies
    ),
    # Bearer-auth gate for Switch-app endpoints. Verifies HearUs Firebase ID
    # tokens on every request except the documented public allowlist
    # (webhooks, admin Basic auth, opaque-token flows, auth bootstrap).
    # Rollout toggle: env HEARUS_AUTH_ENFORCE=0 flips to log-only mode.
    Middleware(HearusBearerAuthMiddleware),
]


def _joining_reminder_scheduler():
    """Background daemon: fires joining reminders at 7 AM and 8 PM IST daily."""
    from datetime import datetime, timedelta
    FIRE_HOURS_IST = {7, 20}
    last_fired = set()
    while True:
        try:
            now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
            key = (now_ist.date(), now_ist.hour)
            if now_ist.hour in FIRE_HOURS_IST and key not in last_fired:
                last_fired.add(key)
                if len(last_fired) > 10:
                    last_fired = {k for k in last_fired if k[0] == now_ist.date()}
                try:
                    from api.switch_placement_routes import _run_joining_reminders
                    _run_joining_reminders()
                except Exception as e:
                    print(f"[REMINDER_SCHEDULER] Error: {e}")
        except Exception as e:
            print(f"[REMINDER_SCHEDULER] Outer error: {e}")
        time.sleep(60)


def _expiry_checker():
    """Background daemon that expires stale applications every 30 minutes."""
    while True:
        time.sleep(1800)
        try:
            cutoff = time.time() - 86400
            db = get_db()
            try:
                stale = db.query(JobApplication).filter(
                    JobApplication.status.in_(["pending", "calling_employer", "employer_no_answer"]),
                    JobApplication.created_at < cutoff,
                ).all()
                for app in stale:
                    app.status = "expired"
                    try:
                        history = json.loads(app.status_history or "[]")
                    except (json.JSONDecodeError, TypeError):
                        history = []
                    history.append({"status": "expired", "at": time.time()})
                    app.status_history = json.dumps(history)
                if stale:
                    db.commit()
                    print(f"[EXPIRY] Expired {len(stale)} stale applications")
            finally:
                db.close()
        except Exception as e:
            print(f"[EXPIRY] Error: {e}")


def get_fastapi_app():
    # Initialize error tracking first

    app = fastapi.FastAPI(
        middleware=middleware,
        title="Vance API",
        version="0.0.5",
        description="Vance is an LLM powered networking agent.",
        docs_url="/api/docs",  # Custom Swagger UI URL
    )

    # Add routers
    for router in API_ROUTERS:
        app.include_router(router)

    # Add admin router
    app.include_router(admin_router)

    # Add calendar OAuth router
    app.include_router(calendar_router)

    # Serve KYC video uploads
    _uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(_uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

    # Start background expiry checker
    threading.Thread(target=_expiry_checker, daemon=True).start()

    # Start joining reminder scheduler (fires at 7 AM and 8 PM IST)
    threading.Thread(target=_joining_reminder_scheduler, daemon=True).start()

    return app
