"""
Contains functions for extracting text from email payloads and
other parsing type use cases.
"""

import base64
import html
import json
import re
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Union
from uuid import uuid4

import pendulum
from bs4 import BeautifulSoup
from bs4.element import Comment

from .email_parser import email_message_parser
from .settings import SELF_EMAIL
from .types import ParsedEmailThread


def gmail_thread_parser(
    thread: dict,
    latest_only: bool = True,
    self_email: str = SELF_EMAIL,
) -> Optional[ParsedEmailThread]:
    """
    Parses a gmail thread into a list of simpler thread object.
    """
    assert self_email
    messages = thread["messages"]

    try:
        parsed_message = gmail_message_parser(messages[-1], self_email)

        if latest_only and parsed_message:
            return parsed_message

        parent = gmail_message_parser(messages[0], self_email)

        if parent is not None:
            if len(messages) == 1:
                return parent

            for _, message in enumerate(messages[1:], 1):
                if parsed_msg := gmail_message_parser(message):
                    parent.replies.append(parsed_msg)

        return parent

    except Exception:
        traceback.print_exc()
        return None


def gmail_message_parser(
    message: Dict[str, Any],
    self_email: str = SELF_EMAIL,
) -> Optional[ParsedEmailThread]:
    """
    Parses a gmail message into an instance of ParsedEmail.
    """
    try:
        ts = message.get("internalDate")
        if ts is None:
            ts = pendulum.now()
        else:
            ts = pendulum.from_timestamp(float(ts) / 1000)

        payload = message.get("payload")
        if payload is None:
            return None

        headers = {
            header["name"].lower(): header["value"]
            for header in payload.get("headers", [])
        }

        parts = payload.get("parts", [])
        if not parts:
            # Check if body data exists directly in payload
            body_data = payload.get("body", {}).get("data")
            if body_data:
                parts = [
                    {
                        "mimeType": payload.get("mimeType", "text/plain"),
                        "body": {"data": body_data},
                    }
                ]
            else:
                return None

        if "<" in (og_from := headers.get("from", "")):
            og_from = (og_from.split("<")[1].split(">"))[0].strip()

        text = ""
        new_email = ""
        quoted_thread = ""
        body_html = ""
        body_html_parts = []

        for _, part in enumerate(parts):
            if part.get("mimeType") == "text/plain":
                part_data = part.get("body", {}).get("data")
                if part_data:
                    try:
                        raw_bytes = base64.urlsafe_b64decode(part_data)
                        plain_text_msg = raw_bytes.decode()
                        plain_text_msg = plain_text_msg.replace("\r\n", "\n")

                        markers = ["\nOn ", "\n> ", "\n\nOn"]
                        main_message = plain_text_msg

                        for marker in markers:
                            if marker in plain_text_msg:
                                parts = plain_text_msg.split(marker, 1)
                                main_message = parts[0]
                                quoted_thread = (
                                    marker + parts[1] if len(parts) > 1 else ""
                                )
                                break

                        main_message = (
                            main_message.replace(SELF_EMAIL, "")
                            .replace("  ", " ")
                            .strip()
                        )

                        text = plain_text_msg
                        new_email = main_message

                    except Exception:
                        traceback.print_exc()
                        text = message.get("snippet", "")
                        new_email = text
                        quoted_thread = ""
                else:
                    text = ""
                    new_email = ""
                    quoted_thread = ""

                continue

            if part["mimeType"] == "text/html":
                if text:
                    continue

                part_data = part.get("body", {}).get("data")
                if part_data:
                    try:
                        body_html = base64.urlsafe_b64decode(part_data).decode()
                    except Exception:
                        traceback.print_exc()
                        body_html = message.get("snippet", "")
                    body_html_parts = body_html.split('<div class="gmail_quote">', 1)
                else:
                    body_html = ""
                    body_html_parts = []

                if len(body_html_parts) < 1:
                    continue
                elif len(body_html_parts) == 1:
                    new_email = (
                        "On "
                        + ts.to_day_datetime_string()
                        + " "
                        + og_from
                        + " wrote:\n"
                        + text_from_html(body_html_parts[0])
                    )
                    text = new_email
                else:
                    new_email = (
                        "On "
                        + ts.to_day_datetime_string()
                        + " "
                        + og_from
                        + " wrote:\n"
                        + text_from_html(body_html_parts[0])
                    )
                    text = new_email
                    quoted_thread = text_from_html(
                        '<div class="gmail_quote">' + body_html_parts[1]
                    )

                break

        if new_email is not None:
            new_email = new_email.strip(" ").strip("\n").strip("\r")

        if text is not None:
            text = text.strip(" ").strip("\n").strip("\r")

        parsed_correctly = bool(new_email) and bool(text)

        if not parsed_correctly:
            try:
                th = email_message_parser(message, self_email)
            except:
                pass
            else:
                return th

        return ParsedEmailThread(
            ts=ts,
            to=headers.get("to"),
            cc=headers.get("cc"),
            bcc=headers.get("bcc"),
            date=headers.get("date"),
            from_=headers.get("from"),
            og_from=og_from,
            subject=headers.get("subject"),
            message_id=headers.get("message-id"),
            html=body_html,
            text=text,
            new_email=new_email,
            quoted_thread=quoted_thread,
            user_email=og_from,
            summary=None,
            self_email=self_email,
        )

    except Exception:
        traceback.print_exc()
        return None


def tag_visible(element):
    if element.parent.name in [
        "style",
        "script",
        "head",
        "title",
        "meta",
        "[document]",
        "yatag",
    ]:
        return False

    if isinstance(element, Comment):
        return False

    return True


