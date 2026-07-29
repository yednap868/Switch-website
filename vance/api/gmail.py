"""
Endpoints to handle authentication and authorization redirects.
"""

import os
import traceback

import fastapi
import pendulum
import requests
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import RedirectResponse
from utils.firebase_init import fs as _gmail_fs
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as id_token_parser

from utils.email_logger import log_email_threads
from utils.gmail import client
from utils.gmail.client import GMailClient
from utils.gmail.settings import Collections
from utils.gmail.util import decode_base64url_to_json
from utils.process_email_threads import process_email_threads

_router = APIRouter(tags=["email"])


CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
DOMAIN = os.environ["DOMAIN"]


AUTH_URI = (
    "https://accounts.google.com/o/oauth2/auth?response_type=code&access_type=offline&"
    f"client_id={CLIENT_ID}&"
    f"redirect_uri={DOMAIN}/emailapi/auth-callback&"
    "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar%20"
    "https%3A//mail.google.com/"
    "%20openid%20profile%20email&prompt=consent"
)


def save_account_data(data: dict):
    """
    Save account auth credentials to firestore.
    """
    _gmail_fs.collection(Collections.EMAILS.value).document(data["email"]).set(
        data, merge=True
    )


def exchange_auth_code(auth_code: str, endpoint="/auth"):
    """
    Exchanges the auth code for access and refresh tokens.
    """
    auth_url = "https://oauth2.googleapis.com/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "code": auth_code,
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": DOMAIN + endpoint,
    }

    try:
        res = requests.post(url=auth_url, headers=headers, data=data, timeout=10)

        # return tokens or false depending on the status code of above response
        if res.status_code == 200:
            response_data = res.json()
            return {
                "access_token": response_data.get("access_token", None),
                "refresh_token": response_data.get("refresh_token", None),
                "id_token": response_data.get("id_token", None),
                "scopes": response_data.get("scope", "").split(" "),
            }
        else:
            raise HTTPException(status_code=401)

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=401)


@_router.get("/emailapi/auth-callback", status_code=200)
async def auth(code: str, request: Request):
    """
    Route for authentication.
    """
    try:
        result = exchange_auth_code(auth_code=code, endpoint=request.url.path)

        scopes = result["scopes"]

        id_token = result["id_token"]
        id_info = id_token_parser.verify_oauth2_token(
            id_token,
            GoogleAuthRequest(),
            CLIENT_ID,
        )

        access_token = result["access_token"]
        refresh_token = result["refresh_token"]

        data = {
            "id": id_info["sub"],
            "email": id_info["email"],
            "name": id_info["name"],
            "scopes": scopes,
            "domain": id_info["email"].split("@")[1],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "last_token_refresh_ts": pendulum.now(),
            "activated": True,
            "show_branding": True,
        }

        save_account_data(data)

        gmail_client = GMailClient(id_info["email"])
        try:
            watch_response = gmail_client.create_watch_request()
            print("============== WATCH REQUEST CREATED ==============")
            print(watch_response)
            print("===================================================")
        except Exception:
            traceback.print_exc()
            raise

    except ValueError:
        traceback.print_exc()
        raise fastapi.HTTPException(status_code=401)

    except Exception:
        traceback.print_exc()
        raise fastapi.HTTPException(status_code=500)

    return RedirectResponse("/")


@_router.get("/emailapi/startauth", status_code=200)
async def start_auth():
    """
    Route for starting authentication.
    """
    return RedirectResponse(AUTH_URI)


@_router.get("/emailapi/success", status_code=200)
async def confirm():
    """
    Route for authenttication confirmation.
    """
    return RedirectResponse("/")


@_router.post("/emailapi/webhook")
def gmail_webhook(data: dict, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for pub/sub.
    """
    try:
        gmail_data = decode_base64url_to_json(data["message"]["data"])
        email_account = gmail_data["emailAddress"]
    except Exception:
        traceback.print_exc()
        raise

    gmail_client = client.GMailClient(email_account)

    threads = gmail_client.get_messages_after_history_id(include_previous_emails=False)

    if not threads:
        print("No new threads. Returning.")
        return None

    threads = list(filter(lambda th: th, threads))

    log_email_threads(email_account, threads)
    filtered_threads = list(
        filter(
            lambda th: (th is not None)
            and (email_account not in str(th.og_from))
            and (email_account not in str(th.from_))
            and (
                "mailer-daemon@googlemail.com" not in str(th.og_from)
            )  # causes a feedback loop
            and ("mailer-daemon@googlemail.com" not in str(th.from_)),
            threads,
        )
    )

    if not filtered_threads:
        return None

    background_tasks.add_task(process_email_threads, email_account, filtered_threads)
    return None
