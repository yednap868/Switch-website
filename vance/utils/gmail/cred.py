"""
Functions to load credentials from a file.
"""

import os

import pendulum
import requests

from .settings import Collections
from utils.firebase_init import fs

assistants = fs.collection(Collections.EMAILS.value)


TZ_NAME = "Asia/Kolkata"

# Load Gmail credentials with proper error handling
try:
    CLIENT_ID: str = os.environ["GMAIL_CLIENT_ID"]
    CLIENT_SECRET: str = os.environ["GMAIL_CLIENT_SECRET"]
except KeyError as e:
    print(f"❌ [GMAIL] Missing required environment variable: {e}")
    print("❌ [GMAIL] Please ensure GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET are set")
    # Set default values to prevent crashes
    CLIENT_ID = ""
    CLIENT_SECRET = ""


def get_access_token(self_email: str) -> str:
    """
    Checks if the access token has expired and then returns it.
    If it is expired, calls refresh_access_token().
    """
    try:
        now = pendulum.now(TZ_NAME)

        data = load_tokens(self_email)

        if data is None:
            print(f"❌ [GMAIL] Token data is None for {self_email}")
            raise ValueError("Token data cannot be None.")

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        if not access_token:
            print(f"❌ [GMAIL] Access token is None for {self_email}")
            raise ValueError("access_token is None")

        if not refresh_token:
            print(f"❌ [GMAIL] Refresh token is None for {self_email}")
            raise ValueError("refresh_token is None")
    except Exception as e:
        print(f"❌ [GMAIL] Error in get_access_token for {self_email}: {e}")
        raise

    last_token_refresh_ts = pendulum.parse(data["last_token_refresh_ts"].isoformat())

    should_refresh = (now - last_token_refresh_ts).total_minutes() >= 59

    if should_refresh:
        access_token = refresh_access_token(self_email, access_token, refresh_token)
        update_access_token(self_email, access_token)

    return access_token


def refresh_access_token(self_email: str, access_token: str, refresh_token: str) -> str:
    """
    Refreshes a stale access token using a valid refresh token.
    """
    REFRESH_URL = "https://oauth2.googleapis.com/token"
    HEADERS = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    res = requests.post(
        data=data,
        timeout=10,
        url=REFRESH_URL,
        headers=HEADERS,
    )

    # unsuccessful request, raising
    if res.status_code != 200:
        print(res.json())
        raise ValueError("Refresh request returned a non 200 status.")

    access_token = res.json()["access_token"]

    update_access_token(self_email, access_token)

    return access_token


# TODO needs to take self_email as an argument and retrieve the token for that specific email
def load_tokens(self_email: str):
    """
    Loads tokens from a file.
    """
    print(f"load_tokens({self_email})")
    doc = assistants.document(self_email).get()

    return doc.to_dict()


# TODO needs to take self_email as an argument and retrieve the token for that specific email
def update_access_token(self_email: str, access_token: str):
    """
    Write tokens to firestore.
    """
    print(f"update_access_token({self_email}, {access_token})")
    assistants.document(self_email).update(
        {
            "access_token": access_token,
            "last_token_refresh_ts": pendulum.now(),
        }
    )


def update_history_id(self_email: str, history_id: str):
    """
    GMailClient._update_history_id()
    """
    print(f"update_history_id({self_email}, {history_id})")

    assistants.document(self_email).update({"history_id": history_id})


def load_last_history_id(self_email: str):
    """
    load_last_history_id()
    """
    print(f"load_last_history_id({self_email})")

    data = assistants.document(self_email).get().to_dict()

    if not data:
        raise ValueError(f"Assistant with email {self_email} does not exist.")

    if data.get("history_id"):
        return data["history_id"]

    return None
