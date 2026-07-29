#!/usr/bin/env python
"""
CLI Testing for Post-Call Webhook Flow

Usage:
    python cli_test_postcall.py
    python cli_test_postcall.py --phone 919876543210

Simulates the ElevenLabs post-call webhook to test:
1. Dynamic profile sending decision (should_send_profiles_to_user)
2. Intent classification
3. Profile matching for job providers
4. Correct message sending behavior

All data is read from Firebase, so the user must have existing extraction data.
"""

import argparse
import asyncio
import json
import time
import traceback

# Load environment variables
from dotenv import load_dotenv

load_dotenv("env_vars.sh")

from services.claude_profile_service import claude_profile_service
from utils.db import get_extraction_data, get_user_profile, save_data_merge


def _format_profile_local(profile, index: int) -> str:
    """
    Local formatter mirroring production WhatsApp formatting for job seeker profiles.
    """
    if hasattr(profile, "__dict__"):
        p = profile.__dict__
    else:
        p = profile

    lines = [f"*Candidate {index}: {p.get('name', 'Unknown')}*"]
    if p.get("target_role"):
        lines.append(f"🎯 Target Role: {p['target_role']}")
    if p.get("core_skills"):
        lines.append(f"💻 Skills: {p['core_skills']}")
    if p.get("work_experience"):
        lines.append(f"📊 Experience: {p['work_experience']}")
    if p.get("current_location"):
        lines.append(f"📍 Location: {p['current_location']}")
    if p.get("salary_expectations"):
        lines.append(f"💰 Expected: {p['salary_expectations']}")
    if p.get("linkedin_url"):
        lines.append(f"🔗 LinkedIn: {p['linkedin_url']}")

    match_score = p.get("match_score")
    if match_score:
        lines.append(f"\n_Match Score: {match_score:.0%}_")

    match_reason = p.get("match_reason", "")
    if match_reason:
        reason_display = (
            match_reason[:150] + "..." if len(match_reason) > 150 else match_reason
        )
        lines.append(f"_Why: {reason_display}_")

    return "\n".join(lines)


# Map fine-grained intents to high-level user types expected by the flows
def normalize_user_type(intent: str) -> str:
    hiring_intents = {"hiring_need", "recruiter_need", "freelancer_need", "sales_need"}
    job_seeker_intents = {"job_seeker_need"}
    if intent in hiring_intents:
        return "job_provider"
    if intent in job_seeker_intents:
        return "job_seeker"
    return "general"


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 70)
    print("  POST-CALL WEBHOOK TEST")
    print("  Tests the post-call flow without actual WhatsApp/ElevenLabs")
    print("=" * 70 + "\n")


def print_section(title: str):
    """Print section header."""
    print("\n" + "-" * 60)
    print(f"  {title}")
    print("-" * 60)


def print_user_data(uid: str):
    """Print current user profile and extraction data."""
    profile = get_user_profile(uid)
    extraction = get_extraction_data(uid)

    print_section("USER PROFILE")

    if profile:
        print("\nBasic Info:")
        for key in ["name", "email", "linkedin_url", "primary_goal", "user_type"]:
            value = profile.get(key)
            if value:
                print(f"  {key}: {value}")
    else:
        print("  (No profile found)")

    print_section("EXTRACTION DATA")

    if extraction and isinstance(extraction, dict):
        print(f"\nFound {len(extraction)} fields:")
        for key, value in extraction.items():
            if value and key != "arbitrary":
                if isinstance(value, list):
                    print(f"  {key}: {', '.join(str(v) for v in value)}")
                else:
                    val_str = str(value)
                    if len(val_str) > 100:
                        val_str = val_str[:100] + "..."
                    print(f"  {key}: {val_str}")
    else:
        print("  (No extraction data found)")
        print("  ⚠️  Post-call webhook requires extraction data to function properly")

    return profile, extraction


