"""
Vance Agent Module

This module provides an agent-based approach for handling WhatsApp conversations.
The agent uses pydantic-ai with tools that are dynamically injected based on user type.
"""

from .agent import get_tools_for_user_type, initialize_agent
from .models import AgentDeps, UserType
from .runner import runner

__all__ = [
    "initialize_agent",
    "get_tools_for_user_type",
    "runner",
    "AgentDeps",
    "UserType",
]
