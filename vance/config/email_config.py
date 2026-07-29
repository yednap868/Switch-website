"""
Email workflow configuration.
Manages email templates, introduction flow, and follow-up settings.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class EmailConfig:
    """Configuration for email introduction workflow."""

    # Email introduction flow steps
    intro_steps: List[str] = None

    # Email templates
    introduction_template: str = None
    follow_up_template: str = None

    # Follow-up settings
    follow_up_delay_days: int = 3
    max_follow_up_attempts: int = 2

    # Email settings
    max_recipients_per_intro: int = 3
    cc_user_on_introductions: bool = True

    def __post_init__(self):
        """Initialize default values if not provided."""
        if self.intro_steps is None:
            self.intro_steps = [
                "connection_reason",
                "desired_outcome",
                "background_context",
            ]

        if self.introduction_template is None:
            self.introduction_template = """
Hi {recipient_name},

I'm Vance - an AI super-connector that makes high-signal, context-rich introductions at just the right moment.

One of my friends, who's currently {user_focus}, is looking for {urgent_need}. Based on what you're working on, I believe you could be a great person for them to connect with.

Would it make sense for you?

If you say yes, I'll go ahead and make the introduction - warm, thoughtful, and right on time.

Best,
Vance - Your AI Super Connector
            """.strip()

        if self.follow_up_template is None:
            self.follow_up_template = """
Hi! I wanted to follow up on the introduction I made last week. 
I understand you're busy, but I wanted to make sure you received my message. 
If you're not interested, no worries at all - just let me know so I can update my records.
            """.strip()

        # Warm introduction template for when both parties agree
        self.warm_introduction_template = """
Hi {user_name} and {recipient_name},

Excited to connect you both!

{user_name}, meet {recipient_name} — {recipient_description}.

{recipient_name}, meet {user_name} — {user_description}.

From what I understand, {connection_context}. Thought this could be a meaningful conversation for both of you.

I'll let you two take it from here - feel free to loop me out.

Best,
Vance - Your AI super-connector
        """.strip()

    def get_intro_step_prompt(self, step: str) -> str:
        """Get prompt for introduction step."""
        prompts = {
            "connection_reason": "What's the main reason you'd like to connect with this person? (e.g., 'I'm looking for a co-founder', 'I need help with marketing', 'I want to learn about their industry')",
            "desired_outcome": "What specific outcome are you hoping for from this connection? (e.g., 'I'd like to schedule a call', 'I want to learn about their experience', 'I'm looking for a partnership')",
            "background_context": "Any specific context or background you'd like me to include? (e.g., 'I'm a first-time founder', 'I have 10 years in tech', 'I'm pivoting from finance to AI')",
        }
        return prompts.get(step, "")

    def format_introduction_email(self, **kwargs) -> str:
        """Format introduction email with provided data."""
        return self.introduction_template.format(**kwargs)

    def format_follow_up_email(self, **kwargs) -> str:
        """Format follow-up email with provided data."""
        return self.follow_up_template.format(**kwargs)

    def format_warm_introduction_email(self, **kwargs) -> str:
        """Format warm introduction email with provided data."""
        return self.warm_introduction_template.format(**kwargs)