def test_intent_classification(extraction_data: dict) -> str:
    """Test intent classification."""
    print_section("INTENT CLASSIFICATION")

    if not extraction_data or not isinstance(extraction_data, dict):
        print("  ❌ No extraction data available for classification")
        return "general"

    # Build extraction text like the webhook does
    extraction_text_parts = []
    for key, value in extraction_data.items():
        if value:
            value_str = str(value).strip()
            if value_str and value_str.lower() not in ["n/a", "none", "null", ""]:
                extraction_text_parts.append(value_str)

    extraction_text = " ".join(extraction_text_parts)

    if not extraction_text.strip():
        print("  ❌ Extraction text is empty")
        return "general"

    print(f"\n  Extraction text length: {len(extraction_text)} chars")
    print(f"  First 200 chars: {extraction_text[:200]}...")

    print("\n  Calling claude_profile_service.classify_intent()...")
    start_time = time.time()

    try:
        intent = claude_profile_service.classify_intent(extraction_text)
        elapsed = time.time() - start_time
        print(f"  ✅ Intent classified in {elapsed:.2f}s")
        print(f"  📋 Result: {intent}")

        # Strong heuristic overrides when Claude is unsure
        if intent == "general":
            text_lower = extraction_text.lower()
            hiring_fields = any(
                extraction_data.get(k)
                for k in [
                    "job_title",
                    "required_skills",
                    "experience_level",
                    "salary_budget",
                    "work_model",
                    "hiring_urgency",
                ]
            )
            job_seeker_fields = any(
                extraction_data.get(k)
                for k in ["target_role", "core_skills", "work_experience"]
            )

            hiring_signals = any(
                kw in text_lower
                for kw in [
                    "hiring",
                    "hire",
                    "recruit",
                    "looking to hire",
                    "job opening",
                    "role open",
                ]
            )
            job_seeker_signals = any(
                kw in text_lower
                for kw in [
                    "looking for a job",
                    "seeking a role",
                    "job seeker",
                    "need a job",
                    "apply",
                    "interviewing",
                ]
            )

            if hiring_fields or hiring_signals:
                print("  ℹ️  Overriding intent to hiring_need based on fields/keywords.")
                return "hiring_need"
            if job_seeker_fields or job_seeker_signals:
                print(
                    "  ℹ️  Overriding intent to job_seeker_need based on fields/keywords."
                )
                return "job_seeker_need"

        return intent
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return "general"


def test_profile_decision(extraction_data: dict) -> tuple[bool, str]:
    """Test dynamic profile sending decision."""
    print_section("PROFILE SENDING DECISION")

    if not extraction_data or not isinstance(extraction_data, dict):
        print("  ❌ No extraction data available for decision")
        return False, "No extraction data"

    print("\n  Calling claude_profile_service.should_send_profiles_to_user()...")
    start_time = time.time()

    try:
        should_send, reason = claude_profile_service.should_send_profiles_to_user(
            extraction_data=extraction_data
        )
        elapsed = time.time() - start_time

        print(f"  ✅ Decision made in {elapsed:.2f}s")
        print(f"\n  📋 Should send profiles: {should_send}")
        print(f"  📋 Reason: {reason}")

        if should_send:
            print("\n  ✅ This user WILL receive candidate profiles")
            print("     (They are identified as actively hiring)")
        else:
            print("\n  ℹ️  This user will NOT receive candidate profiles")
            print("     (They are not identified as hiring)")

        return should_send, reason

    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return False, f"Error: {e}"


def test_profile_matching(extraction_data: dict, uid: str = None):
    """Test profile matching for job providers."""
    print_section("PROFILE MATCHING (Job Provider Flow)")

    try:
        from services.hybrid_matching_service import hybrid_matching_service

        print("\n  Calling hybrid_matching_service.find_job_seeker_matches()...")
        start_time = time.time()

        matched_profiles = hybrid_matching_service.find_job_seeker_matches(
            job_provider_data=extraction_data,
            limit=3,
            min_score=0.6,
            job_provider_uid=uid,
        )

        elapsed = time.time() - start_time
        print(f"  ✅ Matching completed in {elapsed:.2f}s")

        if matched_profiles:
            print(f"\n  Found {len(matched_profiles)} matching candidates:")
            for i, profile in enumerate(matched_profiles, 1):
                if hasattr(profile, "__dict__"):
                    p = profile.__dict__
                elif hasattr(profile, "_asdict"):
                    p = profile._asdict()
                else:
                    p = profile

                name = p.get("name", "Unknown")
                score = p.get("match_score", 0)
                reason = p.get("match_reason", "")[:50]
                print(f"\n  {i}. {name}")
                print(f"     Score: {score}")
                print(f"     Reason: {reason}...")
        else:
            print("\n  ℹ️  No matching candidates found")
            print("     (This could be due to lack of job seekers in database)")

        return matched_profiles

    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()
        return []


