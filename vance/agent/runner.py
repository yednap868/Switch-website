"""
Main runner for the Vance agent.
Orchestrates agent execution with user context and conversation history.
"""

from typing import List, Literal

from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import KnownModelName

from agent.agent import initialize_agent
from agent.models import AgentDeps, UserType, detect_user_type
from utils.db import (
    get_extraction_data,
    get_user_profile,
    load_conversation,
    save_conversation,
)


def generate_conversation_summary(message_history: List[ModelMessage]) -> str:
    """
    Generate a brief summary of the conversation history.

    Args:
        message_history: List of messages from the conversation

    Returns:
        A brief summary string
    """
    if not message_history:
        return "New conversation"

    # Count messages by type
    user_messages = 0
    assistant_messages = 0

    for msg in message_history:
        kind = getattr(msg, "kind", None)
        if kind == "request":
            user_messages += 1
        elif kind == "response":
            assistant_messages += 1

    if user_messages == 0:
        return "New conversation"

    return f"Ongoing conversation ({user_messages} user messages, {assistant_messages} responses)"


async def runner(
    uid: str,
    input: str,
    mode: Literal["voice", "text"],
    model: KnownModelName = "anthropic:claude-sonnet-4-20250514",
) -> str:
    """
    Main runner for interacting with the agent.
    Manages agent instances, conversation history, and user context.

    Args:
        uid: User's WhatsApp ID (phone number)
        input: User's message text
        mode: Either "voice" or "text"
        model: The model to use for the agent

    Returns:
        Agent's response text
    """
    print(f"[RUNNER] Starting for uid={uid}, mode={mode}, model={model}")
    print(f"[RUNNER] Input: {input[:100]}{'...' if len(input) > 100 else ''}")

    # Fetch user profile
    user_profile = get_user_profile(uid)
    if user_profile:
        print(f"[RUNNER] User profile loaded: name={user_profile.get('name')}")
    else:
        print(f"[RUNNER] No existing profile for uid={uid}")
        user_profile = {}

    # Fetch extraction data (from voice calls)
    extraction_data = get_extraction_data(uid)
    if extraction_data:
        print(
            f"[RUNNER] Extraction data loaded with keys: {list(extraction_data.keys())}"
        )
    else:
        extraction_data = {}

    # Detect user type
    user_type = detect_user_type(user_profile)
    print(f"[RUNNER] Detected user_type: {user_type}")

    # Load conversation history (need it before agent init for summary)
    message_history = load_conversation(uid)
    print(f"[RUNNER] Loaded {len(message_history)} messages from history")

    # Generate conversation summary for system prompt context
    conversation_summary = generate_conversation_summary(message_history)

    # Initialize the agent with user-type-specific tools and context
    agent = initialize_agent(
        user_type=user_type,
        mode=mode,
        model=model,
        user_profile=user_profile,
        extraction_data=extraction_data,
        conversation_summary=conversation_summary,
    )

    # Create agent dependencies
    deps = AgentDeps(
        uid=uid,
        mode=mode,
        profile=user_profile,
        user_type=user_type,
        extraction_data=extraction_data,
    )

    # Run the agent
    print(f"[RUNNER] Running agent...")
    result = await agent.run(input, message_history=message_history, deps=deps)
    print(f"[RUNNER] Agent completed, response length: {len(result.output)} chars")

    # Save the conversation
    save_conversation(uid, result)
    print(f"[RUNNER] Conversation saved")

    return result.output
