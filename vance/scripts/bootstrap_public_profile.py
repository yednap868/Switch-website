#!/usr/bin/env python3
"""
Bootstrap a public candidate profile for an existing user.

Usage (from repo root):
    uv run python -m scripts.bootstrap_public_profile --user-id 919172559086

This will:
  1. Load the user's extraction data from Firestore (`extractions/{user_id}`)
  2. Call VoiceExtractionService._sync_job_seeker_profile(...) to:
       - Create/update `user_profiles/{user_id}` with a canonical profile document
       - Generate a unique public slug and store it in `public_profiles/{slug}`
       - Upsert a vectorized profile into Qdrant `UserProfiles` collection
  3. Print the assigned slug and the public URL path.
"""

import argparse
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Optional in production, safe to ignore if missing
    pass

from services.voice_extraction_service import voice_extraction_service  # type: ignore
from utils.db import get_extraction_data


def bootstrap_public_profile(user_id: str) -> None:
    """Create a public candidate profile + slug for the given user ID."""
    print(f"🔍 Bootstrapping public profile for user_id={user_id}")

    # 1. Load extraction data – this should already exist if onboarding call completed
    extraction = get_extraction_data(user_id)
    if not extraction:
        print(
            f"❌ No extraction data found for user '{user_id}'. "
            f"Make sure the onboarding call has completed and extraction is saved."
        )
        sys.exit(1)

    print(f"✅ Found extraction data with {len(extraction.keys())} fields")

    # 2. Call the same internal helper used by the voice onboarding flow
    voice_extraction_service._sync_job_seeker_profile(  # type: ignore[attr-defined]
        user_id=user_id,
        extraction_data=extraction,
    )

    print(
        "\n✅ Public profile bootstrap completed.\n"
        "If this is the first time for this user, a new slug was generated and stored in:\n"
        "  - Firestore:  public_profiles/{slug} → { user_id, active, ... }\n"
        "  - Firestore:  user_profiles/{user_id} → includes 'slug' and 'avatar_url'\n"
        "  - Qdrant:     UserProfiles collection with complete extraction_data\n"
    )
    print(
        "You can now open the public profile at:\n"
        "  https://www.vance.so/{slug}\n"
        "(Replace {slug} with the value stored on the user_profiles document.)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap a public candidate profile for a given user ID"
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="User ID / WhatsApp ID (e.g., 919172559086)",
    )

    args = parser.parse_args()
    bootstrap_public_profile(args.user_id)


if __name__ == "__main__":
    main()


