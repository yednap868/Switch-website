#!/usr/bin/env python
"""
ElevenLabs Post-Call Webhook Mock Testing Script

This script directly executes the _handle_post_call_webhook() function with user-provided
payload data to test the complete post-call webhook flow without needing a running server.

Usage:
    python test_elevenlabs_webhook.py
    python test_elevenlabs_webhook.py --phone 919876543210
    python test_elevenlabs_webhook.py --template job_provider_ai
    python test_elevenlabs_webhook.py --dry-run
    python test_elevenlabs_webhook.py --phone 918766335252 --template job_provider_ai --yes

Features:
- Interactive CLI prompts for all webhook payload fields
- Automatic payload generation with proper ElevenLabs structure
- Direct execution of webhook function (no server needed)
- Comprehensive debug logging matching webhook handler
- Structured log files saved to logs/webhook_tests/
- Template support for quick testing
- Traces all 8 steps of webhook processing

Requirements:
- User must exist in Firebase with extraction data
- Environment variables must be loaded (Firebase credentials, etc.)
- Run from project root directory

Examples:
    # Interactive mode (prompts for all fields)
    python test_elevenlabs_webhook.py

    # With phone number pre-filled
    python test_elevenlabs_webhook.py --phone 919876543210

    # Using a template
    python test_elevenlabs_webhook.py --template job_provider

    # Dry run (show payload without executing)
    python test_elevenlabs_webhook.py --dry-run --phone 919876543210
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


# Color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


# Load environment variables
from dotenv import load_dotenv

load_dotenv("env_vars.sh")

# Import webhook function
try:
    from api.webhooks import _handle_post_call_webhook
    from utils.db import get_user_profile, get_extraction_data
except ImportError as e:
    print(
        f"{Colors.FAIL}❌ [ERROR] Failed to import required modules: {e}{Colors.ENDC}"
    )
    print(
        f"{Colors.WARNING}Make sure you're running from the project root directory{Colors.ENDC}"
    )
    sys.exit(1)


class WebhookTester:
    """Main webhook testing class."""

    def __init__(self, args):
        self.args = args
        self.log_entries = []
        self.start_time = None
        self.payload = None
        self.user_id = None
        self.test_run_id = str(uuid.uuid4())[:8]

    def log(self, level: str, message: str, emoji: str = ""):
        """Log a message with timestamp and optional emoji."""
        timestamp = datetime.now().isoformat()
        log_entry = {"timestamp": timestamp, "level": level, "message": message}
        self.log_entries.append(log_entry)

        # Color mapping
        color = {
            "info": Colors.OKCYAN,
            "success": Colors.OKGREEN,
            "warning": Colors.WARNING,
            "error": Colors.FAIL,
        }.get(level, "")

        print(f"{color}{emoji} [{level.upper()}] {message}{Colors.ENDC}")

    def print_banner(self):
        """Print welcome banner."""
        print("\n" + "=" * 70)
        print(f"{Colors.BOLD}  ELEVENLABS POST-CALL WEBHOOK TESTER{Colors.ENDC}")
        print(f"  Test Run ID: {self.test_run_id}")
        print(f"  Direct execution of _handle_post_call_webhook() function")
        print("=" * 70 + "\n")

    def print_section(self, title: str):
        """Print section header."""
        print("\n" + "-" * 60)
        print(f"{Colors.BOLD}  {title}{Colors.ENDC}")
        print("-" * 60)

    def load_templates(self):
        """Load test templates from JSON file."""
        template_file = Path("webhook_test_templates.json")
        if template_file.exists():
            with open(template_file, "r") as f:
                return json.load(f)
        return {}

    def prompt_user_id(self) -> str:
        """Prompt for user phone number."""
        if self.args.phone:
            user_id = self.args.phone
            print(f"Using phone number from arguments: {user_id}")
        else:
            user_id = input("Enter user phone number (e.g. 919876543210): ").strip()

        # Validate format
        if not user_id or len(user_id) < 10:
            self.log("error", f"Invalid user_id format: {user_id}", "❌")
            sys.exit(1)

        return user_id

    def display_user_data(self, user_id: str):
        """Display existing user profile and extraction data."""
        self.print_section("USER DATA FROM FIREBASE")

        try:
            profile = get_user_profile(user_id)
            extraction = get_extraction_data(user_id)

            if profile:
                print(f"\n{Colors.OKGREEN}✓{Colors.ENDC} User Profile Found:")
                for key in ["name", "email", "linkedin_url", "user_type"]:
                    if profile.get(key):
                        print(f"  {key}: {profile[key]}")
            else:
                print(f"\n{Colors.WARNING}⚠️  No user profile found{Colors.ENDC}")

            if extraction:
                print(
                    f"\n{Colors.OKGREEN}✓{Colors.ENDC} Extraction Data Found ({len(extraction)} fields):"
                )
                for key, value in list(extraction.items())[:5]:  # Show first 5 fields
                    val_str = (
                        str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
                    )
                    print(f"  {key}: {val_str}")
                if len(extraction) > 5:
                    print(f"  ... and {len(extraction) - 5} more fields")
            else:
                print(f"\n{Colors.FAIL}❌ No extraction data found{Colors.ENDC}")
                print(
                    f"{Colors.WARNING}⚠️  Webhook requires extraction data to function properly{Colors.ENDC}"
                )

                if not self.args.yes:
                    proceed = input("\nContinue anyway? (y/n): ").strip().lower()
                    if proceed != "y":
                        sys.exit(0)

            return profile, extraction

        except Exception as e:
            self.log("error", f"Failed to load user data: {e}", "❌")
            return None, None

    def generate_call_id(self) -> str:
        """Generate a realistic call_id (Twilio format)."""
        timestamp = str(int(time.time()))
        return f"CA{timestamp}{uuid.uuid4().hex[:6]}"

    def generate_conversation_id(self) -> str:
        """Generate a realistic conversation_id (ElevenLabs format)."""
        return f"conv_{uuid.uuid4().hex[:16]}"

    def prompt_payload_fields(self, template_data: dict = None) -> dict:
        """Prompt user for all webhook payload fields."""
        self.print_section("WEBHOOK PAYLOAD FIELDS")

        print(
            f"\n{Colors.OKCYAN}Press Enter to use defaults shown in [brackets]{Colors.ENDC}\n"
        )

        # Generate defaults
        default_call_id = self.generate_call_id()
        default_conv_id = self.generate_conversation_id()
        default_duration = 180

        # Use template if provided
        if template_data:
            print(
                f"{Colors.OKGREEN}✓ Using template: {template_data.get('name', 'Unknown')}{Colors.ENDC}"
            )
            print(f"  User Type: {template_data.get('user_type', 'general')}")
            print(f"  Duration: {template_data.get('duration', default_duration)}s")
            print(
                f"  Transcript length: {len(template_data.get('transcript', ''))} chars\n"
            )

            transcript = template_data.get("transcript", "")
            duration = template_data.get("duration", default_duration)
            call_id = default_call_id
            conversation_id = default_conv_id

            # Parse transcript into agent/user messages (simple split)
            agent_messages = []
            user_messages = []
            if transcript:
                # First sentence is usually user message
                sentences = transcript.split(". ")
                if sentences:
                    user_messages = [sentences[0] + "."] if sentences[0] else []
                    if len(sentences) > 1:
                        agent_messages = [". ".join(sentences[1:])]
        else:
            # Prompt for fields
            call_id_input = input(f"call_id [{default_call_id}]: ").strip()
            call_id = call_id_input if call_id_input else default_call_id

            conv_id_input = input(f"conversation_id [{default_conv_id}]: ").strip()
            conversation_id = conv_id_input if conv_id_input else default_conv_id

            duration_input = input(f"duration (seconds) [{default_duration}]: ").strip()
            duration = int(duration_input) if duration_input else default_duration

            print("\ntranscript (multiline, type 'END' on new line to finish):")
            transcript_lines = []
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                transcript_lines.append(line)
            transcript = "\n".join(transcript_lines)

            agent_messages = []
            user_messages = []

        # Build payload
        payload = {
            "call_id": call_id,
            "conversation_id": conversation_id,
            "duration": duration,
            "transcript": transcript,
            "conversation_transcript": transcript,
            "agent_messages": agent_messages,
            "user_messages": user_messages,
            "key_insights": (
                template_data.get("extraction_fields", {}) if template_data else {}
            ),
            "data": {"user_id": self.user_id},
            "user_id": self.user_id,
            "conversation_initiation_client_data": {
                "dynamic_variables": {"user_id": self.user_id}
            },
        }

        # Optional fields
        if not template_data:
            outcome = input("\noutcome (optional, press Enter to skip): ").strip()
            if outcome:
                payload["outcome"] = outcome

            follow_up = input(
                "follow_up_notes (optional, press Enter to skip): "
            ).strip()
            if follow_up:
                payload["follow_up_notes"] = follow_up

            quality = input(
                "quality_score (optional integer, press Enter to skip): "
            ).strip()
            if quality:
                payload["quality_score"] = int(quality)
        else:
            # Add default optional fields for templates
            payload["outcome"] = "completed"
            payload["quality_score"] = 8

        return payload

    def display_payload(self, payload: dict):
        """Display payload in formatted JSON."""
        self.print_section("PAYLOAD PREVIEW")
        print(f"\n{json.dumps(payload, indent=2)}\n")

    async def execute_webhook(self, payload: dict):
        """Execute the webhook function and capture output."""
        self.print_section("EXECUTING WEBHOOK FUNCTION")

        self.start_time = time.time()
        self.log("info", f"Calling _handle_post_call_webhook(payload)", "📞")

        try:
            # Execute webhook function
            await _handle_post_call_webhook(payload)

            elapsed = time.time() - self.start_time
            self.log("success", f"Webhook execution completed in {elapsed:.2f}s", "✅")
            return True

        except Exception as e:
            elapsed = time.time() - self.start_time
            self.log(
                "error", f"Webhook execution failed after {elapsed:.2f}s: {e}", "❌"
            )
            import traceback

            traceback.print_exc()
            return False

    def save_log_file(self, success: bool):
        """Save structured log file to logs/webhook_tests/."""
        log_dir = Path("logs/webhook_tests")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"run_{timestamp_str}_{self.test_run_id}.json"

        elapsed = time.time() - self.start_time if self.start_time else 0

        log_data = {
            "test_run_id": self.test_run_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": self.user_id,
            "success": success,
            "duration_seconds": round(elapsed, 2),
            "payload": self.payload,
            "logs": self.log_entries,
        }

        with open(log_file, "w") as f:
            json.dump(log_data, f, indent=2)

        self.log("info", f"Log saved to: {log_file}", "💾")

    def print_summary(self, success: bool):
        """Print execution summary."""
        self.print_section("TEST SUMMARY")

        elapsed = time.time() - self.start_time if self.start_time else 0

        print(f"\n  Test Run ID: {self.test_run_id}")
        print(f"  User ID: {self.user_id}")
        print(f"  Duration: {elapsed:.2f}s")
        print(
            f"  Status: {Colors.OKGREEN}✓ SUCCESS{Colors.ENDC}"
            if success
            else f"  Status: {Colors.FAIL}✗ FAILED{Colors.ENDC}"
        )
        print(f"  Log entries: {len(self.log_entries)}")
        print()

    async def run(self):
        """Main execution flow."""
        self.print_banner()

        # Step 1: Get user ID
        self.user_id = self.prompt_user_id()
        self.log("info", f"Testing webhook for user: {self.user_id}", "👤")

        # Step 2: Display user data
        profile, extraction = self.display_user_data(self.user_id)

        # Step 3: Get payload fields
        template_data = None
        if self.args.template:
            templates = self.load_templates()
            template_data = templates.get(self.args.template)
            if not template_data:
                self.log("warning", f"Template '{self.args.template}' not found", "⚠️")

        self.payload = self.prompt_payload_fields(template_data)

        # Step 4: Display payload
        self.display_payload(self.payload)

        # Step 5: Confirmation
        if self.args.dry_run:
            print(f"\n{Colors.WARNING}DRY RUN - Not executing webhook{Colors.ENDC}")
            return

        if not self.args.yes:
            confirm = (
                input(f"\n{Colors.BOLD}Execute webhook? (y/n): {Colors.ENDC}")
                .strip()
                .lower()
            )
            if confirm != "y":
                print("Aborted.")
                return

        # Step 6: Execute webhook
        success = await self.execute_webhook(self.payload)

        # Step 7: Save logs
        self.save_log_file(success)

        # Step 8: Print summary
        self.print_summary(success)

        # Step 9: Offer to run again (skip in --yes mode)
        if not self.args.yes:
            again = (
                input(f"\n{Colors.BOLD}Run another test? (y/n): {Colors.ENDC}")
                .strip()
                .lower()
            )
            if again == "y":
                # Reset state
                self.log_entries = []
                self.start_time = None
                self.payload = None
                self.test_run_id = str(uuid.uuid4())[:8]
                await self.run()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ElevenLabs Post-Call Webhook Tester")
    parser.add_argument("--phone", help="User phone number (e.g. 919876543210)")
    parser.add_argument(
        "--template", help="Use predefined template (job_provider, job_seeker, general)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show payload without executing"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts (one-shot mode)",
    )
    args = parser.parse_args()

    tester = WebhookTester(args)

    try:
        asyncio.run(tester.run())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Fatal error: {e}{Colors.ENDC}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
