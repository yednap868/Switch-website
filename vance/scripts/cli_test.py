#!/usr/bin/env python
"""
CLI Testing Loop for Vance Agent

Usage:
    python cli_test.py
    python cli_test.py --phone 919876543210

Simulates WhatsApp conversation flow for testing without actual WhatsApp integration.
All data is saved to Firebase just like production, so you can test full workflows.
"""

import argparse
import asyncio
import time
import traceback

# Load environment variables
from dotenv import load_dotenv

load_dotenv("env_vars.sh")

from agent.agent import get_tools_for_user_type
from agent.models import detect_user_type
from agent.runner import runner
from utils.db import (
    get_extraction_data,
    get_user_profile,
    load_conversation,
    save_data_merge,
)
from utils.firebase_init import fs


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 60)
    print("  VANCE CLI TESTING LOOP")
    print("  Simulates WhatsApp conversation for testing")
    print("=" * 60 + "\n")


def print_response(response: str):
    """Format and print agent response."""
    print("\n" + "-" * 50)
    print("VANCE:")
    print("-" * 50)
    # Handle multi-line responses nicely
    for line in response.split("\n"):
        print(f"  {line}")
    print("-" * 50 + "\n")


def print_profile(uid: str):
    """Print current user profile."""
    profile = get_user_profile(uid)
    extraction = get_extraction_data(uid)

    print("\n" + "=" * 50)
    print("USER PROFILE")
    print("=" * 50)

    if profile:
        print("\nBasic Info:")
        for key in ["name", "email", "linkedin_url", "primary_goal", "user_type"]:
            if profile.get(key):
                print(f"  {key}: {profile[key]}")
    else:
        print("  (No profile found)")

    if extraction:
        print("\nExtraction Data:")
        for key, value in extraction.items():
            if value and key != "arbitrary":
                if isinstance(value, list):
                    print(f"  {key}: {', '.join(value)}")
                else:
                    print(f"  {key}: {str(value)[:100]}")
    else:
        print("\n  (No extraction data)")

    print("=" * 50 + "\n")


def print_tools(uid: str):
    """Print available tools for user's type."""
    profile = get_user_profile(uid) or {}
    user_type = detect_user_type(profile)

    print("\n" + "=" * 50)
    print(f"AVAILABLE TOOLS (user_type: {user_type.value})")
    print("=" * 50)

    tools = get_tools_for_user_type(user_type, "text")
    for tool in tools:
        doc = tool.__doc__ or ""
        first_line = doc.split("\n")[0].strip() if doc else "No description"
        print(f"  - {tool.__name__}: {first_line}")

    print("=" * 50 + "\n")


def print_help():
    """Print available commands."""
    print("\n" + "=" * 50)
    print("COMMANDS")
    print("=" * 50)
    print("  /quit, /exit    - Exit the testing loop")
    print("  /profile        - Show current user profile")
    print("  /tools          - List available tools")
    print("  /type <type>    - Set user type (job_seeker, job_provider, general)")
    print("  /reset          - Clear profile data (start fresh)")
    print("  /history        - Show conversation history")
    print("  /help           - Show this help message")
    print("=" * 50 + "\n")


def reset_user(uid: str):
    """Reset user data for fresh start."""
    try:
        # Delete user document
        fs.collection("users").document(uid).delete()
        fs.collection("extractions").document(uid).delete()

        # Delete conversation history
        conv_ref = fs.collection("conversations").document(uid)
        messages = conv_ref.collection("messages").stream()
        for msg in messages:
            msg.reference.delete()
        conv_ref.delete()

        print(f"Reset complete for {uid}")
    except Exception as e:
        print(f"Error resetting user: {e}")


def show_history(uid: str):
    """Show conversation history."""
    try:
        history = load_conversation(uid)

        if not history:
            print("\n  (No conversation history)")
            return

        print("\n" + "=" * 50)
        print("CONVERSATION HISTORY")
        print("=" * 50)

        for msg in history[-10:]:  # Show last 10 messages
            kind = msg.get("kind", "unknown")
            parts = msg.get("parts", [])

            if kind == "request":
                for part in parts:
                    if isinstance(part, dict) and part.get("content"):
                        print(f"\n  YOU: {part['content']}")
            elif kind == "response":
                for part in parts:
                    if isinstance(part, dict):
                        if part.get("content"):
                            print(f"\n  VANCE: {part['content'][:200]}...")
                        elif part.get("tool_name"):
                            print(f"\n  [Tool: {part['tool_name']}]")

        print("=" * 50 + "\n")
    except Exception as e:
        print(f"Error loading history: {e}")


async def main():
    """Main CLI loop."""
    parser = argparse.ArgumentParser(description="Vance CLI Testing Loop")
    parser.add_argument("--phone", "-p", help="WhatsApp phone number to simulate")
    args = parser.parse_args()

    print_banner()

    # Get WhatsApp number
    if args.phone:
        wa_number = args.phone
    else:
        wa_number = input("Enter WhatsApp number (for user identification): ").strip()

    if not wa_number:
        wa_number = f"test_user_{int(time.time())}"

    # Clean up phone number
    wa_number = wa_number.replace("+", "").replace(" ", "").replace("-", "")

    print(f"\nTesting as user: {wa_number}")

    # Check for existing profile
    profile = get_user_profile(wa_number)
    if profile:
        name = profile.get("name", "Unknown")
        user_type = profile.get("user_type", detect_user_type(profile).value)
        goal = profile.get("primary_goal", "Not set")
        print(f"Found existing profile: {name}")
        print(f"  Type: {user_type}")
        print(f"  Goal: {goal}")
    else:
        print("New user - starting fresh conversation")

    print_help()

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd_parts = user_input.lower().split()
                cmd = cmd_parts[0]

                if cmd in ("/quit", "/exit", "/q"):
                    print("\nGoodbye!")
                    break

                elif cmd == "/profile":
                    print_profile(wa_number)
                    continue

                elif cmd == "/tools":
                    print_tools(wa_number)
                    continue

                elif cmd == "/type":
                    if len(cmd_parts) > 1:
                        new_type = cmd_parts[1]
                        if new_type in ("job_seeker", "job_provider", "general"):
                            save_data_merge(wa_number, "users", {"user_type": new_type})
                            print(f"User type set to: {new_type}")
                        else:
                            print(
                                "Invalid type. Use: job_seeker, job_provider, or general"
                            )
                    else:
                        print("Usage: /type <job_seeker|job_provider|general>")
                    continue

                elif cmd == "/reset":
                    confirm = input("Are you sure? This will delete all data. (y/n): ")
                    if confirm.lower() == "y":
                        reset_user(wa_number)
                    continue

                elif cmd == "/history":
                    show_history(wa_number)
                    continue

                elif cmd == "/help":
                    print_help()
                    continue

                else:
                    print(f"Unknown command: {cmd}. Type /help for available commands.")
                    continue

            # Process through agent
            print("\nProcessing...")
            start_time = time.time()

            try:
                response = await runner(
                    uid=wa_number,
                    input=user_input,
                    mode="text",
                    model="anthropic:claude-sonnet-4-20250514",
                )

                elapsed = time.time() - start_time
                print(f"(Response time: {elapsed:.2f}s)")

                print_response(response)

            except Exception as e:
                print(f"\nError from agent: {e}")
                traceback.print_exc()

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
