"""
Main settings configuration.
Central configuration management for the application.
"""

import os
from typing import Optional

from .email_config import EmailConfig


class Settings:
    """Main settings class that loads and manages all configurations."""

    def __init__(self):
        """Initialize settings with default configurations."""
        self.email = EmailConfig()
        self._load_environment_overrides()

    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables."""
        # Email overrides
        if os.getenv("EMAIL_FOLLOW_UP_DELAY_DAYS"):
            self.email.follow_up_delay_days = int(
                os.getenv("EMAIL_FOLLOW_UP_DELAY_DAYS")
            )

        if os.getenv("EMAIL_MAX_FOLLOW_UP_ATTEMPTS"):
            self.email.max_follow_up_attempts = int(
                os.getenv("EMAIL_MAX_FOLLOW_UP_ATTEMPTS")
            )

    def get_email_config(self) -> EmailConfig:
        """Get email configuration."""
        return self.email

    # Legacy methods - kept for backwards compatibility but return None/empty
    def get_conversation_config(self):
        """Legacy - conversation is now handled by agent."""
        return None

    def get_behavior_config(self):
        """Legacy - behavior is now handled by agent."""
        return None


# Global settings instance
settings = Settings()
