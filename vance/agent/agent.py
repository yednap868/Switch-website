"""
Agent initialization with dynamic tool injection based on user type.
"""

import json
import os
from typing import Any, Dict, Literal, Optional

from pydantic_ai import Agent

from agent.tools.common import COMMON_TOOLS, log_arbitrary_data, log_extraction_data
from agent.tools.job_provider import JOB_PROVIDER_TOOLS
from agent.tools.job_seeker import JOB_SEEKER_TOOLS

from .models import AgentDeps, UserType, detect_user_type


def load_system_prompt(
    mode: Literal["voice", "text"],
    user_profile: Optional[Dict[str, Any]] = None,
    extraction_data: Optional[Dict[str, Any]] = None,
    conversation_summary: Optional[str] = None,
) -> str:
    """
    Load the system prompt for the specified mode with dynamic context.

    Args:
        mode: Either "voice" or "text"
        user_profile: User's profile data from Firestore
        extraction_data: Extraction data from voice calls
        conversation_summary: Summary of conversation history

    Returns:
        System prompt string with context substituted
    """
    # Use absolute path to ensure we load the correct file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, "static", f"system_prompt_{mode}.md")
    
    with open(prompt_path, "r") as f:
        template = f.read()
    
    # Log first line to verify we're loading Switch prompt
    first_line = template.split('\n')[0] if template else ""
    print(f"[AGENT] Loaded system prompt from {prompt_path}")
    print(f"[AGENT] First line: {first_line[:80]}...")

    # Format user profile for display
    if user_profile:
        profile_str = json.dumps(user_profile, indent=2, default=str)
    else:
        profile_str = "No profile yet - this is a new user"
        user_profile = {}

    # Extract user type and connection_type for voice calls
    user_type = detect_user_type(user_profile) if user_profile else None
    user_type_str = user_type.value if user_type and hasattr(user_type, 'value') else (user_profile.get("user_type") or "general") if user_profile else "general"
    
    # Extract connection_type from profile (from WhatsApp conversation)
    connection_type = (
        user_profile.get("connection_type")
        or user_profile.get("goal")
        or user_profile.get("primary_goal")
        or user_profile.get("arbitrary", {}).get("connection_type")
        or user_profile.get("profile", {}).get("connection_type")
        or user_profile.get("profile", {}).get("goal")
        or ""
    )
    
    # Clean up connection_type for job providers (remove "hiring", "looking to hire", etc.)
    primary_goal = user_profile.get("primary_goal", "") or connection_type or ""
    if user_type_str == "job_provider" and primary_goal:
        connection_type_clean = primary_goal.lower()
        # Remove common prefixes for job providers
        for prefix in ["hiring", "looking to hire", "looking for", "need to hire", "recruiting"]:
            if connection_type_clean.startswith(prefix):
                connection_type_clean = connection_type_clean[len(prefix):].strip()
                # If it still has "for" at the start, remove it
                if connection_type_clean.startswith("for "):
                    connection_type_clean = connection_type_clean[4:].strip()
                connection_type = connection_type_clean
                break
        else:
            # If no prefix found but it's a job provider, use as-is
            connection_type = primary_goal
    elif user_type_str == "job_seeker" and primary_goal:
        # For job seekers, extract what they're looking for
        if "looking for" in primary_goal.lower():
            parts = primary_goal.split("looking for", 1)
            if len(parts) > 1:
                connection_type = parts[1].strip()
            else:
                connection_type = primary_goal
        else:
            connection_type = primary_goal or connection_type
    
    # Format extraction data for display
    if extraction_data:
        extraction_str = json.dumps(extraction_data, indent=2, default=str)
    else:
        extraction_str = "No call data yet - user hasn't had a voice call"

    # Format conversation summary
    summary_str = conversation_summary or "New conversation"
    
    # Extract basic user info for easier access in prompts
    user_name = user_profile.get("name") or user_profile.get("profile", {}).get("name") or ""
    user_email = user_profile.get("email") or user_profile.get("profile", {}).get("email") or ""
    linkedin_url = user_profile.get("linkedin_url") or user_profile.get("linkedin") or user_profile.get("profile", {}).get("linkedin_url") or ""
    if isinstance(linkedin_url, dict):
        linkedin_url = linkedin_url.get("linkedin_url") or linkedin_url.get("url") or ""

    # Substitute placeholders (escape double braces for ElevenLabs dynamic variables)
    # First replace Python format placeholders, then leave ElevenLabs placeholders intact
    formatted = template.replace("{{", "___DOUBLE_BRACE___").replace("}}", "___CLOSE_BRACE___")
    formatted = formatted.format(
        user_profile=profile_str,
        extraction_data=extraction_str,
        conversation_summary=summary_str,
        user_type=user_type_str,
        connection_type=connection_type,
        primary_goal=primary_goal or connection_type,
        user_name=user_name,
        user_email=user_email,
        linkedin_url=linkedin_url,
    )
    # Restore double braces for ElevenLabs
    formatted = formatted.replace("___DOUBLE_BRACE___", "{{").replace("___CLOSE_BRACE___", "}}")
    
    return formatted


def get_tools_for_user_type(
    user_type: UserType, mode: Literal["voice", "text"]
) -> list:
    """
    Dynamically select tools based on user type.

    Args:
        user_type: The user's type (job_seeker, job_provider, general)
        mode: Either "voice" or "text"

    Returns:
        List of tool functions for the agent
    """
    tools = list(COMMON_TOOLS)  # Always include common tools

    if mode == "voice":
        # Voice mode only needs extraction tools
        return [log_extraction_data, log_arbitrary_data]

    # Text mode gets user-type-specific tools
    if user_type == UserType.JOB_PROVIDER:
        tools.extend(JOB_PROVIDER_TOOLS)
    elif user_type == UserType.JOB_SEEKER:
        tools.extend(JOB_SEEKER_TOOLS)
    # GENERAL users only get common tools

    return tools


def initialize_agent(
    user_type: UserType,
    mode: Literal["voice", "text"],
    model: str = "anthropic:claude-sonnet-4-20250514",
    user_profile: Optional[Dict[str, Any]] = None,
    extraction_data: Optional[Dict[str, Any]] = None,
    conversation_summary: Optional[str] = None,
) -> Agent[AgentDeps, str]:
    """
    Initialize an agent with user-type-specific tools and context.

    Args:
        user_type: The user's type for tool injection
        mode: Either "voice" or "text"
        model: The model to use for the agent
        user_profile: User's profile data for system prompt context
        extraction_data: Extraction data from voice calls
        conversation_summary: Summary of conversation history

    Returns:
        Configured pydantic-ai Agent
    """
    system_prompt = load_system_prompt(
        mode=mode,
        user_profile=user_profile,
        extraction_data=extraction_data,
        conversation_summary=conversation_summary,
    )
    tools = get_tools_for_user_type(user_type, mode)

    print(f"[AGENT] Initializing agent for user_type={user_type}, mode={mode}")
    print(f"[AGENT] Tools loaded: {[t.__name__ for t in tools]}")

    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        deps_type=AgentDeps,
    )
