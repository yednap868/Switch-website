"""
Unified notification send path.

One event = one `notifications` row (durable record, powers the bell) + one
FCM push per active device. Content is fully parameterized via `Content` +
`params`; audience is resolved via `notification_audience.Audience`.

Public surface:
    notify_user(user_id, content, params, *, idempotency_key=None)
    notify_audience(audience, content, params, *, per_user_params=None,
                    idempotency_key_fn=None, dry_run=False)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from firebase_admin import messaging as fcm_messaging
from firebase_admin.exceptions import FirebaseError
from sqlalchemy.orm import Session

from models.sql_models import FcmToken, Notification
from services.notification_audience import Audience, resolve
from utils.firebase_init import initialize_firebase
from utils.postgres import get_db

DEFAULT_ICON = "https://app.switchlocally.com/icon-192.png"
PUSH_HOST = "https://app.switchlocally.com"


@dataclass
class Content:
    type: str = "generic"
    title: str = ""
    body: str = ""
    url: str = "/"
    icon: Optional[str] = None


@dataclass
class RenderedContent:
    type: str
    title: str
    body: str
    url: str
    icon: str


@dataclass
class DeviceResult:
    token: str
    delivered: bool
    error: Optional[str] = None


@dataclass
class SendResult:
    user_id: str
    notification_id: Optional[int]
    devices_attempted: int
    devices_delivered: int
    device_results: list[DeviceResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class BulkSendResult:
    audience: dict
    resolved_user_ids: list[str]
    dry_run: bool
    results: list[SendResult] = field(default_factory=list)

    @property
    def total_attempted(self) -> int:
        return sum(r.devices_attempted for r in self.results)

    @property
    def total_delivered(self) -> int:
        return sum(r.devices_delivered for r in self.results)


def render(content: Content, params: dict) -> RenderedContent:
    p = params or {}
    return RenderedContent(
        type=content.type.format_map(_SafeDict(p)) if "{" in content.type else content.type,
        title=content.title.format_map(_SafeDict(p)),
        body=content.body.format_map(_SafeDict(p)),
        url=content.url.format_map(_SafeDict(p)),
        icon=content.icon or DEFAULT_ICON,
    )


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _build_fcm_message(token: str, rendered: RenderedContent, notification_id: int, extra_data: dict) -> fcm_messaging.Message:
    data = {k: str(v) for k, v in (extra_data or {}).items()}
    data["url"] = rendered.url
    data["notification_id"] = str(notification_id)
    data["type"] = rendered.type

    link = rendered.url if rendered.url.startswith("http") else f"{PUSH_HOST}{rendered.url}"

    return fcm_messaging.Message(
        notification=fcm_messaging.Notification(title=rendered.title, body=rendered.body),
        data=data,
        token=token,
        android=fcm_messaging.AndroidConfig(priority="high"),
        webpush=fcm_messaging.WebpushConfig(
            notification=fcm_messaging.WebpushNotification(
                icon=rendered.icon,
                vibrate=[200, 100, 200],
                renotify=True,
                tag=str(notification_id),
            ),
            fcm_options=fcm_messaging.WebpushFCMOptions(link=link),
        ),
    )


def _is_unregistered(exc: Exception) -> bool:
    """FCM token is dead (uninstalled, revoked, expired). Disable it."""
    msg = str(exc).lower()
    return (
        "unregistered" in msg
        or "not-registered" in msg
        or "invalid-argument" in msg
        or "invalid registration" in msg
        or "registration-token-not-registered" in msg
    )


def _send_one(db: Session, user_id: str, rendered: RenderedContent, extra_data: dict, idempotency_key: Optional[str]) -> SendResult:
    if idempotency_key:
        existing = (
            db.query(Notification)
            .filter_by(user_id=user_id)
            .filter(Notification.data.like(f'%"idempotency_key": "{idempotency_key}"%'))
            .first()
        )
        if existing:
            return SendResult(
                user_id=user_id,
                notification_id=existing.id,
                devices_attempted=0,
                devices_delivered=0,
                skipped=True,
                skip_reason="idempotent_duplicate",
            )

    data_payload = dict(extra_data or {})
    data_payload["url"] = rendered.url
    if idempotency_key:
        data_payload["idempotency_key"] = idempotency_key

    notif = Notification(
        user_id=user_id,
        type=rendered.type,
        title=rendered.title,
        body=rendered.body,
        data=json.dumps(data_payload),
        created_at=time.time(),
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    tokens = (
        db.query(FcmToken)
        .filter(FcmToken.user_id == user_id, FcmToken.disabled_at.is_(None))
        .all()
    )

    device_results: list[DeviceResult] = []
    delivered = 0

    for tok in tokens:
        try:
            msg = _build_fcm_message(tok.token, rendered, notif.id, data_payload)
            fcm_messaging.send(msg)
            tok.last_seen_at = time.time()
            delivered += 1
            device_results.append(DeviceResult(token=tok.token, delivered=True))
        except FirebaseError as exc:
            err = str(exc)
            if _is_unregistered(exc):
                tok.disabled_at = time.time()
            device_results.append(DeviceResult(token=tok.token, delivered=False, error=err))
        except Exception as exc:
            err = str(exc)
            if _is_unregistered(exc):
                tok.disabled_at = time.time()
            device_results.append(DeviceResult(token=tok.token, delivered=False, error=err))

    db.commit()

    return SendResult(
        user_id=user_id,
        notification_id=notif.id,
        devices_attempted=len(tokens),
        devices_delivered=delivered,
        device_results=device_results,
    )


def notify_user(
    user_id: str,
    content: Content,
    params: Optional[dict] = None,
    *,
    extra_data: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
) -> SendResult:
    """Send a notification to a single user. Writes DB row + fires FCM to all active devices."""
    initialize_firebase()
    rendered = render(content, params or {})

    db = get_db()
    try:
        return _send_one(db, user_id, rendered, extra_data or {}, idempotency_key)
    finally:
        db.close()


def notify_audience(
    audience: Audience,
    content: Content,
    params: Optional[dict] = None,
    *,
    extra_data: Optional[dict] = None,
    per_user_params: Optional[Callable[[str], dict]] = None,
    idempotency_key_fn: Optional[Callable[[str], str]] = None,
    dry_run: bool = False,
) -> BulkSendResult:
    """
    Resolve an audience spec and send to everyone matched.

    - `params` is the shared base.
    - `per_user_params(user_id)` is merged over `params` per recipient for
      personalization (e.g. name, job-match-specific fields).
    - `idempotency_key_fn(user_id)` produces an idempotency key per recipient
      so re-runs of the same campaign don't double-notify anyone.
    - `dry_run=True` returns the resolved user_ids without sending.
    """
    initialize_firebase()
    db = get_db()
    try:
        user_ids = resolve(db, audience)
        bulk = BulkSendResult(
            audience=audience.to_dict(),
            resolved_user_ids=user_ids,
            dry_run=dry_run,
        )
        if dry_run:
            return bulk

        base_params = params or {}
        for uid in user_ids:
            merged = dict(base_params)
            if per_user_params:
                try:
                    merged.update(per_user_params(uid) or {})
                except Exception as exc:
                    print(f"[NOTIFY] per_user_params failed for {uid}: {exc}")
            rendered = render(content, merged)
            idk = idempotency_key_fn(uid) if idempotency_key_fn else None
            result = _send_one(db, uid, rendered, extra_data or {}, idk)
            bulk.results.append(result)
        return bulk
    finally:
        db.close()