def simulate_webhook_messages(uid: str, should_send: bool, matched_profiles: list):
    """Simulate what messages would be sent."""
    print_section("SIMULATED WHATSAPP MESSAGES")

    # Use production formatter if available; else local formatter
    formatter = None
    try:
        from api.webhooks import _format_job_seeker_profile_message as prod_formatter

        formatter = prod_formatter
    except Exception:
        formatter = _format_profile_local

    if should_send and matched_profiles:
        print("\n  [Would send to user]:")
        print(
            f"  📱 'Great news! I found {len(matched_profiles)} candidates for your role:'\n"
        )
        for i, profile in enumerate(matched_profiles, 1):
            if formatter:
                try:
                    msg = formatter(profile, i)
                except Exception:
                    msg = None
            else:
                msg = None

            if not msg:
                msg = _format_profile_local(profile, i)

            for line in msg.splitlines():
                print(f"  📱 {line}")
            print()
        print("  📱 'Which candidate interests you most?'")

    elif should_send and not matched_profiles:
        print("\n  [Would send to user]:")
        print("  📱 'Matching you with candidates now - profiles coming shortly!'")
        print("  ⚠️  But no candidates were found to send")

    else:
        print("\n  [No profiles message sent]")
        print("  ℹ️  User is not a job provider, so no profiles are sent")
        print("  ℹ️  This is correct behavior - avoids misleading messages")


async def run_full_test(uid: str):
    """Run the complete post-call webhook test."""
    print(f"\n🔍 Testing post-call flow for user: {uid}\n")

    # Step 1: Get user data
    profile, extraction = print_user_data(uid)

    if not extraction:
        print("\n" + "=" * 70)
        print("  ⚠️  CANNOT PROCEED - NO EXTRACTION DATA")
        print("  Run a voice call or manually add extraction data first")
        print("=" * 70 + "\n")
        return

    # Step 2: Test intent classification
    intent = test_intent_classification(extraction)
    user_type = normalize_user_type(intent)

    # Step 3: Test profile sending decision
    should_send, reason = test_profile_decision(extraction)

    # Step 4: If should send, test profile matching
    matched_profiles = []
    if should_send:
        matched_profiles = test_profile_matching(extraction, uid=uid)

    # Step 5: Simulate messages
    simulate_webhook_messages(uid, should_send, matched_profiles)

    # Summary
    print_section("TEST SUMMARY")
    print(f"\n  User ID: {uid}")
    print(f"  Intent: {intent}")
    print(f"  User type (coarse): {user_type}")
    print(f"  Should send profiles: {should_send}")
    print(f"  Decision reason: {reason}")
    if should_send:
        print(f"  Matched candidates: {len(matched_profiles)}")

    # Check for issues
    print_section("DIAGNOSTICS")

    issues = []

    if not extraction:
        issues.append("No extraction data found")

    if intent == "general":
        issues.append("Intent classified as 'general' - may need more specific data")

    if should_send and not matched_profiles:
        issues.append("Marked as job provider but no candidates found")

    if not should_send and intent == "hiring_need":
        issues.append(
            "Intent is hiring_need but decision says don't send - inconsistency"
        )

    if issues:
        print("\n  ⚠️  Potential issues detected:")
        for issue in issues:
            print(f"     - {issue}")
    else:
        print("\n  ✅ No issues detected - flow looks correct")

    print("\n" + "=" * 70 + "\n")


def print_help():
    """Print available commands."""
    print("\n" + "=" * 50)
    print("COMMANDS")
    print("=" * 50)
    print("  /test           - Run full post-call webhook test")
    print("  /intent         - Test intent classification only")
    print("  /decision       - Test profile sending decision only")
    print("  /match          - Test profile matching only")
    print("  /data           - Show user profile and extraction data")
    print("  /set-extraction - Manually set mock extraction data")
    print("  /quit, /exit    - Exit")
    print("  /help           - Show this help")
    print("=" * 50 + "\n")


