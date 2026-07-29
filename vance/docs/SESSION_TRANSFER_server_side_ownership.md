# Session transfer — server-side ownership scoping

## Objective

After PR #22 (Vance-2025/Vance) closes "any authenticated user can hit any endpoint," this work closes the next door: **handlers must derive the caller's identity from the verified bearer token (`request.state.user["phone"]`) rather than trusting URL path params or request-body fields.** The frontend stops sending `user_id` / `phone` / `employer_phone` in the URL or body because the server ignores what it's sent on self-scoped endpoints.

End state:

- Self-scoped endpoints (Category A): URL/body param removed; handler reads `caller_phone(request)`.
- Cross-user reads (Category B): keep the path param — the token identifies the caller, the param identifies the target.
- Opaque-token routes (Category C): already authenticated by the token in the URL, untouched.
- Admin/webhooks/deprecated OTP (Category D/E): allowlisted in middleware, untouched.

## Plan

Full route-by-route classification lives at `backend/docs/server-side-ownership-plan.md` (copied into the repo on this branch). That doc is the source of truth for which routes go in which category and what each rewrite looks like. Read it first.

Two prerequisites (both shipped already):

- Vance-2025/Vance#22 — `HearusBearerAuthMiddleware` enforces bearer auth on every non-allowlisted path. Sets `request.state.user` on success.
- `utils/hearus_auth.py` — exports `caller_phone(request)` which reads `request.state.user["phone"]`, raising 500 if missing (which would mean the route is wrongly on the public allowlist).

## Progress so far