def text_from_html(body: str):
    unique = uuid4().hex[:8]
    placeholder = f"<div>{unique}</div>"
    body = body.replace("<br>", placeholder)

    soup = BeautifulSoup(body, "html.parser")
    texts = (
        soup.findAll()
    )  # removed text=True due to Pyright error. might cause problems.
    visible_texts = filter(tag_visible, texts)

    return (
        (" ".join(t.strip() for t in visible_texts))
        .replace(unique, "\n")
        .replace(" \n ", "\n")
        .replace("\n ", "\n")
        .replace(" \n", "\n")
    )


def parse_cc_header(cc_header):
    matches = re.findall(r"<(.*?)>|([\w\.-]+@[\w\.-]+)", cc_header)
    email_addresses = ", ".join(
        [
            match[0] if match[0] else match[1]
            for match in matches
            if match[0] or match[1]
        ]
    )
    return email_addresses


def create_message(
    to: list[str],
    cc: list[str],
    bcc: list[str],
    from_: str,
    subject: str,
    content: str,
    self_name: str = "",
    self_email: str = "",
):
    """
    Creates valid email formatted message with quoted history.
    """
    message = MIMEMultipart()

    cc_header = ", ".join(cc)
    to_header = ", ".join(to)
    bcc_header = ", ".join(bcc)

    message["From"] = from_ if from_ else f"{self_name} <{self_email}>"
    message["To"] = to_header
    message["Cc"] = cc_header
    message["Bcc"] = bcc_header
    message["Subject"] = subject

    BODY = """<div dir="ltr">{content}</div>
<br>
{footer}
<br>
"""

    footer = ""

    body = BODY.format(
        content=content.replace("\n", "<br>"),
        footer=footer,
    )

    msg = MIMEText(body, "html")

    message.attach(msg)

    return {
        "raw": base64.urlsafe_b64encode(message.as_string().encode()).decode(),
    }


def remove_email_from_header_string(name: str, email: str, header: str) -> str:
    """
    Remove email from header string.
    """
    to_remove = [
        f", {name} <{email}>",
        f"{name} <{email}>",
        email,
        '"" <>',
    ]
    for item in to_remove:
        header = header.replace(item, "")

    return header


def create_reply(
    thread: ParsedEmailThread,
    reply: str,
    self_name: str = "",
    self_email: str = "",
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
    send_to_user_only: bool = False,
):
    """
    Creates valid email formatted message with quoted history.
    """
    message = MIMEMultipart()

    if not send_to_user_only:
        cc = thread.cc if thread.cc else ""
        cc = parse_cc_header(cc)
        from_ = thread.from_ if thread.from_ else ""
        to = thread.to if thread.to else ""
        og_from = thread.og_from if thread.og_from else ""
    else:
        assert user_name
        assert user_email

        cc = ""
        from_ = ""
        to = f"{user_name} <{user_email}>"
        og_from = ""

    message["From"] = f"{self_name} <{self_email}>"
    to_field = from_ + ", " + to + ", " + og_from
    to_field = remove_email_from_header_string(self_name, self_email, to_field)
    to_field = remove_email_from_header_string(
        "Ember Spark", "ember.spark@ignitetech.com", to_field
    )

    message["To"] = to_field
    cc_field = remove_email_from_header_string(self_name, self_email, cc)

    message["Cc"] = cc_field
    message["Bcc"] = thread.bcc if not send_to_user_only else ""  # pyright: ignore
    message["In-Reply-To"] = thread.message_id  # pyright: ignore
    message["References"] = thread.message_id  # pyright: ignore

    if thread.subject.upper().startswith("RE:"):  # pyright: ignore
        message["Subject"] = thread.subject  # pyright: ignore
    else:
        message["Subject"] = "Re: " + thread.subject  # pyright: ignore

    # Modify the BODY template to handle None values
    BODY = """<div dir="ltr">{reply}</div>
<br>
{footer}
<br>
{quote_section}
"""
    # Only add quote section if we have valid thread data
    if thread.date and thread.from_ and thread.quoted_thread:
        quote_section = f"""<div class="gmail_quote">
<div dir="ltr" class="gmail_attr">On {html.escape(str(thread.date))}, {html.escape(str(thread.from_))} wrote:<br></div>
<blockquote class="gmail_quote" style="margin:0px 0px 0px 0.8ex; border-left: 1px solid rgb(204,204,204);padding-left: 1ex;">
{thread.quoted_thread}
</blockquote></div>"""
    else:
        quote_section = ""

    footer = ""

    formatted_reply = reply.replace("\n", "<br>")

    body = BODY.format(
        reply=formatted_reply,
        footer=footer,
        quote_section=quote_section,
    )

    msg = MIMEText(body, "html")
    message.attach(msg)

    raw_message = message.as_string()

    encoded_message = base64.urlsafe_b64encode(raw_message.encode()).decode()

    return {
        "raw": encoded_message,
        "threadId": thread.thread_id,
    }


def decode_base64url_to_json(input_str: str):
    """
    Decodes a URL-safe Base64 string.
    """
    # Replace URL-safe characters with regular Base64 characters
    input_str = input_str.replace("-", "+").replace("_", "/")
    # Pad with '=' to make the length of the string a multiple of 4
    padding = len(input_str) % 4
    if padding == 2:
        input_str += "=="
    elif padding == 3:
        input_str += "="
    elif padding != 0:
        raise ValueError("Invalid base64url string")

    # Decode the string
    decoded_bytes = base64.b64decode(input_str)
    # Convert bytes to string and parse JSON
    decoded_str = decoded_bytes.decode("utf-8")
    json_data = json.loads(decoded_str)

    return json_data
