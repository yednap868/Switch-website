# Server-side ownership scoping — route-by-route plan

Every "Category A" route drops its URL/body user_id param; handler reads caller's phone from `request.state.user["phone"]`. "Category B" keeps the URL param (caller viewing someone else's data). "Category C/D/E" already fine.

## Category A — self-scoped (drop URL/body user_id, use token)

| Route | File | Change |
|---|---|---|
| `GET  /api/switch/profile/{user_id}` | switch_routes.py:154 | → `GET /api/switch/profile` |
| `PUT  /api/switch/profile/{user_id}` | switch_routes.py:267 | → `PUT /api/switch/profile` |
| `POST /api/switch/upload-photo/{user_id}` | switch_routes.py:431 | → `POST /api/switch/upload-photo` |
| `PUT  /api/switch/users/{user_id}/training-progress` | switch_routes.py:401 | → `PUT /api/switch/users/training-progress` |
| `GET  /api/switch/applications/{user_id}` | switch_routes.py:974 | → `GET /api/switch/applications` |
| `PUT  /api/switch/applications/{user_id}/{job_id}` | switch_routes.py:1556 | → `PUT /api/switch/applications/{job_id}` (caller is self) |
| `POST /api/switch/apply` | switch_routes.py:484 | body: drop user_id, use token |
| `POST /api/switch/swipe` | switch_routes.py:555 | body: drop user_id, use token |
| `POST /api/switch/swipe-apply` | switch_routes.py:652 | body: drop user_id, use token |
| `GET  /api/switch/swipes-remaining/{user_id}` | switch_routes.py:637 | → `GET /api/switch/swipes-remaining` |
| `GET  /api/switch/notifications/{user_id}` | switch_routes.py:2849 | → `GET /api/switch/notifications` |
| `POST /api/switch/delivery-apply` | switch_routes.py:749 | body: drop user_id |
| `POST /api/switch/delivery-docs/upload/{user_id}/{job_id}` | switch_routes.py:859 | → `POST /api/switch/delivery-docs/upload/{job_id}` |
| `GET  /api/switch/delivery-docs/{user_id}/{job_id}` | switch_routes.py:943 | → `GET /api/switch/delivery-docs/{job_id}` |
| `POST /api/switch/contacts` | switch_routes.py:1698 | body ContactsUploadRequest: drop user_id |
| `POST /api/switch/fcm-token` | switch_booking_routes.py:153 | body: drop phone |
| `POST /api/switch/track-referral` | switch_routes.py:1613 | body: drop user_id |
| `GET  /api/candidate-profile/{user_id}` | candidate_profile_routes.py:44 | → `GET /api/candidate-profile` |
| `PUT  /api/candidate-profile/{user_id}` | candidate_profile_routes.py:138 | → `PUT /api/candidate-profile` |
| `POST /api/candidate-profile/{user_id}/upload-photo` | candidate_profile_routes.py:243 | → `POST /api/candidate-profile/upload-photo` |
| `POST /api/community/post` | community_routes.py:129 | body: drop user_id |
| `POST /api/community/post/{post_id}/like` | community_routes.py:169 | body: drop user_id |
| `POST /api/community/post/{post_id}/comment` | community_routes.py:212 | body: drop user_id |
| `GET  /api/community/feed` | community_routes.py:57 | query ?user_id: drop, use token |
| `POST /api/switch/jyoti-call` | switch_routes.py:3133 | body: drop user_id |

### Employer-side self-scoped

