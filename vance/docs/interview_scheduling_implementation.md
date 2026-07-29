# Interview Scheduling Implementation Notes

## Overview

This document describes the implementation of the post-call interview scheduling feature in Vance. After a voice call ends with a user who has hiring intent, the system automatically presents matching candidates and allows the user to schedule interviews directly via WhatsApp.

---

## Table of Contents

1. [User Flow](#user-flow)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Detailed Implementation](#detailed-implementation)
5. [Candidate Notifications](#candidate-notifications)
6. [Google OAuth Setup](#google-oauth-setup)
7. [Environment Variables](#environment-variables)
8. [Dependencies](#dependencies)
9. [Firestore Collections](#firestore-collections)
10. [Message Flow Examples](#message-flow-examples)
11. [Error Handling](#error-handling)
12. [Testing](#testing)

---

## User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POST-CALL INTERVIEW SCHEDULING                       │
└─────────────────────────────────────────────────────────────────────────────┘

1. CALL ENDS
   └── User completes voice call with Vance
   └── ElevenLabs saves call data + extraction to Firestore
   └── User sends follow-up message on WhatsApp

2. INTENT DETECTION
   └── System checks extraction_data.intent
   └── If intent == "hiring_need" or "recruiter_need":
       └── Trigger hiring flow
   └── Else:
       └── Normal ready_for_connection flow

3. CANDIDATE PRESENTATION
   └── Search Qdrant for matching profiles (top 3)
   └── Format candidates with name, headline, summary, match reason
   └── Store candidates in user session (state_manager)
   └── Set state → "post_call_candidates_presented"
   └── Send WhatsApp message with candidate list
   └── 🔔 Notify each candidate via WhatsApp that their profile was shown

4. CANDIDATE SELECTION
   └── User responds with selection (e.g., "1 and 3", "all", "the engineer")
   └── Claude parses selection → list of selected candidates
   └── Store selected candidates in session
   └── Check if all candidates have emails
   └── Set state → "awaiting_interview_time"
   └── Ask for preferred interview time

5. TIME INPUT & SCHEDULING
   └── User provides time (e.g., "tomorrow 2pm", "Monday morning")
   └── Claude parses natural language → datetime
   └── Validate time is in future
   └── Create Google Calendar events with Google Meet
   └── 🔔 Notify each candidate via WhatsApp about their scheduled interview
   └── Send confirmation with Meet links to hiring user
   └── Set state → "ready_for_connection"
   └── Clear candidate data from session
```

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WhatsApp Message                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         router_v2.py (webhook)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      conversation_service.py                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ process_message()                                                    │    │
│  │   └── handlers["post_call_candidates_presented"]                     │    │
│  │   └── handlers["awaiting_interview_time"]                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ _handle_post_call_conversation()                                     │    │
│  │   └── _check_and_present_hiring_candidates()                         │    │
│  │       └── _present_hiring_candidates()                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ _handle_candidate_selection()                                        │    │
│  │   └── _parse_candidate_selection_with_claude()                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ _handle_interview_time_input()                                       │    │
│  │   └── claude_profile_service.parse_time_expression()                 │    │
│  │   └── interview_scheduling_service.schedule_multiple_interviews()    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   interview_scheduling_service.py                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ InterviewSchedulingService                                           │    │
│  │   └── schedule_interview()                                           │    │
│  │   └── schedule_multiple_interviews()                                 │    │
│  │   └── format_candidate_presentation()                                │    │
│  │   └── format_time_request()                                          │    │
│  │   └── format_confirmation()                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Notification Functions                                               │    │
│  │   └── notify_candidate_profile_shown() ──────► WhatsApp + History   │    │
│  │   └── notify_candidate_interview_scheduled() ► WhatsApp + History   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      utils/calendar/google_calendar.py                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ VanceCalendarClient                                                  │    │
│  │   └── _load_credentials() ─── Firestore ───┐                         │    │
│  │   └── get_access_token()                   │                         │    │
│  │   └── _refresh_access_token() ─────────────┤                         │    │
│  │   └── create_interview_event() ────────────┼──► Google Calendar API  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Google Calendar API                                 │
│                    (Creates event + Google Meet link)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
Vance/
├── api/
│   ├── app.py                          # Modified: Added calendar_router
│   └── calendar_routes.py              # NEW: OAuth endpoints
├── config/
│   └── conversation_flow.json          # Modified: Added new states
├── services/
│   ├── conversation_service.py         # Modified: Added interview handlers
│   └── interview_scheduling_service.py # NEW: Scheduling orchestration
├── utils/
│   └── calendar/
│       ├── __init__.py                 # NEW: Module init
│       └── google_calendar.py          # NEW: Calendar client
└── docs/
    └── interview_scheduling_implementation.md  # This file
```

---

## Detailed Implementation

### 1. Calendar Client (`utils/calendar/google_calendar.py`)

The `VanceCalendarClient` class handles all Google Calendar API interactions.

#### Key Features:

- **Credential Loading**: Fetches OAuth tokens from Firestore on initialization
- **Token Refresh**: Automatically refreshes access tokens every 30 minutes
- **Event Creation**: Creates calendar events with Google Meet links

#### Token Refresh Flow:

```python
def get_access_token(self) -> str:
    """Called before every API request."""
    now = pendulum.now(self.tz)
    delta = now - self.last_token_refresh_ts

    if delta.total_minutes() >= 30:
        self._refresh_access_token()  # Refresh and update Firestore

    return self.access_token
```

#### Event Creation:

```python
def create_interview_event(
    self,
    hiring_user_email: str,
    candidate_email: str,
    candidate_name: str,
    start_time: datetime,
    duration_minutes: int = 30,
    description: str = "",
) -> dict:
    """Creates event with:
    - Organizer: Vance's account
    - Attendees: Hiring user + Candidate
    - Google Meet link auto-generated
    - 10-minute reminder
    """
```

### 2. OAuth Routes (`api/calendar_routes.py`)

Provides endpoints for one-time OAuth setup.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/calendar/oauth/start` | GET | Redirect to Google consent screen |
| `/api/calendar/oauth/callback` | GET | Handle OAuth callback, save tokens |
| `/api/calendar/oauth/status` | GET | Check if calendar is configured |
| `/api/calendar/oauth/disconnect` | DELETE | Remove credentials (for re-auth) |

### 3. Interview Scheduling Service (`services/interview_scheduling_service.py`)

Orchestrates the scheduling flow and provides message formatting.

#### Methods:

| Method | Purpose |
|--------|---------|
| `schedule_interview()` | Schedule single interview |
| `schedule_multiple_interviews()` | Schedule back-to-back interviews with gaps |
| `format_candidate_presentation()` | Format candidates for WhatsApp |
| `format_time_request()` | Format time input request |
| `format_confirmation()` | Format scheduling confirmation |

### 4. Conversation Handlers (`services/conversation_service.py`)

New handlers added to the existing conversation service.

#### Handler Registration:

```python
handlers = {
    # ... existing handlers ...
    # Interview scheduling states
    "post_call_candidates_presented": self._handle_candidate_selection,
    "awaiting_interview_time": self._handle_interview_time_input,
}
```

#### Handler Methods:

| Method | State | Purpose |
|--------|-------|---------|
| `_present_hiring_candidates()` | call_agreed → post_call_candidates_presented | Search and present candidates |
| `_handle_candidate_selection()` | post_call_candidates_presented | Parse user's selection |
| `_handle_interview_time_input()` | awaiting_interview_time | Parse time, schedule interviews |
| `_check_and_present_hiring_candidates()` | Helper | Check intent and trigger flow |
| `_parse_candidate_selection_with_claude()` | Helper | Use Claude to parse selection |

---

## Candidate Notifications

Candidates receive WhatsApp notifications at key points in the interview scheduling flow. These notifications keep candidates informed and maintain conversation context for future interactions.

### Notification Types

#### 1. Profile Shown Notification

**Triggered**: When a candidate's profile is presented to a hiring user (in `_present_hiring_candidates()`)

**Message**:
```
Hey! Just wanted to let you know - your profile was just shown to
*{job_provider_name}* who's looking for candidates like you.
I'll keep you posted if they want to connect!
```

**Implementation**: `notify_candidate_profile_shown(candidate_wa_id, job_provider_name)`

#### 2. Interview Scheduled Notification

**Triggered**: When an interview is successfully scheduled (in `_handle_interview_time_input()`)

**Message**:
```
Great news! *{hiring_user_name}* wants to interview you!

Interview scheduled for *{time}*
Google Meet: {meet_link}

A calendar invite has been sent to your email. Good luck!
```

**Implementation**: `notify_candidate_interview_scheduled(candidate_wa_id, hiring_user_name, interview_time, meet_link)`

### Conversation History Logging

All notification messages are logged to the candidate's conversation history using `conversation_history.save_message()`. This ensures:

1. **Context Continuity**: When a candidate replies to a notification, Vance has full context of what was previously communicated
2. **7-Day Retention**: Messages are retained for 7 days per the standard conversation history policy
3. **Metadata Tracking**: Each notification includes metadata for tracking:
   - `notification_type`: "profile_shown" or "interview_scheduled"
   - Additional context like job provider name, interview time, meet link

### Notification Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CANDIDATE NOTIFICATION FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

Profile Shown:
┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐
│ Hiring User  │───►│ _present_hiring_  │───►│ notify_candidate │
│ sees matches │    │ candidates()      │    │ _profile_shown() │
└──────────────┘    └───────────────────┘    └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │ WhatsApp Message │
                                             │ + History Log    │
                                             └──────────────────┘

Interview Scheduled:
┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐
│ Hiring User  │───►│ _handle_interview │───►│ notify_candidate │
│ provides time│    │ _time_input()     │    │ _interview_      │
└──────────────┘    └───────────────────┘    │ scheduled()      │
                                             └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │ WhatsApp Message │
                                             │ + History Log    │
                                             └──────────────────┘
```

### Important Notes

1. **Non-blocking**: Notifications are wrapped in try/catch to prevent failures from affecting the main flow
2. **Valid WhatsApp ID Required**: Notifications are only sent if the candidate has a valid WhatsApp ID (numeric phone number)
3. **Graceful Degradation**: If notification fails, an error is logged but the main flow continues

---

## Google OAuth Setup

### Step 1: Create OAuth Credentials in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Select **Web application**
6. Configure:
   - **Name**: `Vance Calendar Client`
   - **Authorized redirect URIs**: Add your callback URL:
     - Development: `http://localhost:8000/api/calendar/oauth/callback`
     - Production: `https://your-domain.com/api/calendar/oauth/callback`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### Step 2: Enable Google Calendar API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google Calendar API"
3. Click **Enable**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** (or Internal if using Google Workspace)
3. Fill in required fields:
   - App name: `Vance`
   - User support email: Your email
   - Developer contact: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `openid`
   - `profile`
   - `email`
5. Add test users (if in testing mode):
   - Add the email address that Vance will use for scheduling

### Step 4: Set Environment Variables

Add to your environment (see [Environment Variables](#environment-variables) section).

### Step 5: Run OAuth Flow

1. Start your application
2. Visit: `https://your-domain.com/api/calendar/oauth/start`
3. Log in with Vance's Google account
4. Grant calendar permissions
5. You'll be redirected to callback with success message
6. Credentials are now saved in Firestore

### Step 6: Verify Setup

Check status at: `https://your-domain.com/api/calendar/oauth/status`

Expected response:
```json
{
  "configured": true,
  "email": "vance@yourdomain.com",
  "name": "Vance",
  "activated": true
}
```

---

## Environment Variables

Add these to your `env_vars.sh` or environment configuration:

```bash
# Google OAuth for Vance Calendar
# These are SEPARATE from any other Google credentials in the project

# OAuth Client ID from Google Cloud Console
export VANCE_CALENDAR_CLIENT_ID="your-client-id.apps.googleusercontent.com"

# OAuth Client Secret from Google Cloud Console
export VANCE_CALENDAR_CLIENT_SECRET="your-client-secret"

# OAuth Redirect URI (must match exactly what's in Google Cloud Console)
# Development:
export VANCE_CALENDAR_REDIRECT_URI="http://localhost:8000/api/calendar/oauth/callback"
# Production:
# export VANCE_CALENDAR_REDIRECT_URI="https://your-domain.com/api/calendar/oauth/callback"
```

### Variable Descriptions:

| Variable | Description | Example |
|----------|-------------|---------|
| `VANCE_CALENDAR_CLIENT_ID` | OAuth 2.0 Client ID from Google Cloud Console | `123456789-abc.apps.googleusercontent.com` |
| `VANCE_CALENDAR_CLIENT_SECRET` | OAuth 2.0 Client Secret | `GOCSPX-abcdef123456` |
| `VANCE_CALENDAR_REDIRECT_URI` | Callback URL for OAuth flow (must match Console config) | `https://api.vance.so/api/calendar/oauth/callback` |

### Important Notes:

1. **Redirect URI Must Match Exactly**: The `VANCE_CALENDAR_REDIRECT_URI` must exactly match one of the authorized redirect URIs in Google Cloud Console, including protocol (http/https) and any trailing slashes.

2. **Separate from Firebase**: These credentials are for OAuth user authentication, separate from the Firebase service account credentials (`GOOGLE_APPLICATION_CREDENTIALS`).

3. **Keep Secrets Secure**: Never commit these values to version control. Use environment variables or a secrets manager.

---

## Dependencies

The interview scheduling feature requires the following Python packages (managed via `uv` in `pyproject.toml`):

| Package | Version | Purpose |
|---------|---------|---------|
| `pendulum` | >=3.1.0 | Time parsing and manipulation |
| `requests` | >=2.32.5 | HTTP requests to Google Calendar API |
| `fastapi` | >=0.121.3 | OAuth route endpoints |
| `firebase-admin` | >=7.1.0 | Firestore credential storage |
| `google-auth` | >=2.43.0 | OAuth token verification in callback |

### Installation

All dependencies are already included in the project's `pyproject.toml`. To install:

```bash
uv sync
```

Or to add a new dependency:

```bash
uv add <package-name>
```

---

## Firestore Collections

### Collection: `vance_calendar_credentials`

Stores OAuth credentials for Vance's calendar account.

**Document ID**: Vance's email address (e.g., `vance@yourdomain.com`)

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Vance's Google email |
| `name` | string | Display name from Google |
| `access_token` | string | Current OAuth access token |
| `refresh_token` | string | OAuth refresh token (long-lived) |
| `scopes` | array | Granted OAuth scopes |
| `last_token_refresh_ts` | timestamp | When access token was last refreshed |
| `activated` | boolean | Whether account is active |
| `tz_name` | string | Timezone (default: "Asia/Kolkata") |

**Example Document**:

```json
{
  "email": "vance@yourdomain.com",
  "name": "Vance",
  "access_token": "ya29.a0AfH6SMB...",
  "refresh_token": "1//0gYj3...",
  "scopes": [
    "https://www.googleapis.com/auth/calendar",
    "openid",
    "profile",
    "email"
  ],
  "last_token_refresh_ts": "2024-01-15T10:30:00Z",
  "activated": true,
  "tz_name": "Asia/Kolkata"
}
```

### Session Data (in `users` collection via state_manager)

During the interview scheduling flow, candidate data is stored in the user's session:

| Field | Type | Purpose |
|-------|------|---------|
| `suggested_candidates` | array | Candidates presented to user |
| `selected_candidates` | array | Candidates user selected for interviews |
| `candidates_missing_email` | array | Names of candidates without emails |

---

## Message Flow Examples

### Example 1: Complete Happy Path

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ VANCE (after call with hiring manager):                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ I'd love to introduce you to some candidates that fit your hiring needs:    │
│                                                                              │
│ *1. Sarah Chen*                                                              │
│ _Senior Software Engineer at Google_                                         │
│ 8 years experience in distributed systems, ML infrastructure                │
│ Why they're a match: Strong backend experience, looking for startup roles   │
│                                                                              │
│ *2. Mike Johnson*                                                            │
│ _Staff Engineer at Meta_                                                     │
│ Technical lead with team management experience                               │
│ Why they're a match: Wants to join early-stage company as tech lead         │
│                                                                              │
│ *3. Priya Sharma*                                                            │
│ _Engineering Manager at Stripe_                                              │
│ Built and scaled payments infrastructure                                     │
│ Why they're a match: Looking for founding engineer roles                     │
│                                                                              │
│ Let me know which candidates you'd like to interview and which aren't       │
│ relevant. I'll schedule the interviews for you.                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ USER:                                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ I'd like to meet Sarah and Mike                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ VANCE:                                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Great choices! I'll set up interviews with Sarah Chen and Mike Johnson.     │
│                                                                              │
│ When would you prefer to schedule these interviews? You can say something   │
│ like "tomorrow at 2pm" or "next Monday morning".                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ USER:                                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tomorrow at 3pm works                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ VANCE:                                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Done! I've scheduled your interviews:                                        │
│                                                                              │
│ *Sarah Chen* - Tuesday, January 16 at 03:00 PM                               │
│ Google Meet: https://meet.google.com/abc-defg-hij                            │
│                                                                              │
│ *Mike Johnson* - Tuesday, January 16 at 03:45 PM                             │
│ Google Meet: https://meet.google.com/klm-nopq-rst                            │
│                                                                              │
│ Calendar invites have been sent to everyone. Good luck with the interviews! │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Example 2: User Selects All Candidates

```
USER: "all of them look great"
VANCE: "Great choices! I'll set up interviews with Sarah Chen, Mike Johnson,
        and Priya Sharma. When would you prefer to schedule these interviews?"
```

### Example 3: Unclear Selection

```
USER: "maybe the second one"
VANCE: "I wasn't sure which candidates you'd like to interview. Could you tell
        me which ones from: Sarah Chen, Mike Johnson, Priya Sharma? Or say
        'all' if you'd like to meet all of them."
```

### Example 4: No Interest

```
USER: "none of these are relevant"
VANCE: "No problem, John. Let me know when you'd like to see more candidates
        or if there's something else I can help with."
```

### Example 5: Missing Email

```
VANCE: "Great choices! I'll set up interviews with them.

        Note: I don't have email addresses for Sarah Chen. Could you provide
        their emails? Or I can proceed with the others.

        When would you prefer to schedule the interviews?"

USER: "sarah@google.com and tomorrow 2pm"
VANCE: [Parses email and time, schedules interview]
```

---

## Error Handling

### Calendar Not Configured

If OAuth hasn't been completed:

```python
if not interview_scheduling_service.is_available():
    # Falls back to normal ready_for_connection flow
    return self._handle_ready_for_connection(user_id, "", None)
```

### No Matching Candidates

```python
if not matches:
    return f"Hi {name}! I looked for candidates matching your needs but
             didn't find great matches yet. Let me know more about what
             you're looking for and I'll keep searching."
```

### Token Refresh Failure

```python
if response.status_code != 200:
    raise ValueError(f"Failed to refresh access token: {response.text}")
# Admin should re-run OAuth flow at /api/calendar/oauth/start
```

### Calendar API Error

```python
except Exception as e:
    return f"Sorry {name}, I had trouble scheduling the interviews.
             Error: {str(e)}
             Would you like me to try again, or would you prefer a different time?"
```

### Time Parsing Failure

```python
if ptype in ("none", "ambiguous"):
    return f"I couldn't understand that time, {name}. Could you try again?
             For example: 'tomorrow at 2pm', 'next Monday at 10am', or 'in 2 hours'."
```

---

## Testing

### Manual Testing Checklist

1. **OAuth Flow**
   - [ ] Visit `/api/calendar/oauth/start`
   - [ ] Complete Google consent
   - [ ] Verify redirect to callback with success
   - [ ] Check `/api/calendar/oauth/status` returns configured: true
   - [ ] Verify credentials in Firestore

2. **Candidate Presentation**
   - [ ] Complete a call with hiring intent
   - [ ] Send follow-up message
   - [ ] Verify candidates are presented
   - [ ] Check state is `post_call_candidates_presented`

3. **Candidate Selection**
   - [ ] Select single candidate ("the first one")
   - [ ] Select multiple ("1 and 3")
   - [ ] Select all ("all of them")
   - [ ] Reject all ("none")
   - [ ] Verify state changes to `awaiting_interview_time`

4. **Time Parsing**
   - [ ] "tomorrow at 2pm"
   - [ ] "next Monday morning"
   - [ ] "in 2 hours"
   - [ ] Invalid time (past)
   - [ ] Ambiguous time

5. **Scheduling**
   - [ ] Verify calendar event created
   - [ ] Verify Google Meet link generated
   - [ ] Verify attendees added
   - [ ] Verify confirmation message sent
   - [ ] Check state returns to `ready_for_connection`

6. **Candidate Notifications**
   - [ ] Verify "profile shown" notification sent to candidates when presented
   - [ ] Verify notification logged to candidate's conversation history
   - [ ] Verify "interview scheduled" notification sent after scheduling
   - [ ] Verify interview notification includes Meet link and time
   - [ ] Verify candidate can reply to notification with context maintained

### API Testing

```bash
# Check OAuth status
curl https://your-domain.com/api/calendar/oauth/status

# Expected: {"configured": true, "email": "...", ...}
```

---

## Troubleshooting

### "Calendar not configured" Error

**Cause**: OAuth flow hasn't been completed.

**Solution**: Visit `/api/calendar/oauth/start` and complete authorization.

### "No refresh token received" Error

**Cause**: Google didn't return a refresh token (happens if already authorized).

**Solution**:
1. Go to https://myaccount.google.com/permissions
2. Remove access for the Vance app
3. Re-run OAuth flow with `prompt=consent`

### Token Refresh Failing

**Cause**: Refresh token expired or revoked.

**Solution**:
1. Visit `/api/calendar/oauth/disconnect`
2. Re-run OAuth flow at `/api/calendar/oauth/start`

### Calendar Events Not Showing Meet Link

**Cause**: `conferenceDataVersion` not set to "1" in API call.

**Solution**: Ensure the API call includes:
```python
params={"sendUpdates": "all", "conferenceDataVersion": "1"}
```

### Wrong Timezone in Events

**Cause**: Timezone not set correctly.

**Solution**: Check `tz_name` in Firestore credentials document. Default is "Asia/Kolkata".

---

## Future Enhancements

1. **Free/Busy Checking**: Check calendar availability before suggesting times
2. **Rescheduling**: Allow users to reschedule interviews
3. **Cancellation**: Allow users to cancel interviews
4. **Multi-timezone Support**: Handle users in different timezones
5. **Interview Reminders**: Send WhatsApp reminders before interviews
6. **Feedback Collection**: Ask for feedback after interviews
