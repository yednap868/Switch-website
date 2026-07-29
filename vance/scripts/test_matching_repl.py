#!/usr/bin/env python3
"""
Interactive REPL for testing the hybrid matching service.

Usage:
    uv run python test_matching_repl.py

Type your job requirements and see matched candidates in real-time.
"""

import asyncio
import json
import sys
from dotenv import load_dotenv

load_dotenv("env_vars.sh")

from services.hybrid_matching_service import HybridMatchingService


def print_banner():
    print("\n" + "=" * 70)
    print("  HYBRID MATCHING SERVICE - INTERACTIVE TESTER")
    print("=" * 70)
    print(
        """
This REPL lets you test job seeker matching with custom queries.

EXAMPLE INPUT (paste this to test):
{
    "urgent_needs": "Looking for a senior Python developer with AWS experience",
    "job_title": "Senior Backend Engineer",
    "required_skills": "Python, AWS, FastAPI, PostgreSQL",
    "experience_level": "5+ years",
    "work_model": "Remote",
    "office_location": "Bangalore"
}

COMMANDS:
  paste JSON   - Full structured query (like above)
  free text    - Just type requirements naturally
  /example     - Show the example again
  /fields      - List all supported fields
  /limit N     - Set max results (default: 3)
  /min N.N     - Set min score threshold (default: 0.5)
  /quit        - Exit

"""
    )


def print_example():
    print(
        """
EXAMPLE JSON:
{
    "urgent_needs": "Looking for a senior Python developer with AWS experience",
    "job_title": "Senior Backend Engineer",
    "required_skills": "Python, AWS, FastAPI, PostgreSQL",
    "experience_level": "5+ years",
    "work_model": "Remote",
    "office_location": "Bangalore"
}

Or just type naturally:
> I need a React developer with 3 years experience in Bangalore
"""
    )


def print_fields():
    print(
        """
SUPPORTED FIELDS:
  Structured (high priority):
    - job_title          : "Senior Backend Engineer"
    - required_skills    : "Python, AWS, Docker"
    - experience_level   : "5+ years" or "Senior"
    - office_location    : "Bangalore"
    - work_model         : "Remote", "Hybrid", "On-site"
    - role_description   : Brief description of the role
    - salary_budget      : "20-30 LPA"
    - hiring_urgency     : "Immediate", "This month"

  Unstructured (fallback):
    - urgent_needs       : Natural language description
"""
    )


def print_matches(profiles, elapsed):
    if not profiles:
        print("\n  No matches found.")
        return

    print(f"\n  Found {len(profiles)} matches in {elapsed:.2f}s:\n")
    print("-" * 60)

    for i, p in enumerate(profiles, 1):
        print(f"\n  [{i}] {p.name}")
        print(f"      UID: {p.uid}")
        print(f"      Score: {p.match_score:.2f}")
        if p.target_role:
            print(f"      Target Role: {p.target_role}")
        if p.core_skills:
            skills = (
                p.core_skills[:60] + "..." if len(p.core_skills) > 60 else p.core_skills
            )
            print(f"      Skills: {skills}")
        if p.work_experience:
            print(f"      Experience: {p.work_experience}")
        if p.current_location:
            print(f"      Location: {p.current_location}")
        if p.match_reason:
            reason = (
                p.match_reason[:80] + "..."
                if len(p.match_reason) > 80
                else p.match_reason
            )
            print(f"      Reason: {reason}")

    print("\n" + "-" * 60)


async def run_match(service, query_data, limit, min_score):
    import time

    start = time.time()

    print(f"\n  Searching with limit={limit}, min_score={min_score}...")

    profiles = await service.find_job_seeker_matches(
        job_provider_data=query_data,
        limit=limit,
        min_score=min_score,
    )

    elapsed = time.time() - start
    print_matches(profiles, elapsed)


def parse_input(user_input):
    """Parse user input - either JSON or natural language."""
    stripped = user_input.strip()

    # Try to parse as JSON
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as e:
            print(f"  Invalid JSON: {e}")
            return None

    # Treat as natural language -> put in urgent_needs
    return {"urgent_needs": stripped}


async def main():
    print_banner()

    service = HybridMatchingService()
    print("  Service initialized.\n")

    limit = 3
    min_score = 0.5

    while True:
        try:
            print(f"\n[limit={limit}, min={min_score}]")
            user_input = input("> ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input == "/quit" or user_input == "/q":
                print("  Bye!")
                break
            elif user_input == "/example":
                print_example()
                continue
            elif user_input == "/fields":
                print_fields()
                continue
            elif user_input.startswith("/limit"):
                try:
                    limit = int(user_input.split()[1])
                    print(f"  Limit set to {limit}")
                except (IndexError, ValueError):
                    print("  Usage: /limit N")
                continue
            elif user_input.startswith("/min"):
                try:
                    min_score = float(user_input.split()[1])
                    print(f"  Min score set to {min_score}")
                except (IndexError, ValueError):
                    print("  Usage: /min 0.5")
                continue

            # Parse and run query
            query_data = parse_input(user_input)
            if query_data:
                print(f"  Query: {json.dumps(query_data, indent=2)[:200]}...")
                await run_match(service, query_data, limit, min_score)

        except KeyboardInterrupt:
            print("\n  Interrupted. Type /quit to exit.")
        except EOFError:
            print("\n  Bye!")
            break
        except Exception as e:
            print(f"  Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
