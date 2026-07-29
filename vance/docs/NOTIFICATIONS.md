# Notifications

One system. Every notification = one durable DB row (powers the in-app bell) + one FCM push per active device (powers the lock-screen banner). Content is parameterized; audience is parameterized; nothing is hard-coded.

---

## Architecture

```
caller code
    │
    ▼
services.notification_service.notify_user(user_id, content, params)
services.notification_service.notify_audience(audience, content, params)
    │
    ├─── resolve audience  →  list[user_id]       (services.notification_audience.resolve)
    │
    ├─── render content    →  title, body, url    (str.format_map with params)
    │
    ├─── INSERT notifications row                 (powers NotificationBell.jsx)
    │
    └─── for each active fcm_tokens row:
             messaging.send(...)                  (lock-screen push)
             on UNREGISTERED → disable token      (auto-cleanup)
```

Admin endpoints in `api/admin_notifications_routes.py` are thin HTTP wrappers over the two service functions.

---

## Files

| File | Role |
|---|---|
| `services/notification_service.py` | `Content`, `notify_user`, `notify_audience`, `render` |
| `services/notification_audience.py` | `Audience`, `resolve` — filter → list[user_id] |
| `api/admin_notifications_routes.py` | `/api/admin/notifications/{send,send-to-user,preview-audience}` |
| `api/switch_booking_routes.py` | `/api/switch/fcm-token` — bearer-authenticated device registration |
| `models.sql_models.FcmToken` | Device-token table (token PK, user_id, phone, role, platform, disabled_at) |
| `models.sql_models.Notification` | Durable per-user feed row |

---

## Content

```python
@dataclass
class Content:
    type:  str = "generic"   # drives bell icon — see frontend TYPE_ICONS
    title: str               # supports {placeholder}
    body:  str               # supports {placeholder}
    url:   str = "/"         # supports {placeholder}, deep-link
    icon:  Optional[str] = None
```

### Parameter interpolation

`title`, `body`, `url` are passed through `str.format_map` with a "safe" dict (missing keys are left literal rather than raising). Params come from the caller:

```python
Content(
    type="interview",
    title="Interview: {role} at {company}",
    body="{when} • {location}",
    url="/app/interviews/{application_id}",
)
# params={"role": "Cook", "company": "Barista", "when": "Fri 3pm",
#         "location": "MG Road", "application_id": 42}
```

### `type` → bell icon

The `type` field on a notification drives which Lucide icon appears in the bell. Mapping lives in `frontend/src/components/NotificationBell.jsx`:

| `type` | Icon |
|---|---|
| `match` | Heart |
| `view` | Eye |
| `interview` | Calendar |
| `hired` | Trophy |
| `expiry` | Clock |
| anything else | Bell (default) |

If you introduce a new type, add it to `TYPE_ICONS` so the bell renders properly.

---

## Audience

