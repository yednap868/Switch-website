from dataclasses import dataclass, field
from typing import Literal, Optional

import pendulum


@dataclass
class ParsedEmailThread:
    ts: Optional[pendulum.DateTime]
    to: Optional[str]
    cc: Optional[str]
    bcc: Optional[str]
    date: Optional[str]
    from_: Optional[str]
    og_from: Optional[str]
    user_email: Optional[str]
    subject: Optional[str]
    html: Optional[str]
    text: Optional[str]
    new_email: Optional[str]
    summary: Optional[str]
    quoted_thread: Optional[str]
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    event_id: Optional[str] = None
    self_email: Optional[str] = None
    replies: list["ParsedEmailThread"] = field(default_factory=list)
    LATEST_REPLY_INDEX: Literal[0, -1] = 0

    @classmethod
    def from_dicts(
        cls,
        self_dict: dict,
        children_dicts: list[dict],
        latest_reply_first: bool = True,
    ) -> "ParsedEmailThread":
        LATEST_REPLY_INDEX = 0
        if latest_reply_first:
            replies = [cls.from_dicts(child, []) for child in reversed(children_dicts)]
        else:
            replies = [cls.from_dicts(child, []) for child in children_dicts]
            LATEST_REPLY_INDEX = -1

        ts = self_dict.get("ts")

        if not isinstance(ts, str) and ts:
            ts = pendulum.parse(ts.isoformat())
        else:
            ts = pendulum.parse(str(ts))

        assert isinstance(ts, pendulum.DateTime)

        return cls(
            ts=ts,
            to=self_dict.get("to"),
            cc=self_dict.get("cc"),
            bcc=self_dict.get("bcc"),
            date=self_dict.get("date"),
            from_=self_dict.get("from"),
            user_email=self_dict.get("user_email", self_dict.get("og_from")),
            og_from=self_dict.get("og_from"),
            subject=self_dict.get("subject"),
            html=self_dict.get("html"),
            text=self_dict.get("text"),
            new_email=self_dict.get("new_email"),
            summary=self_dict.get("summary"),
            quoted_thread=self_dict.get("quoted_thread"),
            thread_id=self_dict.get("thread_id"),
            message_id=self_dict.get("message_id"),
            event_id=self_dict.get("event_id"),
            self_email=self_dict.get("assistant_email"),
            replies=replies,
            LATEST_REPLY_INDEX=LATEST_REPLY_INDEX,
        )

    @property
    def latest_reply(self) -> "ParsedEmailThread":
        return self.replies[self.LATEST_REPLY_INDEX] if len(self.replies) > 0 else self

    def __str__(self) -> str:
        """
        Override the default string representation of the object.
        """

        def format_email(email_obj: "ParsedEmailThread"):
            lines = []
            date_str = (
                email_obj.ts.format("MMM D, YYYY [at] h:mm A")
                if email_obj.ts
                else "Unknown date"
            )
            from_str = email_obj.og_from or email_obj.from_ or "Unknown"
            lines.append(f"On {date_str}, {from_str} wrote:")

            # Additional headers as secondary info
            if email_obj.to:
                lines.append(f"To: {email_obj.to}")
            if email_obj.cc:
                lines.append(f"CC: {email_obj.cc}")

            lines.append("-" * 60)

            # Email body - prefer text over html
            content = (
                email_obj.new_email or email_obj.text or email_obj.html or "No content"
            )
            lines.append(content.strip())

            return "\n".join(lines)

        # Collect all emails (root + replies) and sort chronologically
        all_emails = [self] + self.replies
        all_emails.sort(key=lambda email: email.ts or pendulum.now())

        # Format the thread
        result = []
        for i, email_obj in enumerate(all_emails):
            if i > 0:  # Add separator between emails
                result.append(f"\n{'═' * 60}")

            result.append(format_email(email_obj))

        return "\n".join(result)
