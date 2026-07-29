"""
OAuth routes for Google Calendar integration.
Handles one-time setup flow to authorize Vance's calendar account.
"""

import os
from urllib.parse import quote

import pendulum
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as id_token_parser

from utils.db import fs as db

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# Environment variables
VANCE_CALENDAR_CLIENT_ID = os.getenv("VANCE_CALENDAR_CLIENT_ID")
VANCE_CALENDAR_CLIENT_SECRET = os.getenv("VANCE_CALENDAR_CLIENT_SECRET")
VANCE_CALENDAR_REDIRECT_URI = os.getenv("VANCE_CALENDAR_REDIRECT_URI")

# Firestore collection
CREDENTIALS_COLLECTION = "vance_calendar_credentials"

# OAuth scopes
SCOPES = "https://www.googleapis.com/auth/calendar openid profile email"


@router.get("/oauth/start")
async def start_oauth():
    """
    Start the OAuth flow by redirecting to Google's consent screen.
    Visit this endpoint once to authorize Vance's Google account.
    """
    if not VANCE_CALENDAR_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="VANCE_CALENDAR_CLIENT_ID not configured",
        )

    if not VANCE_CALENDAR_REDIRECT_URI:
        raise HTTPException(
            status_code=500,
            detail="VANCE_CALENDAR_REDIRECT_URI not configured",
        )

    # Build OAuth URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/auth?"
        "response_type=code&"
        "access_type=offline&"
        f"client_id={VANCE_CALENDAR_CLIENT_ID}&"
        f"redirect_uri={quote(VANCE_CALENDAR_REDIRECT_URI, safe='')}&"
        f"scope={quote(SCOPES, safe='')}&"
        "prompt=consent"
    )

    return RedirectResponse(auth_url)


@router.get("/oauth/callback")
async def oauth_callback(code: str):
    """
    Handle OAuth callback from Google.
    Exchanges auth code for tokens and saves to Firestore.
    """
    if not all(
        [
            VANCE_CALENDAR_CLIENT_ID,
            VANCE_CALENDAR_CLIENT_SECRET,
            VANCE_CALENDAR_REDIRECT_URI,
        ]
    ):
        raise HTTPException(
            status_code=500,
            detail="OAuth environment variables not fully configured",
        )

    # Exchange auth code for tokens
    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": VANCE_CALENDAR_CLIENT_ID,
                "client_secret": VANCE_CALENDAR_CLIENT_SECRET,
                "redirect_uri": VANCE_CALENDAR_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        if token_response.status_code != 200:
            print(f"Token exchange failed: {token_response.text}")
            raise HTTPException(
                status_code=401,
                detail=f"Failed to exchange auth code: {token_response.text}",
            )

        tokens = token_response.json()

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Token request failed: {str(e)}")

    # Verify we got a refresh token
    if not tokens.get("refresh_token"):
        raise HTTPException(
            status_code=400,
            detail="No refresh token received. Revoke app access and try again with prompt=consent.",
        )

    # Parse id_token to get user info
    try:
        id_info = id_token_parser.verify_oauth2_token(
            tokens["id_token"],
            google_requests.Request(),
            VANCE_CALENDAR_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Failed to verify id_token: {str(e)}"
        )

    # Build credential data
    credential_data = {
        "email": id_info["email"],
        "name": id_info.get("name", ""),
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "scopes": tokens.get("scope", "").split(" "),
        "last_token_refresh_ts": pendulum.now(),
        "activated": True,
        "tz_name": "Asia/Kolkata",
    }

    # Save to Firestore
    try:
        db.collection(CREDENTIALS_COLLECTION).document(id_info["email"]).set(
            credential_data, merge=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save credentials: {str(e)}"
        )

    return {
        "status": "success",
        "message": f"Calendar connected for {id_info['email']}",
        "email": id_info["email"],
    }


@router.get("/oauth/status")
async def oauth_status():
    """
    Check if calendar is configured and return status.
    """
    try:
        docs = list(db.collection(CREDENTIALS_COLLECTION).limit(1).stream())

        if docs:
            data = docs[0].to_dict()
            return {
                "configured": True,
                "email": data.get("email"),
                "name": data.get("name"),
                "activated": data.get("activated", False),
            }

        return {"configured": False}

    except Exception as e:
        return {"configured": False, "error": str(e)}


@router.delete("/oauth/disconnect")
async def disconnect_calendar():
    """
    Remove calendar credentials (for re-authentication).
    """
    try:
        docs = list(db.collection(CREDENTIALS_COLLECTION).stream())

        for doc in docs:
            doc.reference.delete()

        return {"status": "success", "message": "Calendar disconnected"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")