`services.notification_audience.Audience` — a parameterized spec that filters the user base down to a list of `user_id`s. All fields AND together. Explicit `user_ids` short-circuits everything else (you're naming people).

### Filter fields

| Field | Type | Semantics | Backing columns |
|---|---|---|---|
| `user_ids` | `list[str]` | Explicit recipient list; short-circuits all other filters | — |
| `role` | `"worker" \| "employer" \| "any"` | Which side of the marketplace | determines whether we search worker tables or employer tables |
| `regions` | `list[str]` | City / area substrings (case-insensitive `ILIKE`) | `users.location`, `candidates.area`, `employer_profiles.location` |
| `preferred_roles` | `list[str]` | Job roles the worker targets | `candidates.previous_roles` (JSON), `user_profiles.role`, `users.job_role`, `users.previous_role` |
| `employment_status` | `list[str]` | Worker's current availability | `candidates.status` (e.g. `AVAILABLE`, `PLACED`, `INTERVIEWING`) |
| `onboarding_complete` | `bool` | Profile completeness threshold | `candidates.profile_completeness_score >= 80` |
| `joined_after` | `float` (unix ts) | Signed up on/after this time | `candidates.created_at` for workers, `employer_profiles.created_at` for employers |
| `joined_before` | `float` (unix ts) | Signed up on/before this time | same |
| `employer_phones` | `list[str]` | Workers currently placed with these employers (or the employers themselves) | `placements.employer_phone` / `employer_profiles.phone` |
| `placement_status` | `list[str]` | Stage of placement pipeline | `placements.status` (e.g. `matched`, `interview`, `hired`, `active`) |
| `has_active_token` | `bool` (default `True`) | Only include users with at least one non-disabled FCM token | `fcm_tokens.disabled_at IS NULL` |

### Audience examples

```python
# All Gurgaon cooks who finished onboarding and have a device registered.
Audience(
    role="worker",
    regions=["Gurgaon"],
    preferred_roles=["Cook", "Chef"],
    onboarding_complete=True,
)

# Every worker who joined in the last 7 days.
Audience(
    role="worker",
    joined_after=time.time() - 7 * 86400,
)

# Workers currently placed with a specific employer.
Audience(
    role="worker",
    employer_phones=["919876543210"],
    placement_status=["active", "hired"],
)

# Two specific people, no filters.
Audience(user_ids=["919876543210", "919123456789"])

# All employers.
Audience(role="employer")
```

---

## Programmatic use

### One user

```python
from services.notification_service import Content, notify_user

result = notify_user(
    user_id="919876543210",
    content=Content(
        type="hired",
        title="You're hired!",
        body="{company} hired you",
        url="/app/applications/{application_id}",
    ),
    params={"company": "Barista", "application_id": 42},
    idempotency_key="hired:42",   # re-runs won't duplicate
)
# SendResult(user_id, notification_id, devices_attempted, devices_delivered, device_results, skipped)
```

### Audience fan-out

```python
from services.notification_audience import Audience
from services.notification_service import Content, notify_audience

bulk = notify_audience(
    audience=Audience(role="worker", regions=["Gurgaon"], onboarding_complete=True),
    content=Content(
        type="match",
        title="Naya Kaam: {role}",
        body="{company}, {location} • {salary}",
        url="/app",
    ),
    params={"role": "Cook", "company": "Barista",
            "location": "MG Road", "salary": "₹18,000/month"},
    idempotency_key_fn=lambda uid: f"barista_cook_apr21:{uid}",
    dry_run=False,
)
# BulkSendResult(audience, resolved_user_ids, dry_run, results, total_attempted, total_delivered)
```

Per-user personalization via `per_user_params`:

```python
notify_audience(
    audience=Audience(role="worker", employer_phones=["91..."], placement_status=["active"]),
    content=Content(type="generic", title="Hi {name}!", body="Salary credited: ₹{amount}"),
    params={"amount": "15000"},
    per_user_params=lambda uid: {"name": _lookup_name(uid)},
)
```

### Idempotency

`notify_user(idempotency_key=...)` and `notify_audience(idempotency_key_fn=...)` stamp the key into the notification's `data` JSON. On re-run, the sender sees an existing row with the same key for that user and skips — returns `skipped=True, skip_reason="idempotent_duplicate"`. Use it for:

- Event-driven sends where the event could fire twice (`f"hired:{application_id}"`)
- Campaign blasts you might re-run (`f"barista_cook_apr21:{user_id}"`)

---

## Admin HTTP API

Auth: header `X-Admin-Secret: <ADMIN_NOTIFY_SECRET>`. Endpoints return 503 until the env var is set; they return 401 on wrong/missing secret.

All endpoints are under `/api/admin/notifications`.

### `POST /send` — audience fan-out

```bash
curl -X POST https://api.relayy.world/api/admin/notifications/send \
  -H "X-Admin-Secret: $ADMIN_NOTIFY_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "audience": {
      "role": "worker",
      "regions": ["Gurgaon"],
      "preferred_roles": ["Cook", "Chef"],
      "onboarding_complete": true
    },
    "content": {
      "type": "match",
      "title": "Naya Kaam: {role}",
      "body": "{company}, {location} • {salary}",
      "url": "/app"
    },
    "params": {
      "role": "Cook",
      "company": "Barista",
      "location": "MG Road",
      "salary": "₹18,000/month"
    },
    "idempotency_key_prefix": "barista_cook_apr21",
    "dry_run": false
  }'
```

Response:

```json
{
  "audience": {...},
  "dry_run": false,
  "resolved_user_ids": ["919...", "918..."],
  "resolved_count": 12,
  "total_devices_attempted": 14,
  "total_devices_delivered": 13,
  "results": [
    {"user_id": "919...", "notification_id": 481, "devices_attempted": 1,
     "devices_delivered": 1, "skipped": false, "errors": []},
    ...
  ]
}
```

### `POST /send-to-user` — single recipient

```bash
curl -X POST https://api.relayy.world/api/admin/notifications/send-to-user \
  -H "X-Admin-Secret: $ADMIN_NOTIFY_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "919876543210",
    "content": {
      "type": "generic",
      "title": "App update available",
      "body": "Tap to refresh and get the latest features",
      "url": "/"
    },
    "idempotency_key": "app_update_v1_2_3"
  }'
```

### `POST /preview-audience` — resolve without sending

For sanity-checking a filter before you commit to a blast. Returns the matching `user_id` list.

```bash
curl -X POST https://api.relayy.world/api/admin/notifications/preview-audience \
  -H "X-Admin-Secret: $ADMIN_NOTIFY_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "worker",
    "regions": ["Gurgaon"],
    "placement_status": ["active"]
  }'
```

---

## Client registration (PWA)

The frontend registers a device token for the authenticated user at `POST /api/switch/fcm-token`. Identity comes from the bearer — body carries only the device metadata.

```js
// after Notification.requestPermission() === 'granted'
const token = await getToken(messaging, { vapidKey: VITE_FIREBASE_VAPID_KEY });
await apiFetch('/api/switch/fcm-token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ token, platform: 'web', role: 'worker' }),
});
```

Backend upserts into `fcm_tokens` keyed by `token`. Re-registering the same token refreshes `last_seen_at` and clears `disabled_at` (handles reinstall / re-grant).

---

## Click-through contract

```
user taps push
  │
  ▼
firebase-messaging-sw.js: notificationclick
  │
  ├── focused tab open? → postMessage({type: "NOTIFICATION_CLICK", url, notificationId})
  │                      → client.focus()
  │
  └── no tab open?       → clients.openWindow(`${url}?notif=${notificationId}`)
                            │
                            ▼
                         useNotificationClick (on SPA mount)
                            │
                            ├── PUT /api/switch/notifications/:id/read (with bearer)
                            ├── navigate if url is local
                            └── bump bell refresh token
```

`useNotificationClick` handles both branches: the message listener and the cold-open query-string case. It strips `?notif=<id>` from the URL after consuming it, so refreshes don't re-fire.

---

## Token lifecycle

| Event | Outcome |
|---|---|
| First registration | `INSERT fcm_tokens` with `disabled_at=NULL` |
| Re-registration (same token) | `UPDATE` last_seen_at, clear disabled_at |
| Registration after reinstall (new token) | new row; old token stays until FCM fails it |
| FCM returns `UNREGISTERED` / `INVALID_ARGUMENT` | service sets `disabled_at = now()`, excluded from future sends |
| User grants permission on a second device | additional row, same `user_id` — all sends fan out to both |

No manual cleanup needed.

---

## Environment variables

| Variable | Where | Who generates it | Required? |
|---|---|---|---|
| `ADMIN_NOTIFY_SECRET` | Railway (backend) | **You** — `openssl rand -hex 32` | For admin endpoints. Boot succeeds without it; endpoints return 503 |
| `VITE_FIREBASE_VAPID_KEY` | Vercel (frontend) | **Firebase Console** — `relay-15824` → Project Settings → Cloud Messaging → Web Push certificates | Required. Without it, `getToken()` no-ops and no device registers |
| `FIREBASE_CREDENTIALS_JSON` / `FIREBASE_CREDENTIALS_PATH` | Railway (backend) | Firebase service account | Already set; needed for `messaging.send` |

---

## Observability

Each send returns a result struct with per-device outcomes. Logs:

- Successful send: no log (kept quiet)
- `notify_user` / `notify_audience` failures: printed with user_id
- FCM device-level errors: captured in `device_results[].error` on the return value

If you need persistent audit trails, the `notifications` table is that trail — every send inserts a row with `type`, `title`, `body`, `data` (JSON including `url`, `idempotency_key`, and whatever `extra_data` the caller passed).

---

## Adding a new notification type

1. Call `notify_user` or `notify_audience` with a `Content(type="your_new_type", ...)` — no registry to update on the backend.
2. If you want a custom bell icon, add `your_new_type` to `TYPE_ICONS` in `frontend/src/components/NotificationBell.jsx`. Otherwise it falls back to the Bell icon.

That's it. No schema change, no template file, no deployment coordination.
