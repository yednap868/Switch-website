"""
Configuration module for Vance AI agent.
Provides centralized configuration management for all components.
"""

from .email_config import EmailConfig
from .settings import Settings

__all__ = [
    "EmailConfig",
    "Settings",
]
