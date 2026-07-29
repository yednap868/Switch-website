"""
Bearer-auth middleware for Switch-app endpoints.

Enforces a valid `Authorization: Bearer <hearus_id_token>` on every request
unless the path matches a documented public allowlist (webhooks, admin
routes, opaque-token endpoints, auth bootstrap, health/docs, CORS preflight).

The token payload is attached to `request.state.user` so downstream handlers
can read it via:

    user = request.state.user
    user["phone"]  # e.g. "919876543210"
    user["uid"]    # Firebase UID

For ownership enforcement on user-scoped routes, see
`utils.hearus_auth.require_owner` — use it as an additional `Depends` on
routes that take a `{user_id}` path param so callers can't read/write
someone else's data even with a valid token.
"""

from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from utils.hearus_auth import verify_hearus_token


# Exact-path allowlist — no auth required, full stop.
_PUBLIC_EXACT = {
    "/",
    "/health",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
    # Auth bootstrap — the endpoint that mints the first session from a phone
    # auth ID token, plus the deprecated 2factor fallbacks (kept alive until
    # a separate cleanup PR retires them).
    "/api/candidate-onboarding/signup",
    "/api/candidate-onboarding/verify-otp",
    "/api/candidate-onboarding/firebase-verify",
    # Referral link redirect
}

# Path-prefix allowlist — everything under these paths is public.
_PUBLIC_PREFIXES = (
    # CORS preflight is handled by Starlette before we run; keep anyway.
    # WhatsApp / Meta webhooks (signed by Meta, not Firebase).
    "/api/webhooks/",
    "/api/whatsapp",
    # Switch WhatsApp business webhooks (separate WABA — Meta-signed).
    "/api/switch-wa/",
    # Vobiz voice webhooks + WS bridge — inbound from telephony provider.
    "/api/vobiz/",
    "/ws/vobiz-bridge",
    # Live-connect voice bridge (legacy Vance networking).
    "/ws/live-connect-bridge",
    "/api/live-connect/",
    # ElevenLabs post-call webhooks (signed with ELEVENLABS_WH_SECRET).
    "/api/elevenlabs/",
    # Admin — separate auth (HTTP Basic / X-Admin-Key). Covers /admin/*,
    # /api/admin/*, and the Switch admin-payments JSON routes that live
    # under /api/switch/admin/ but use X-Admin-Key header auth.
    "/admin",
    "/api/admin",
    "/api/switch/admin/",
    # WhatsApp blast ops endpoints — BLAST_ADMIN_KEY query/header auth.
    "/api/blast/",
    # WhatsApp blast click-tracking redirects — opaque-token, public.
    "/wa/",
    # SMS-tracking click redirects (public short links).
    "/api/sms/",
    "/api/switch/r/",
    "/api/switch/sms-stats/",
    # Vobiz "answer" webhook for employer-shortlist call — invoked by telephony
    # provider, not by an authenticated app client.
    "/api/switch/employer/shortlist-answer",
    # Vobiz bridge-call webhooks (worker/employer answer + hangup) — same story.
    "/api/switch/interview/bridge-answer-worker/",
    "/api/switch/interview/bridge-answer-employer/",
    "/api/switch/interview/bridge-hangup/",
    # Worker ID-card QR verification — employer scans a printed QR to verify
    # a worker's placement. Public by design (no bearer at scan time); the
    # response is scoped to non-sensitive card fields only.
    "/api/switch/worker-card/",
    # Employer match landing page — opaque-token authenticated.
    "/api/employer-match/",
    # Placement token flows — opaque-token.
    "/api/switch/checkin-context/",
    "/api/switch/checkin/",
    "/api/switch/verify-context/",
    "/api/switch/verify/",
    # Static / framework.
    "/static/",
    "/docs",
    "/redoc",
)

# Regex allowlist for paths that can't be expressed as simple prefixes.
# Currently only used for the ElevenLabs signed webhook URL pattern, if any.
_PUBLIC_REGEX: tuple[re.Pattern, ...] = ()


def _is_public(path: str, method: str) -> bool:
    if method == "OPTIONS":  # CORS preflight
        return True
    if path in _PUBLIC_EXACT:
        return True
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    for rgx in _PUBLIC_REGEX:
        if rgx.match(path):
            return True
    return False


class HearusBearerAuthMiddleware(BaseHTTPMiddleware):
    """
    Rejects any request to a non-public path that lacks a valid HearUs
    bearer token. Attaches decoded user info to `request.state.user` for
    authenticated requests.

    Enforcement is not toggleable — every non-allowlisted path requires a
    valid token, period. If a route legitimately needs to be open, add it
    to the allowlist in this file.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if _is_public(path, method):
            return await call_next(request)

        auth = request.headers.get("Authorization") or request.headers.get("authorization") or ""
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else None

        user = None
        err: str | None = None
        if token:
            try:
                user = verify_hearus_token(token)
            except Exception as e:
                err = str(e)

        if user is None:
            print(f"[AUTH] reject {method} {path} — {'invalid' if token else 'missing bearer'}: {err or 'no token'}")
            return JSONResponse(
                {"detail": "Authentication required"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="switch-app"'},
            )

        request.state.user = user
        return await call_next(request)
