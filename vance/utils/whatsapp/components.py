import os
import random
from typing import Any, Dict, Optional

import pendulum


class MsgComponents:
    """
    Utility class for generating JSON structures for various kinds of messages.
    """

    @classmethod
    def header(
        cls, url: Optional[str] = None, text: Optional[str] = None
    ) -> Dict[str, Any]:
        if url is not None:
            return {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "link": url,
                        },
                    },
                ],
            }
        elif text is not None:
            return {
                "type": "header",
                "parameters": [
                    {
                        "type": "text",
                        "text": "text",
                    },
                ],
            }
        else:
            raise ValueError("Atleast one of the arguments should be not None")

    @classmethod
    def body(cls, parameters: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "body",
            "parameters": parameters,
        }

    @classmethod
    def reply_button(
        cls, index: int = 0, payload: str = "dummy_payload"
    ) -> dict[str, Any]:
        if index > 3:
            raise ValueError("Index cannot be greater than 3")

        return {
            "type": "button",
            "sub_type": "quick_reply",
            "index": str(index),
            "parameters": [
                {
                    "type": "payload",
                    "payload": payload,
                },
            ],
        }

    @classmethod
    def reply_button_interactive(cls, title: str, id_payload: str) -> dict[str, Any]:
        return {
            "type": "button",
            "title": title,
            "id": id_payload,
        }

    @classmethod
    def url_button(cls, index: int = 0, suffix: str = "") -> dict[str, Any]:
        if index > 3:
            raise ValueError("Index cannot be greater than 3")

        return {
            "type": "button",
            "sub_type": "url",
            "index": str(index),
            "parameters": [
                {
                    "type": "text",
                    "text": suffix,
                },
            ],
        }

    @classmethod
    def list_scaffold(
        cls,
        to: str,
        header: dict,
        body: str,
        footer: str,
        button_text: str,
        sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if footer is not None:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {
                        "text": body,
                    },
                    "footer": {
                        "text": footer,
                    },
                    "action": {
                        "button": button_text,
                        "sections": sections,
                    },
                },
            }

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body,
                },
                "action": {
                    "button": button_text,
                    "sections": sections,
                },
            },
        }

    @classmethod
    def buttons_scaffold(
        cls, to: str, body: str, footer: str, buttons: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body,
                },
                "footer": {
                    "text": footer,
                },
                "action": {
                    "buttons": buttons,
                },
            },
        }

    @classmethod
    def list_section(cls, title: str, rows: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "title": title,
            "rows": rows,
        }

    @classmethod
    def list_item(cls, id: str, title: str, description: str) -> dict[str, str]:
        return {
            "id": id,
            "title": title,
            "description": description,
        }

    @classmethod
    def text_scaffold(cls, to: str, text: str) -> dict[str, Any]:
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": text,
            },
        }

    @classmethod
    def template_scaffold(
        cls,
        to: str,
        template_name: str,
        language_code: str = "en",
        body_parameters: Optional[list[str]] = None,
        body_named_parameters: Optional[list[Dict[str, str]]] = None,
        button_payloads: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Construct a WhatsApp template message payload.

        body_parameters must be ordered to match placeholders in the approved template.
        button_payloads sets dynamic quick-reply payloads per button index at send time.
        """
        components: list[Dict[str, Any]] = []
        if body_named_parameters:
            params: list[Dict[str, Any]] = []
            for item in body_named_parameters:
                name = item.get("name")
                value = item.get("value", "")
                param: Dict[str, Any] = {"type": "text", "text": value}
                if name:
                    param["parameter_name"] = name
                params.append(param)
            components.append({"type": "body", "parameters": params})
        elif body_parameters:
            components.append(
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": p or ""} for p in body_parameters
                    ],
                }
            )

        if button_payloads:
            for idx, payload in enumerate(button_payloads):
                components.append({
                    "type": "button",
                    "sub_type": "quick_reply",
                    "index": str(idx),
                    "parameters": [{"type": "payload", "payload": payload}],
                })

        return {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code, "policy": "deterministic"},
                "components": components,
            },
        }

    @classmethod
    def contact_card_scaffold(
        cls, to: str, name: str, phone: str, email: str = None, organization: str = None
    ) -> dict[str, Any]:
        """Generate WhatsApp contact card message with proper structure for 'Message' button."""
        contact_data = {
            "name": {
                "formatted_name": name,
                "first_name": name.split()[0] if name else "Vance",
                "last_name": name.split()[-1] if len(name.split()) > 1 else "",
            },
            "phones": [
                {
                    "phone": phone,
                    "type": "WORK",
                    "wa_id": phone.replace("+", "").replace(" ", "").replace("-", ""),
                }
            ],
        }

        if email:
            contact_data["emails"] = [{"email": email, "type": "WORK"}]

        # Use proper WhatsApp contact structure - don't put bio in org.company
        # This ensures "Message" button appears instead of "Invite to WhatsApp"
        if organization:
            # WhatsApp API doesn't support "notes" field, so use organization fields properly
            contact_data["org"] = {
                "company": (
                    organization[:50] + "..."
                    if len(organization) > 50
                    else organization
                ),
                "title": "AI Superconnector",
            }

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "contacts",
            "contacts": [contact_data],
        }

    @classmethod
    def referral_contact_card_scaffold(
        cls,
        to: str,
        name: str,
        phone: str,
        email: str = None,
        introducer_name: str = None,
    ) -> dict[str, Any]:
        """Generate WhatsApp contact card for referrals with deeplink in phone field."""
        import urllib.parse

        # Create prefilled message with introducer's name
        if introducer_name and introducer_name != "there":
            prefilled_text = f"Hi Vance, {introducer_name} introduced us. I'd love your help with some warm introductions."
        else:
            prefilled_text = (
                "Hi Vance, I'd love your help with some warm introductions."
            )

        # URL encode the prefilled text
        encoded_text = urllib.parse.quote(prefilled_text)

        # Clean phone number for WhatsApp format (remove +, spaces, dashes)
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        # Create deeplink with prefilled message
        deeplink_url = f"https://wa.me/{clean_phone}?text={encoded_text}"

        contact_data = {
            "name": {
                "formatted_name": name,
                "first_name": name.split()[0] if name else "Vance",
                "last_name": name.split()[-1] if len(name.split()) > 1 else "",
            },
            "phones": [
                {
                    "phone": deeplink_url,  # Put deeplink in phone field
                    "type": "WORK",
                    "wa_id": clean_phone,  # Keep clean phone for wa_id
                }
            ],
        }

        if email:
            contact_data["emails"] = [{"email": email, "type": "WORK"}]

        # Set organization for proper WhatsApp contact display
        if introducer_name and introducer_name != "there":
            contact_data["org"] = {
                "company": "AI Superconnector",
                "title": f"Networking Specialist - {introducer_name} connected us",
            }
        else:
            contact_data["org"] = {
                "company": "AI Superconnector",
                "title": "Networking Specialist",
            }

        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "contacts",
            "contacts": [contact_data],
        }

    @classmethod
    def typing_indicator_scaffold(cls, to: str) -> dict[str, Any]:
        """Create typing indicator message."""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "typing",
            "typing": {"action": "typing"},
        }

    @classmethod
    def reaction_scaffold(cls, to: str, message_id: str, emoji: str) -> dict[str, Any]:
        """Create reaction message."""
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }


class MsgBodyParams:
    """
    Parameters that replace placeholders in templates.
    """

    @classmethod
    def text(cls, text: str) -> dict[str, Any]:
        """Plain text."""
        return {
            "type": "text",
            "text": text,
        }

    @classmethod
    def btext(cls, text: str) -> dict[str, Any]:
        """Bold text."""
        return cls.text(f"*{text}*")

    @classmethod
    def date(cls, dt: pendulum.DateTime) -> dict[str, Any]:
        return {
            "type": "date_time",
            "date_time": {
                "fallback_value": dt.to_rfc850_string(),
                "day_of_week": dt.day_of_week + 1,
                "year": dt.year,
                "month": dt.month,
                "day_of_month": dt.day,
                "hour": dt.hour,
                "minute": dt.minute,
                "calendar": "GREGORIAN",
            },
        }


class HumanBehaviorConfig:
    """Configuration for human-like behaviors in messaging."""

    def __init__(
        self,
        # Basic settings
        typing_enabled: bool = True,
        reactions_enabled: bool = True,
        memory_enabled: bool = True,
        # LinkedIn search settings
        linkedin_search_enabled: bool = True,
        scrapingdog_api_key: str = "",
        linkedin_search_max_results: int = 5,
        # Introduction settings
        introduction_detection_enabled: bool = True,
        introduction_patterns: list = None,
        # Call settings
        call_affirmation_enabled: bool = True,
        call_affirmation_patterns: list = None,
    ):
        # Basic settings
        self.typing_enabled = typing_enabled
        self.reactions_enabled = reactions_enabled
        self.memory_enabled = memory_enabled

        # LinkedIn search settings
        self.linkedin_search_enabled = linkedin_search_enabled
        self.scrapingdog_api_key = scrapingdog_api_key or os.getenv(
            "SCRAPINGDOG_API_KEY", ""
        )
        self.linkedin_search_max_results = linkedin_search_max_results

        # Introduction settings
        self.introduction_detection_enabled = introduction_detection_enabled
        self.introduction_patterns = introduction_patterns or [
            "introduce me to",
            "connect me with",
            "introduce me with",
            "i want to meet",
            "i'd like to meet",
            "can you introduce",
            "please introduce",
            "introduce me",
            "connect me to",
            "i want to connect with",
        ]

        # Call settings
        self.call_affirmation_enabled = call_affirmation_enabled
        self.call_affirmation_patterns = call_affirmation_patterns or [
            "call me",
            "ring me",
            "phone me",
            "call now",
            "place a call",
            "yes",
            "sure",
            "go ahead",
            "let's do it",
            "sounds good",
            "ok",
            "okay",
        ]


class HumanBehaviorUtils:
    """Utility class for human-like behaviors in messaging."""

    @staticmethod
    def calculate_typing_duration(text: str, config: HumanBehaviorConfig) -> int:
        """Calculate typing duration based on message complexity."""
        if not config.typing_enabled:
            return 0

        sentences = text.count(".") + text.count("!") + text.count("?")
        if sentences == 0:
            sentences = 1

        return min(sentences * 500, 2000)  # Simple calculation

    @staticmethod
    def should_show_typing(text: str, config: HumanBehaviorConfig) -> bool:
        """Determine if typing indicator should be shown."""
        if not config.typing_enabled:
            return False
        return len(text) > 50

    @staticmethod
    def get_random_reaction(config: HumanBehaviorConfig) -> str:
        """Get a random reaction."""
        if not config.reactions_enabled:
            return ""
        return random.choice(["👍", "🙌", "😊", "🙏"])

    @staticmethod
    def is_introduction_request(text: str, config: HumanBehaviorConfig) -> bool:
        """Check if text contains an introduction request."""
        if not config.introduction_detection_enabled:
            return False

        text_lower = text.lower().strip()
        return any(
            pattern.lower() in text_lower for pattern in config.introduction_patterns
        )

    @staticmethod
    def extract_person_name(text: str, config: HumanBehaviorConfig) -> str:
        """Extract person name from introduction request."""
        import re

        text_lower = text.lower().strip()
        patterns = [
            r"introduce me to\s+([a-zA-Z\s]+)",
            r"connect me with\s+([a-zA-Z\s]+)",
            r"i want to meet\s+([a-zA-Z\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                name = match.group(1).strip()
                name = re.sub(r"\b(to|with|me|you|can|please)\b", "", name).strip()
                if name:
                    return name.title()

        return ""


class MemoryUtils:
    """Utility class for conversation memory and context management."""

    @staticmethod
    def get_conversation_summary(uid: str, depth: int = 5) -> str:
        """Get conversation summary for context."""
        try:
            from utils.db import load_conversation

            messages = load_conversation(uid)
            if not messages:
                return ""

            recent_messages = messages[-depth:] if len(messages) > depth else messages
            summary_parts = []

            for msg in recent_messages:
                if hasattr(msg, "content") and msg.content:
                    summary_parts.append(f"- {msg.content[:100]}...")

            return "\n".join(summary_parts) if summary_parts else ""
        except Exception:
            return ""

    @staticmethod
    def get_conversation_context(uid: str, config: HumanBehaviorConfig) -> dict:
        """Get conversation context."""
        if not config.memory_enabled:
            return {}

        return {"conversation_summary": MemoryUtils.get_conversation_summary(uid, 5)}
