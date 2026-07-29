"""
Admin endpoint for sending notifications to one user or a filtered audience.

Content is fully parameterized: caller supplies `title`, `body`, `url`, and
a free-form `params` dict whose values are interpolated into the content
strings via str.format_map.

Audience is parameterized via the Audience dataclass — filter by role,
regions, preferred_roles, employment_status, onboarding_complete, joining
window, employer, placement status.

Auth: X-Admin-Secret header matching ADMIN_NOTIFY_SECRET (falls back to
ADMIN_SECRET_KEY so it shares a secret with the HTML admin if desired).
This route is allowlisted public in the bearer middleware because the
shared secret is its own auth path.
"""

from __future__ import annotations

import os
import secrets as _secrets
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.notification_audience import Audience
from services.notification_service import Content, notify_audience, notify_user

router = APIRouter(prefix="/api/admin/notifications", tags=["admin-notifications"])

_ADMIN_SECRET = os.getenv("ADMIN_NOTIFY_SECRET") or os.getenv("ADMIN_SECRET_KEY") or ""


def _check_secret(provided: Optional[str]) -> None:
    if not _ADMIN_SECRET:
        raise HTTPException(status_code=503, detail="ADMIN_NOTIFY_SECRET not configured")
    if not provided or not _secrets.compare_digest(provided, _ADMIN_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")


class AudienceSpec(BaseModel):
    user_ids: Optional[list[str]] = None
    role: str = "any"                               # "worker" | "employer" | "any"
    regions: Optional[list[str]] = None
    preferred_roles: Optional[list[str]] = None
    employment_status: Optional[list[str]] = None
    onboarding_complete: Optional[bool] = None
    joined_after: Optional[float] = None
    joined_before: Optional[float] = None
    employer_phones: Optional[list[str]] = None
    placement_status: Optional[list[str]] = None
    has_active_token: bool = True

    def to_audience(self) -> Audience:
        return Audience(**self.model_dump())


class ContentSpec(BaseModel):
    type: str = "generic"                           # drives bell icon on NotificationBell
    title: str
    body: str
    url: str = "/"
    icon: Optional[str] = None

    def to_content(self) -> Content:
        return Content(
            type=self.type,
            title=self.title,
            body=self.body,
            url=self.url,
            icon=self.icon,
        )


class SendRequest(BaseModel):
    audience: AudienceSpec
    content: ContentSpec
    params: dict = Field(default_factory=dict)
    extra_data: dict = Field(default_factory=dict)
    idempotency_key_prefix: Optional[str] = None    # combined with user_id for per-user key
    dry_run: bool = False


class SendToUserRequest(BaseModel):
    user_id: str
    content: ContentSpec
    params: dict = Field(default_factory=dict)
    extra_data: dict = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


@router.post("/send")
async def admin_send(body: SendRequest, x_admin_secret: Optional[str] = Header(default=None)):
    """Resolve an audience and send a notification to everyone in it."""
    _check_secret(x_admin_secret)

    audience = body.audience.to_audience()
    content = body.content.to_content()

    idk_fn = None
    if body.idempotency_key_prefix:
        prefix = body.idempotency_key_prefix
        idk_fn = lambda uid, _p=prefix: f"{_p}:{uid}"

    bulk = notify_audience(
        audience,
        content,
        body.params,
        extra_data=body.extra_data,
        idempotency_key_fn=idk_fn,
        dry_run=body.dry_run,
    )

    return JSONResponse({
        "audience": bulk.audience,
        "dry_run": bulk.dry_run,
        "resolved_user_ids": bulk.resolved_user_ids,
        "resolved_count": len(bulk.resolved_user_ids),
        "total_devices_attempted": bulk.total_attempted,
        "total_devices_delivered": bulk.total_delivered,
        "results": [
            {
                "user_id": r.user_id,
                "notification_id": r.notification_id,
                "devices_attempted": r.devices_attempted,
                "devices_delivered": r.devices_delivered,
                "skipped": r.skipped,
                "skip_reason": r.skip_reason,
                "errors": [
                    {"token": d.token[:12] + "…", "error": d.error}
                    for d in r.device_results if d.error
                ],
            }
            for r in bulk.results
        ],
    })


@router.post("/send-to-user")
async def admin_send_to_user(body: SendToUserRequest, x_admin_secret: Optional[str] = Header(default=None)):
    """Send a notification to a single user_id directly."""
    _check_secret(x_admin_secret)

    result = notify_user(
        body.user_id,
        body.content.to_content(),
        body.params,
        extra_data=body.extra_data,
        idempotency_key=body.idempotency_key,
    )

    return JSONResponse({
        "user_id": result.user_id,
        "notification_id": result.notification_id,
        "devices_attempted": result.devices_attempted,
        "devices_delivered": result.devices_delivered,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
        "errors": [
            {"token": d.token[:12] + "…", "error": d.error}
            for d in result.device_results if d.error
        ],
    })


@router.post("/preview-audience")
async def admin_preview_audience(body: AudienceSpec, x_admin_secret: Optional[str] = Header(default=None)):
    """Resolve an audience spec without sending — for testing filters."""
    _check_secret(x_admin_secret)

    bulk = notify_audience(
        body.to_audience(),
        Content(type="generic", title="", body=""),
        {},
        dry_run=True,
    )
    return JSONResponse({
        "audience": bulk.audience,
        "resolved_user_ids": bulk.resolved_user_ids,
        "resolved_count": len(bulk.resolved_user_ids),
    })
