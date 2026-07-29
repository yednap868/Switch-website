"""
Firebase ID-token verification against the HearUs project + FastAPI dependency
for bearer-auth on Switch-app endpoints.

Why HearUs: the app's phone-auth flow runs against project `hearus-4f2fe`
(relay-15824 is parked behind a Google-side SMS gate). Backend ID-token
verification therefore targets HearUs specifically; relay's default
`firebase_admin` app is untouched and keeps serving Firestore / FCM.

The verifier tries three paths in order, mirroring `/firebase-verify`:
  1. firebase_admin.verify_id_token(token, app=_hearus_app)  — primary
  2. JWKS-based pyjwt verification with audience=hearus-4f2fe — fallback when
     the admin app failed to init (e.g. missing creds on a fresh deploy)
  3. firebase_admin.verify_id_token(token) on the default relay app — last
     resort, only for historical tokens minted against relay

Exports:
  verify_hearus_token(id_token)  → dict with uid/phone (raises ValueError)
  require_hearus_user             → FastAPI Depends; 401 on missing/invalid
  require_hearus_user_owns(user_id_path_param) → 403 on mismatch
"""

from __future__ import annotations

import os
import time
from typing import Optional

import requests as _requests
import jwt as _pyjwt
from jwt.algorithms import RSAAlgorithm as _RSAAlgorithm
from fastapi import Depends, HTTPException, Request

_HEARUS_PROJECT_ID = "hearus-4f2fe"

_GOOGLE_JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
_jwks_cache: dict = {}
_jwks_cached_at: float = 0.0


def _verify_via_jwks(id_token: str, project_id: str) -> dict:
    """Self-contained verification using Google's public JWKs. Cached 1h."""
    global _jwks_cache, _jwks_cached_at
    if not _jwks_cache or (time.time() - _jwks_cached_at) > 3600:
        resp = _requests.get(_GOOGLE_JWKS_URL, timeout=5)
        resp.raise_for_status()
        _jwks_cache = {k["kid"]: k for k in resp.json().get("keys", [])}
        _jwks_cached_at = time.time()
    header = _pyjwt.get_unverified_header(id_token)
    key_data = _jwks_cache.get(header.get("kid"))
    if not key_data:
        raise ValueError("no matching public key for token kid")
    public_key = _RSAAlgorithm.from_jwk(key_data)
    return _pyjwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=project_id,
        issuer=f"https://securetoken.google.com/{project_id}",
    )


def _get_hearus_admin_app():
    """Lazy import; returns the named HearUs firebase_admin app, or None."""
    try:
        import firebase_admin
        return firebase_admin.get_app("hearus_phone_auth")
    except Exception:
        return None


def verify_hearus_token(id_token: str) -> dict:
    """
    Verify an ID token minted by hearus-4f2fe.

    Returns a dict with at least {uid, phone_number, raw}. Raises ValueError
    on any verification failure.
    """
    if not id_token:
        raise ValueError("empty token")

    decoded: Optional[dict] = None
    last_err: Optional[Exception] = None

    hearus_app = _get_hearus_admin_app()
    if hearus_app is not None:
        try:
            from firebase_admin import auth as firebase_auth
            decoded = firebase_auth.verify_id_token(id_token, app=hearus_app)
        except Exception as e:
            last_err = e

    if decoded is None:
        try:
            decoded = _verify_via_jwks(id_token, _HEARUS_PROJECT_ID)
        except Exception as e:
            last_err = e

    if decoded is None:
        raise ValueError(f"token verification failed: {last_err}")

    phone_raw = decoded.get("phone_number", "") or ""
    phone = phone_raw.lstrip("+").replace(" ", "").replace("-", "")
    if not phone.startswith("91") and len(phone) == 10:
        phone = "91" + phone

    uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
    return {"uid": uid, "phone": phone, "phone_number": phone_raw, "raw": decoded}


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization") or request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    return auth[7:].strip()


def require_hearus_user(request: Request) -> dict:
    """
    FastAPI dependency. Verifies Authorization: Bearer <id_token> against HearUs.
    Returns {uid, phone, phone_number, raw} on success. Raises 401 otherwise.
    """
    token = _extract_bearer(request)
    try:
        return verify_hearus_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def caller_phone(request: Request) -> str:
    """
    Read the resolved caller phone (from the verified bearer token) off
    `request.state.user`. Available on every non-public request because
    `HearusBearerAuthMiddleware` populated it before the handler ran.

    Canonical form: 12-digit string starting with "91" (India).

    Raises 500 if called on a public/allowlisted route that didn't go through
    the middleware — those routes have no caller identity and shouldn't be
    asking for one.
    """
    user = getattr(request.state, "user", None)
    if not user or not user.get("phone"):
        raise HTTPException(
            status_code=500,
            detail="caller_phone() called on a route without bearer auth — "
                   "check HearusBearerAuthMiddleware allowlist",
        )
    return user["phone"]


def require_owner(user_id_param_name: str = "user_id"):
    """
    Returns a dependency that (a) verifies the bearer token, (b) ensures the
    token's phone matches the path/query user_id. 403 on mismatch.

    Path-param binding happens via request.path_params so callers don't need
    to restructure their signatures. Usage:

        @router.get("/profile/{user_id}")
        async def get_profile(user_id: str, user=Depends(require_owner("user_id"))):
            ...
    """
    def _inner(request: Request, user=Depends(require_hearus_user)) -> dict:
        target = request.path_params.get(user_id_param_name)
        if target is None:
            target = request.query_params.get(user_id_param_name)
        if not target:
            # No user_id to check against — treat as simple auth-required.
            return user
        # Accept either 91-prefixed or bare 10-digit matches on either side.
        a = str(target).lstrip("+").replace(" ", "").replace("-", "")
        b = user.get("phone", "")
        if a == b or a.lstrip("91") == b.lstrip("91"):
            return user
        raise HTTPException(status_code=403, detail="Forbidden: token does not match user")
    return _inner