| Route | File | Change |
|---|---|---|
| `GET  /api/switch/employer/profile/{phone}` | switch_routes.py:2925 | → `GET /api/switch/employer/profile` |
| `PUT  /api/switch/employer/profile/{phone}` | switch_routes.py:2963 | → `PUT /api/switch/employer/profile` |
| `POST /api/switch/employer/post-job` | switch_routes.py:1884 | body: drop employer_phone |
| `GET  /api/switch/employer/my-jobs/{employer_phone}` | switch_routes.py:2017 | → `GET /api/switch/employer/my-jobs` |
| `GET  /api/switch/employer/applications/{employer_phone}` | switch_routes.py:1960 | → `GET /api/switch/employer/applications` |
| `GET  /api/switch/employer/inbox/{employer_phone}` | switch_routes.py:2390 | → `GET /api/switch/employer/inbox` |
| `GET  /api/switch/employer/matched-candidates/{employer_phone}` | switch_routes.py:2516 | → `GET /api/switch/employer/matched-candidates` |
| `POST /api/switch/employer/shortlist` | switch_routes.py:2071 | body: drop employer_phone |
| `POST /api/switch/employer/shortlist-answer` | switch_routes.py:2178 | body: drop employer_phone |
| `POST /api/switch/employer/batch-action` | switch_routes.py:2460 | body: drop employer_phone |
| `POST /api/switch/employer/express-interest` | switch_routes.py:2571 | body: drop worker_phone? Actually this is employer→worker; keep worker, drop employer. |
| `POST /api/switch/employer/accept-interest` | switch_routes.py:2656 | same |
| `POST /api/switch/interview/schedule` | switch_routes.py:2711 | body: drop employer_phone |
| `POST /api/switch/interview/confirm` | switch_routes.py:2769 | body: drop user/employer_phone |
| `POST /api/switch/interview/outcome` | switch_routes.py:2796 | body: drop employer_phone |
| `POST /api/switch/employer/hiring-request/create` | switch_booking_routes.py:373 | body: drop phone |
| `GET  /api/switch/employer/hiring-requests/{phone}` | switch_booking_routes.py:537 | → `GET /api/switch/employer/hiring-requests` |
| `GET  /api/switch/employer/hiring-request/{req_id}` | switch_booking_routes.py:555 | keep req_id; drop scope implicit to caller |
| `POST /api/switch/employer/hiring-request/{req_id}/close` | switch_booking_routes.py:573 | same |
| `POST /api/switch/worker/direct-interest` | switch_booking_routes.py:700 | body: drop worker phone, use token |
| `GET  /api/switch/worker/opportunities/{phone}` | switch_booking_routes.py:587 | → `GET /api/switch/worker/opportunities` |
| `POST /api/switch/worker/opportunity/{req_id}/respond` | switch_booking_routes.py:623 | keep req_id; drop phone from body |

## Category B — cross-user reads (keep param)

| Route | Reason |
|---|---|
| `GET /api/switch/worker-photo/{user_id}` | Employer viewing worker photo in card |
| `GET /api/switch/worker/profile/{phone}` | Employer viewing worker full profile |
| `GET /api/switch/available-workers` | Public listing |
| `GET /api/switch/jobs/jobhai-feed` | Public jobs feed |
| `GET /api/switch/jobs/feed/{candidate_id}` | Personalized feed — ambiguous, keep for now |
| `PUT /api/switch/notifications/{notification_id}/read` | notification_id is not a user_id |
| `POST /api/switch/applications/{application_id}/no-show` | application_id is not a user_id (employer no-show) |
| `GET /api/switch/blast/active` | Worker polls all active blasts |
| `POST /api/switch/blast` | Worker creates (body has no user_id; caller is in token) → actually Cat A |
| `POST /api/switch/blast/{blast_id}/respond` | Worker responds to own-created blast; Cat A |
| `GET /api/switch/blast/{blast_id}/stats` | Probably employer viewing blast response stats |
| `GET /api/switch/coach` | Worker's AI coach stream; body has user_id → Cat A |
| `GET /api/switch/photo-stats` | Admin? |
| `POST /api/switch/interview/bridge-call` | Either side initiates; needs checking |
| `POST /api/switch/jobs/{job_id}/select-candidate` | Employer selecting; body has employer_phone? → Cat A if so |

## Category C — opaque-token allowlisted (no change)

- `/hire/:token`, `/hire/:token/:action`
- `/checkin-context/:token`, `/checkin/:token/submit`
- `/verify-context/:token`, `/verify/:token/submit`
- `/employer-match/:token`

## Category D — admin / webhook / public (no change)

- `/admin/*`, `/api/webhooks/*`, `/api/vobiz/*`, `/ws/vobiz-bridge`, ElevenLabs, SMS redirects
- `/api/candidate-onboarding/signup`, `/verify-otp`, `/firebase-verify`
- `/api/switch/r/{campaign}`, `/api/switch/sms-stats/{campaign}`
- `/api/switch/send-whatsapp-otp`, `/verify-whatsapp-otp`, `/call-otp` — deprecated; stays open, separate cleanup PR

## Tasks

### Backend
For each Category A route:
1. Change route path to drop the user_id param.
2. Change handler signature: add `request: Request` (or use existing), read `phone = request.state.user["phone"]`.
3. Remove user_id from Pydantic body schemas where applicable.
4. Keep handler body logic identical; just source the phone from token.

### Frontend
For each Category A call site:
1. Remove `/${userId}` from URL template.
2. Remove `user_id` / `phone` field from POST/PUT body payloads.

### Testing
- Build frontend.
- Local smoke: log in as worker, hit profile read → 200 with self data. Hit profile write → 200.
- Local smoke: log in, try to bypass by sending `user_id: "someone_else"` in body — confirm it's ignored (handler uses token phone).

### Rollback
Revert commits, redeploy. Low-risk: a bad deploy would 401 or 404 specific routes, not corrupt data.
