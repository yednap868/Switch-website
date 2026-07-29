"""
Simple Google Calendar client for Vance interview scheduling.
Uses OAuth user credentials stored in Firestore.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import pendulum
import requests

from utils.db import fs as db

# Environment variables for Vance Calendar OAuth
VANCE_CALENDAR_CLIENT_ID = os.getenv("VANCE_CALENDAR_CLIENT_ID")
VANCE_CALENDAR_CLIENT_SECRET = os.getenv("VANCE_CALENDAR_CLIENT_SECRET")

# Firestore collection for calendar credentials
CREDENTIALS_COLLECTION = "vance_calendar_credentials"

# Default timezone
DEFAULT_TZ = "Asia/Kolkata"


class VanceCalendarClient:
    """
    Minimal Google Calendar client for scheduling interviews.
    Loads OAuth credentials from Firestore and handles token refresh.
    """

    def __init__(self):
        """Initialize client and load credentials from Firestore."""
        self.email: str = ""
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.last_token_refresh_ts: pendulum.DateTime = None
        self.doc_ref = None
        self.tz: str = DEFAULT_TZ

        self._load_credentials()

    def _load_credentials(self):
        """Fetch Vance's calendar credentials from Firestore."""
        docs = list(db.collection(CREDENTIALS_COLLECTION).limit(1).stream())

        if not docs:
            raise ValueError(
                "Calendar not configured. Run OAuth setup at /api/calendar/oauth/start first."
            )

        doc = docs[0]
        data = doc.to_dict()

        self.email = data.get("email", "")
        self.access_token = data.get("access_token", "")
        self.refresh_token = data.get("refresh_token", "")
        self.tz = data.get("tz_name", DEFAULT_TZ)
        self.doc_ref = doc.reference

        # Parse timestamp
        last_refresh = data.get("last_token_refresh_ts")
        if last_refresh:
            if hasattr(last_refresh, "timestamp"):
                # Firestore timestamp
                self.last_token_refresh_ts = pendulum.from_timestamp(
                    last_refresh.timestamp()
                ).in_timezone(self.tz)
            else:
                # Already a pendulum datetime or similar
                self.last_token_refresh_ts = pendulum.instance(
                    last_refresh
                ).in_timezone(self.tz)
        else:
            # Force refresh on first use
            self.last_token_refresh_ts = pendulum.now(self.tz).subtract(hours=1)

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if needed.
        Tokens are refreshed if older than 30 minutes.
        """
        now = pendulum.now(self.tz)
        delta = now - self.last_token_refresh_ts

        if delta.total_minutes() >= 30:
            self._refresh_access_token()

        return self.access_token

    def _refresh_access_token(self):
        """Refresh the access token via Google OAuth and update Firestore."""
        if not VANCE_CALENDAR_CLIENT_ID or not VANCE_CALENDAR_CLIENT_SECRET:
            raise ValueError(
                "VANCE_CALENDAR_CLIENT_ID and VANCE_CALENDAR_CLIENT_SECRET must be set"
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": VANCE_CALENDAR_CLIENT_ID,
                "client_secret": VANCE_CALENDAR_CLIENT_SECRET,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        if response.status_code != 200:
            print(f"Token refresh failed: {response.text}")
            raise ValueError(
                f"Failed to refresh access token: {response.status_code} - {response.text}"
            )

        result = response.json()
        self.access_token = result.get("access_token", "")
        self.last_token_refresh_ts = pendulum.now(self.tz)

        # Update Firestore
        if self.doc_ref:
            self.doc_ref.update(
                {
                    "access_token": self.access_token,
                    "last_token_refresh_ts": self.last_token_refresh_ts,
                }
            )

    def create_interview_event(
        self,
        hiring_user_email: str,
        candidate_email: str,
        candidate_name: str,
        start_time: datetime,
        duration_minutes: int = 30,
        description: str = "",
    ) -> dict[str, Any]:
        """
        Create a calendar event with Google Meet link for an interview.

        Args:
            hiring_user_email: Email of the hiring manager
            candidate_email: Email of the candidate
            candidate_name: Name of the candidate (for event title)
            start_time: Interview start time
            duration_minutes: Duration of the interview (default 30 min)
            description: Optional event description

        Returns:
            Google Calendar API response with event details
        """
        token = self.get_access_token()

        # Calculate end time
        if isinstance(start_time, pendulum.DateTime):
            end_time = start_time.add(minutes=duration_minutes)
        else:
            end_time = start_time + timedelta(minutes=duration_minutes)

        # Format times
        start_str = start_time.isoformat().split(".")[0]
        end_str = end_time.isoformat().split(".")[0]

        event = {
            "summary": f"Interview: {candidate_name}",
            "description": description,
            "start": {
                "dateTime": start_str,
                "timeZone": self.tz,
            },
            "end": {
                "dateTime": end_str,
                "timeZone": self.tz,
            },
            "attendees": [
                {
                    "email": self.email,
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted",
                },
                {"email": hiring_user_email},
                {"email": candidate_email},
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": uuid.uuid4().hex,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        response = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params={
                "sendUpdates": "all",
                "conferenceDataVersion": "1",
            },
            json=event,
            timeout=15,
        )

        if response.status_code not in (200, 201):
            print(f"Calendar API error: {response.status_code} - {response.text}")
            raise ValueError(f"Failed to create calendar event: {response.text}")

        return response.json()

    def create_event_multiple_attendees(
        self,
        attendees: list[str],
        summary: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        enable_meet: bool = True,
    ) -> dict[str, Any]:
        """
        Create a calendar event with multiple attendees.

        Args:
            attendees: List of attendee email addresses
            summary: Event title
            description: Event description
            start_time: Event start time
            end_time: Event end time
            enable_meet: Whether to add Google Meet link

        Returns:
            Google Calendar API response with event details
        """
        token = self.get_access_token()

        # Format times
        start_str = start_time.isoformat().split(".")[0]
        end_str = end_time.isoformat().split(".")[0]

        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_str,
                "timeZone": self.tz,
            },
            "end": {
                "dateTime": end_str,
                "timeZone": self.tz,
            },
            "attendees": [
                {
                    "email": self.email,
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted",
                }
            ]
            + [{"email": email} for email in attendees],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        if enable_meet:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": uuid.uuid4().hex,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        params = {"sendUpdates": "all"}
        if enable_meet:
            params["conferenceDataVersion"] = "1"

        response = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params=params,
            json=event,
            timeout=15,
        )

        if response.status_code not in (200, 201):
            print(f"Calendar API error: {response.status_code} - {response.text}")
            raise ValueError(f"Failed to create calendar event: {response.text}")

        return response.json()


def is_calendar_configured() -> bool:
    """Check if calendar credentials are configured in Firestore."""
    try:
        docs = list(db.collection(CREDENTIALS_COLLECTION).limit(1).stream())
        return len(docs) > 0
    except Exception as e:
        print(f"Error checking calendar configuration: {e}")
        return False


def get_calendar_email() -> Optional[str]:
    """Get the configured calendar email address."""
    try:
        docs = list(db.collection(CREDENTIALS_COLLECTION).limit(1).stream())
        if docs:
            return docs[0].to_dict().get("email")
        return None
    except Exception as e:
        print(f"Error getting calendar email: {e}")
        return None
