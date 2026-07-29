"""
The GMail API Client. Uses GCP Pub/Sub and GMail API to send and receive emails.
"""

import traceback
from typing import List, Optional, Union

import requests
from . import cred
from .settings import PUB_SUB_TOPIC_NAME, SELF_EMAIL, SELF_NAME
from .types import ParsedEmailThread
from .util import create_message, create_reply, gmail_thread_parser
from utils.firebase_init import fs


class GMailClient:
    """
    Client for Google Calendar API.
    """

    def __init__(self, email: str):
        """
        Initialize the client
        """
        print(f"GMailClient.__init__({email})")

        self.tz_name = cred.TZ_NAME
        self.email = email

        self.BASE_URL = "https://gmail.googleapis.com/gmail/v1"
        self.WATCH_URL = f"{self.BASE_URL}/users/me/watch"
        self.GET_MSG_URL = f"{self.BASE_URL}/users/me/messages"
        self.SEND_MSG_URL = f"{self.BASE_URL}/users/me/messages/send"
        self.GET_THREADS = f"{self.BASE_URL}/users/me/threads"
        self.GET_HISTORY = f"{self.BASE_URL}/users/me/history"

        # tokens and headers
        self.access_token = cred.get_access_token(self.email)
        self.auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        self.history_id = cred.load_last_history_id(self.email)

        if not self.history_id:
            self.sync()

    def _refresh_auth_headers(self):
        """
        Refresh auth headers
        """
        print("GMailClient._refresh_auth_headers()")

        self.access_token = cred.get_access_token(self.email)
        self.auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_messages_after_history_id(
        self, include_previous_emails: bool = False
    ) -> Optional[List[Optional[ParsedEmailThread]]]:
        """
        Retrieves all messages after a given history_id.
        """
        self._refresh_auth_headers()

        params = {
            "startHistoryId": self.history_id,
            "historyTypes": ["messageAdded"],
        }

        try:
            res = requests.get(
                self.GET_HISTORY,
                params=params,
                headers=self.auth_headers,
                timeout=10,
            )
        except Exception:
            traceback.print_exc()
            return None

        res = res.json()
        history_id = res.get("historyId")

        if not history_id:
            return []

        self.history_id = history_id

        cred.update_history_id(self.email, history_id)

        history = res.get("history")
        if history is None:
            return None

        new_threads = []

        for _, item in enumerate(history, 1):
            messages = item.get("messages")

            if messages is None:
                continue

            for _, message in enumerate(messages, 1):
                thread_id = message.get("threadId")

                thread = self.get_thread(thread_id)
                if not thread:
                    continue

                labels = thread.get("messages", [{}])[-1].get("labelIds", [])

                if "DRAFT" in labels:
                    continue

                extracted_msg = gmail_thread_parser(
                    thread, not include_previous_emails, self.email
                )

                if extracted_msg is None:
                    continue

                extracted_msg.thread_id = thread_id
                extracted_msg.self_email = self.email

                if extracted_msg.replies:
                    for reply_idx in range(len(extracted_msg.replies)):
                        extracted_msg.replies[reply_idx].thread_id = thread_id
                        extracted_msg.replies[reply_idx].self_email = self.email

                new_threads.append(extracted_msg)

        return new_threads

    def send_email(
        self,
        subject: str,
        content: str,
        to: list[str] = [],
        cc: list[str] = [],
        bcc: list[str] = [],
        from_: Optional[str] = None,
        self_name: str = SELF_NAME,
        self_email: str = SELF_EMAIL,
    ):
        """
        Start a new email thread using to, cc, bcc.
        """
        print("GMailClient.reply_to_thread()")
        self._refresh_auth_headers()

        if not from_:
            from_ = f"{self_name} <{self_email}>"

        msg = create_message(
            to=to,
            cc=cc,
            bcc=bcc,
            from_=from_,
            subject=subject,
            content=content,
            self_name=self_name,
            self_email=self_email,
        )

        res = requests.post(
            self.SEND_MSG_URL,
            json=msg,
            headers=self.auth_headers,
            timeout=10,
        )

        return res

    def reply_to_thread(
        self,
        thread: ParsedEmailThread,
        reply: str,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        send_to_user_only: bool = False,
        self_name: str = SELF_NAME,
        self_email: str = SELF_EMAIL,
    ):
        """
        Reply to a specific thread using thread_id.
        """
        self._refresh_auth_headers()

        if not thread:
            return None

        if send_to_user_only:
            assert user_name and user_email
            msg = create_reply(
                thread=thread,
                reply=reply,
                self_name=self_name,
                self_email=self_email,
                user_name=user_name,
                user_email=user_email,
                send_to_user_only=send_to_user_only,
            )
        else:
            msg = create_reply(
                thread=thread,
                reply=reply,
                self_name=self_name,
                self_email=self_email,
            )

        res = requests.post(
            self.SEND_MSG_URL,
            json=msg,
            headers=self.auth_headers,
            timeout=10,
        )
        res = res.json()

        return res

    def get_thread(self, thread_id: str) -> Optional[dict]:
        """
        Get a specific thread from the inbox using thread_id.
        """
        self._refresh_auth_headers()

        params = {
            "format": "full",
        }

        res = requests.get(
            f"{self.GET_THREADS}/{thread_id}",
            params=params,
            headers=self.auth_headers,
            timeout=10,
        )

        if res.status_code > 299:
            return None

        return res.json()

    def get_threads(self, max_results=100) -> dict:
        """
        Retrieve threads from GMail.
        """
        self._refresh_auth_headers()

        params = {
            "maxResults": max_results,
        }

        res = requests.get(
            self.GET_THREADS,
            params=params,
            headers=self.auth_headers,
            timeout=10,
        )

        return res.json()

    def create_watch_request(self):
        """
        Create a watch request for the gmail api.
        """
        self._refresh_auth_headers()

        data = {
            "topicName": PUB_SUB_TOPIC_NAME,
            "labelIds": ["INBOX"],
            "labelFilterBehaviour": "INCLUDE",
        }

        res = requests.post(
            url=self.WATCH_URL,
            json=data,
            timeout=10,
            headers=self.auth_headers,
        )

        return res.json()

    def sync(self):
        """
        Sync locally saved latest history_id to GMail servers so that we only
        process the latest emails.
        """
        self._refresh_auth_headers()

        threads = self.get_threads(1)
        if len(threads) == 0:
            return

        history_id = threads["threads"][0].get("historyId")

        if history_id:
            self.history_id = history_id
            cred.update_history_id(self.email, history_id)
        else:
            raise ValueError("No last history ID found.")