Branch: `server-side-ownership` (stacked on `bearer-auth-all-routes`, i.e. PR #22). Backend route migrations are now complete end-to-end across the five in-scope routers; frontend call-site work is still TODO.

**Backend — complete (as of 2026-04-20):**

All Category A routes in the following files now derive caller identity from `caller_phone(request)` and no longer trust URL/body user_id / phone / employer_phone. Deprecated fields are kept `Optional` with a `# DEPRECATED: candidate for deletion` comment so older clients continue to validate during rollout.

- `api/switch_routes.py` — worker-side (profile, applications, swipe, swipe-apply, apply, delivery-apply, delivery-docs GET + upload, track-referral, contacts, jyoti-call, training-progress, notifications, swipes-remaining, blast + blast/active + blast/respond) and employer-side (profile GET/PUT, post-job, my-jobs, applications, inbox, matched-candidates, shortlist, express-interest, accept-interest).
- `api/switch_booking_routes.py` — fcm-token, employer/hiring-request/create, employer/hiring-requests, worker/opportunities, worker/opportunity/{req_id}/respond, worker/direct-interest, interview/bridge-call.
- `api/candidate_profile_routes.py` — GET/PUT /api/candidate-profile, POST /api/candidate-profile/upload-photo.
- `api/community_routes.py` — GET /feed, POST /post, POST /post/{id}/like, POST /post/{id}/comment.
- `api/switch_practice_routes.py` — POST /practice-payment, POST /practice-payment/verify. Caught during the frontend sweep, not in the original 5-file scope.
- `utils/hearus_auth.py` — `caller_phone(request)` helper (from earlier in the session).

**Middleware allowlist additions this session:**

- `/api/switch/employer/shortlist-answer` (Vobiz answer webhook).
- `/api/switch/interview/bridge-answer-worker/`, `/bridge-answer-employer/`, `/bridge-hangup/` (all Vobiz webhooks on the critical call path — previously would have 401'd Vobiz and silently broken bridge interviews).

**Bonus cleanup from earlier in the session** (commit `14fd5db`):
- Deleted all 21 manual `@router.options(...)` handlers across 8 files. CORSMiddleware already handles browser preflight; the manual handlers were cargo-culted from a 2026-01 misdiagnosis (fastapi#1849). Verified no regressions via curl-level preflight checks.

**Out-of-scope for this PR** (flagged by the plan, deliberately untouched):
- Routes that take a non-user path param and have no ownership check (`/employer/batch-action`, `/interview/{schedule,confirm,outcome}`, `/employer/hiring-request/{req_id}(+close)`, `/applications/{application_id}/no-show`, `/jobs/{job_id}/select-candidate`). The token authenticates the caller, but the handler doesn't restrict which `application_id` / `req_id` / `job_id` they can touch. That's a separate ownership-policy PR.
- Category B routes (cross-user reads like `/worker-photo/{user_id}`, `/worker/profile/{phone}`, `/available-workers`) — keeping path params is correct; token authenticates the viewer.
- Category C opaque-token flows (`/hire/:token`, `/checkin/:token`, `/verify/:token`, `/employer-match/:token`) — authenticated by the token-in-URL, no middleware change needed.
- Category D/E admin, webhook, and deprecated OTP endpoints — already allowlisted.

**Frontend — complete** (yednap868/Switch-app#7, stacked on #6):
- URL template sweep across `SwitchApp.jsx`, `EmployerApp.jsx`, hooks, and components — every `/${userId}` / `/${phone}` / `/${employerPhone}` dropped on Category A calls.
- Body-field sweep — `user_id`, `phone`, `employer_phone`, `worker_phone`, `employer_id`, `referee_user_id` removed from the matching POST/PUT payloads.
- Three raw `fetch()` sites migrated to `apiFetch` (delivery-docs upload, matched-candidates discovery, bridge-call). They previously bypassed the bearer header entirely and would have 401'd under the #22 middleware.
- Four hooks/components (`useApplications`, `useContacts`, `useJobFeed`, `NotificationBell`) also moved to `apiFetch` for the same reason.
- Incidental fix: the "available to chat" toggle was POSTing to a nonexistent `/api/switch/profile/update` — rewired to the real `PUT /api/switch/profile` with `{ isAvailable }`.

## Notes / gotchas that bit me mid-session

1. **`@router.options(...)` decorators also have paths.** When you change a handler's route, update the matching OPTIONS decorator too or OpenAPI will show both the old and new path. There's a shared `options_handler` up top with many stacked decorators — edit that carefully.
2. **Some handlers name the Pydantic body `request`**, which collides with FastAPI's `Request`. When adding `request: Request` to read the token, rename the body param to `payload` and sweep `request.` → `payload.` within the handler body (scope the sweep to the handler line range; don't global-replace — other handlers use `request` legitimately).
3. **Don't delete the deprecated fields on Pydantic models.** Mark `Optional[str] = None` with a `# DEPRECATED: candidate for deletion` comment so frontend clients with old payloads still validate during the rollout.
4. Import `caller_phone` from `utils.hearus_auth` once at the top of each router file.
5. Bodies that were `request: SomeModel` with *internal references* (e.g. `request.user_id`, `request.job_id`) need every `.user_id` reference swapped to `caller_phone(http_request)` and every other `.field` kept as `payload.field`.

## Suggested execution order (next session)

Backend + frontend code complete. PRs open and out of draft: [Vance#22](https://github.com/Vance-2025/Vance/pull/22) → [Vance#23](https://github.com/Vance-2025/Vance/pull/23) on backend; [Switch-app#6](https://github.com/yednap868/Switch-app/pull/6) → [Switch-app#7](https://github.com/yednap868/Switch-app/pull/7) on frontend. Remaining work:

1. **End-to-end QA with a real HearUs token.** 401-without-bearer and 404-on-old-URL are both verified; the 200-with-valid-bearer golden paths (worker: profile → swipe → apply → applications → notifications; employer: `/hire` → post-job → inbox → shortlist) are not. Preview URL during the last session: https://switch-preview-owner-auth.netlify.app wired to a local backend via ngrok.
2. **Review overlapping PRs against main — none of the four are zero-overlap.** While we were working, main/prod gained new commits that touch the same files. Verify nothing broke:
   - **Vance#22** (backend middleware) — overlaps with `api/app.py` (prod commit `f4efed7` added a self-hosted joining reminder scheduler). `git merge-tree` shows no conflict markers, but re-read the final merged `app.py` to confirm middleware order + scheduler startup are both sane.
   - **Vance#23** (backend ownership) — overlaps with `api/switch_placement_routes.py` (prod commit `66cb7ae` added `GET /api/switch/worker-card/{phone}/{job_key}` for employer QR-scan verification; the CORS-cleanup commit in #23 deletes `@router.options` handlers in the same file). Auto-merges cleanly, but review the resulting file to ensure the new endpoint survived and still has the correct signature.
   - **Switch-app#6** (frontend apiFetch) — overlaps with ~14 files touched by the 13 new `main` commits (VideoKYC, WorkerIdCard, WorkerMapView, map-as-pins, PWA install CTA, etc.). Auto-merges cleanly but the new components call the backend via raw `fetch()`. Those calls will 401 once the backend middleware is deployed — see task below.
   - **Switch-app#7** (frontend ownership sweep) — overlaps on the same files as #6. Same review needed: confirm the ownership-scoping edits still apply cleanly after main's refactors landed on `SwitchApp.jsx` / `EmployerApp.jsx`.
3. **Allowlist / auth-wire the new endpoints that landed on main while we were working.** `/api/switch/worker-card/` was added to #22's middleware allowlist (employer QR scan — public by design). Still pending:
   - **New backend endpoints:** audit commits `66cb7ae` (worker-card) and `f4efed7` (joining reminder scheduler) for anything else that needs allowlist or auth treatment.
   - **New frontend `fetch()` sites on main:** `VideoKYC.jsx`, `WorkerIdCard.jsx`, `WorkerCardVerify.jsx`, `WorkerMapView.jsx`, `PwaInstallScreenEmployer.jsx`, `JobDetailSheet.jsx`, `JobsTab.jsx`, and the updated `SwitchApp.jsx`/`EmployerApp.jsx` regions each introduced or moved API calls that don't go through `apiFetch`. They need to be migrated (bearer header + strip URL/body user_id) in the same pattern as Switch-app#7 — ideally in a new PR stacked on top of #7 after it merges.
4. **Merge in order, one stack at a time.** Backend: #22 → #23 (bases auto-rebase). Frontend: #6 → #7.
5. **After merge: delete the DEPRECATED-marked Optional fields** on Pydantic bodies. They were kept as a deploy-skew cushion; once both sides are on prod, they add nothing and can be dropped in a small follow-up commit.

## Rollback

Revert the branch; no schema migrations, no data writes that rely on the new route shapes. Old frontends still work against old backend (the WIP branch has not been deployed anywhere).

## Open questions to confirm with Pankaj next session

- **Do we break the old URLs outright** (`/profile/{user_id}` returning 404) or keep them as deprecated aliases that also read from the token? The 2026-04-19 session chose "break outright" and the 2026-04-20 session shipped that. Not yet explicitly reconfirmed — if you'd rather alias, it's a small follow-up commit per renamed route.
- **Some routes accept a path param that is *not* a user_id** (e.g. `/applications/{application_id}/no-show`, `/jobs/{job_id}/select-candidate`, `/employer/batch-action`, `/interview/{schedule,confirm,outcome}`, `/employer/hiring-request/{req_id}(+close)`). The token authenticates the caller but the handler doesn't restrict which row they can touch. Server-side DB-lookup + ownership check is a separate policy decision — deliberately deferred out of this PR, worth a dedicated follow-up.
