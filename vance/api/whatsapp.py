"""
WhatsApp webhook handler for Vance AI agent.
Uses agent-based architecture with pydantic-ai.
"""

from .whatsapp_modules.router_agent import router as _router

__all__ = ["_router"]