def set_mock_extraction(uid: str):
    """Set mock extraction data for testing."""
    print("\nChoose a mock extraction scenario:")
    print("  1. Job Provider (Hiring for backend role)")
    print("  2. Job Seeker (Looking for frontend job)")
    print("  3. Investor (Looking to invest)")
    print("  4. Founder (Looking for co-founder)")
    print("  5. General (Networking)")

    choice = input("\nEnter choice (1-5): ").strip()

    mock_data = {}

    if choice == "1":
        mock_data = {
            "urgent_needs": "We need to hire a senior backend engineer urgently. Looking for someone with Python and distributed systems experience.",
            "the_story": "I'm the CTO at a Series A startup. We're scaling rapidly and need to grow the engineering team.",
            "current_focus": "Building out the backend infrastructure and hiring key engineers",
            "job_title": "Senior Backend Engineer",
            "company": "TechStartup Inc",
            "team_size": "15 engineers",
        }
    elif choice == "2":
        mock_data = {
            "urgent_needs": "I'm actively looking for a frontend developer position. React and TypeScript expertise.",
            "the_story": "5 years of experience in frontend development. Previously at a FAANG company.",
            "current_focus": "Finding a new role at an innovative startup",
            "target_role": "Senior Frontend Developer",
            "skills": "React, TypeScript, Next.js, Node.js",
            "experience_years": "5",
        }
    elif choice == "3":
        mock_data = {
            "urgent_needs": "Looking to invest in early-stage B2B SaaS startups. Check sizes $100k-500k.",
            "the_story": "Angel investor with 10+ years in tech. Previously founded and exited a startup.",
            "current_focus": "Building a portfolio of AI-first B2B companies",
            "investment_thesis": "B2B SaaS with strong unit economics",
        }
    elif choice == "4":
        mock_data = {
            "urgent_needs": "Looking for a technical co-founder for my AI startup idea",
            "the_story": "Business background, 8 years in product management",
            "current_focus": "Validating the market and finding the right technical partner",
            "startup_idea": "AI-powered customer support automation",
        }
    elif choice == "5":
        mock_data = {
            "urgent_needs": "Just networking and exploring opportunities",
            "the_story": "Consultant helping companies with digital transformation",
            "current_focus": "Building relationships in the tech ecosystem",
        }
    else:
        print("Invalid choice")
        return

    try:
        save_data_merge(uid, "extractions", mock_data)
        print(f"\n✅ Mock extraction data saved for {uid}")
        print(
            f"   Scenario: {['', 'Job Provider', 'Job Seeker', 'Investor', 'Founder', 'General'][int(choice)]}"
        )
    except Exception as e:
        print(f"\n❌ Error saving mock data: {e}")


async def main():
    """Main CLI loop."""
    parser = argparse.ArgumentParser(description="Post-Call Webhook Test")
    parser.add_argument("--phone", "-p", help="WhatsApp phone number to test")
    args = parser.parse_args()

    print_banner()

    # Get WhatsApp number
    if args.phone:
        wa_number = args.phone
    else:
        wa_number = input("Enter WhatsApp number (user ID): ").strip()

    if not wa_number:
        wa_number = f"test_user_{int(time.time())}"

    # Clean up phone number
    wa_number = wa_number.replace("+", "").replace(" ", "").replace("-", "")

    print(f"\nTesting user: {wa_number}")

    # Check for existing data
    profile = get_user_profile(wa_number)
    extraction = get_extraction_data(wa_number)

    if profile:
        print(f"✅ Found user profile: {profile.get('name', 'Unknown')}")
    else:
        print("⚠️  No user profile found")

    if extraction:
        print(f"✅ Found extraction data: {len(extraction)} fields")
    else:
        print("⚠️  No extraction data found - use /set-extraction to add mock data")

    print_help()

    while True:
        try:
            user_input = input("\nCommand: ").strip()

            if not user_input:
                continue

            cmd = user_input.lower().split()[0]

            if cmd in ("/quit", "/exit", "/q"):
                print("\nGoodbye!")
                break

            elif cmd == "/test":
                await run_full_test(wa_number)

            elif cmd == "/intent":
                extraction = get_extraction_data(wa_number)
                test_intent_classification(extraction)

            elif cmd == "/decision":
                extraction = get_extraction_data(wa_number)
                test_profile_decision(extraction)

            elif cmd == "/match":
                extraction = get_extraction_data(wa_number)
                test_profile_matching(extraction)

            elif cmd == "/data":
                print_user_data(wa_number)

            elif cmd == "/set-extraction":
                set_mock_extraction(wa_number)

            elif cmd == "/help":
                print_help()

            else:
                print(f"Unknown command: {cmd}. Type /help for available commands.")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
