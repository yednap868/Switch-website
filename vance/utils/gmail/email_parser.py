import base64
import html
import re
from typing import Any, Dict, Optional
from uuid import uuid4

import pendulum
from bs4 import BeautifulSoup
from bs4.element import Comment

from .settings import SELF_EMAIL
from .types import ParsedEmailThread


def extract_quoted_part(html_body):
    """
    Extracts the quoted part from the HTML body of an email.
    """
    if not html_body:
        return ""

    quoted_patterns = [
        "<blockquote[^>]*>(.*?)</blockquote>",
        '<div class="quoted-text"[^>]*>(.*?)</div>',
        '<div class="gmail_quote">',
        # to do add more
    ]

    for pattern in quoted_patterns:
        quoted_match = re.search(pattern, html_body, re.IGNORECASE | re.DOTALL)
        if quoted_match:
            return html.unescape(quoted_match.group(1))

    return ""


def email_message_parser(
    message: Dict[str, Any],
    self_email: str = SELF_EMAIL,
) -> Optional[ParsedEmailThread]:
    """
    Parses a gmail message into an instance of ParsedEmail.
    """
    ts = message.get("internalDate")
    ts = pendulum.from_timestamp(float(str(ts)) / 1000)

    payload = message.get("payload")

    if payload is None:
        return None

    headers = {
        header["name"].lower(): header["value"] for header in payload.get("headers", [])
    }

    from_ = headers.get("from")
    to = headers.get("to")
    cc = headers.get("cc")
    bcc = headers.get("bcc")
    date = headers.get("date")
    subject = headers.get("subject")
    message_id = headers.get("message-id")

    og_from = extract_email_address(str(from_))

    text = ""
    html_body = ""

    parts = payload.get("parts")

    result = {"text": "", "html": "", "attachments": []}

    if not parts:
        if payload.get("body", {}).get("data") is not None:
            if headers.get("content-type") == "text/plain":
                result["text"] = base64.urlsafe_b64decode(
                    (payload["body"]["data"])
                ).decode()
            elif headers.get("content-type") == "text/html":
                result["html"] = base64.urlsafe_b64decode(
                    (payload["body"]["data"])
                ).decode()
        else:
            return None

    while parts:
        part = parts.pop(0)

        if "parts" in part:
            parts.extend(part["parts"])

        if part["mimeType"] == "text/plain":
            result["text"] = base64.urlsafe_b64decode((part["body"]["data"])).decode()

        if part["mimeType"] == "text/html":
            result["html"] = base64.urlsafe_b64decode((part["body"]["data"])).decode()

        if "attachmentId" in part["body"]:
            result["attachments"].append(
                {
                    "partId": part["partId"],
                    "mimeType": part["mimeType"],
                    "filename": part.get("filename", ""),
                    "body": part["body"],
                }
            )

    if result["text"] == "":
        result["text"] = extract_text_from_html(result["html"])

    text = parse_quotes(result["text"])
    html_body = result["html"]
    new_email, quoted_thread = extract_new_email_and_quoted_part(result["text"])
    # new_email = parse_quotes(new_email)

    new_email = (
        "On " + ts.to_day_datetime_string() + " " + og_from + " wrote:\n"
    ) + new_email

    return ParsedEmailThread(
        ts=ts,
        to=to,
        cc=cc,
        bcc=bcc,
        date=date,
        from_=from_,
        og_from=og_from,
        subject=subject,
        message_id=message_id,
        html=html_body,
        text=text,
        new_email=new_email,
        summary="",
        quoted_thread=quoted_thread,
        user_email=og_from,  # og_from is the user's email
        self_email=self_email,
    )


def parse_quotes(text):
    return re.sub(r"(?<!<)>", "", text)


def extract_text_from_html(html):
    """
    Extract text content from HTML.

    Parameters:
        html (str): The HTML string.

    Returns:
        str: The extracted text content.
    """
    # Parse the HTML
    soup = BeautifulSoup(html, "html.parser")

    # Extract text content
    text = soup.get_text(separator="\n", strip=True)

    return text


def format_email_text(email_text):
    # Remove '>' characters from the text
    email_text = re.sub(r">+", "", email_text)

    # Remove '\n' and '\r' characters
    email_text = email_text.replace("\r\n", "\n")

    # Remove consecutive whitespace characters
    email_text = re.sub(r"\s+", " ", email_text)

    # Remove leading and trailing whitespace
    email_text = email_text.strip()

    return email_text


def extract_email_address(header: str) -> str:
    """
    Extracts the email address from a header string containing the email address and name.
    """
    if "<" in header and ">" in header:
        return header.split("<", 1)[1].split(">", 1)[0]
    else:
        return header


def extract_new_email_and_quoted_part(email_text):
    # Find the index of the first occurrence of '>'
    quote_index = email_text.find("\n>")

    # If '>' is found, check if the next line also contains '>'
    if quote_index != -1:
        # Check if the next line after '>' contains '>'
        next_line_index = email_text.find("\n", quote_index)
        if next_line_index != -1 and "\n>" in email_text[next_line_index:]:
            # Extract text before '>' as new_email and text after '>' as quoted_part
            new_email = email_text[:quote_index]
            quoted_part = email_text[quote_index:]
        else:
            # If the next line does not contain '>', consider the entire text as new_email
            new_email = email_text
            quoted_part = ""
    else:
        # If '>' is not found, consider the entire text as new_email and quoted_part as empty
        new_email = email_text
        quoted_part = ""

    return new_email.strip(), quoted_part.strip()


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
