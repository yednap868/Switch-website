#!/usr/bin/env python3
"""
Test script to verify ElevenLabs audio fetching locally.

Usage:
    uv run python -m scripts.test_audio_fetch --user-id 918368828660
"""

import argparse
import asyncio
import sys

from services.profile_audio_service import profile_audio_service
from utils.db import fs


async def test_audio_fetch(user_id: str) -> None:
    """Test fetching audio from ElevenLabs API for a given user."""
    print(f"🧪 Testing audio fetch for user_id={user_id}")

    # Get the most recent conversation_id from user_calls
    print("\n--- Step 1: Finding conversation_id ---")
    root = fs.collection("user_calls").document(user_id)
    calls = root.collection("calls").order_by("created_at", direction="DESCENDING").limit(1)
    docs = list(calls.stream())

    if not docs:
        print(f"❌ No call logs found for {user_id}")
        sys.exit(1)

    call_doc = docs[0]
    call_data = call_doc.to_dict() or {}
    conversation_id = call_data.get("conversation_id") or call_data.get("call_id")

    if not conversation_id:
        print(f"❌ No conversation_id found in call log: {call_data}")
        sys.exit(1)

    print(f"✅ Found conversation_id: {conversation_id}")

    # Test fetching audio from API
    print("\n--- Step 2: Fetching audio from ElevenLabs API ---")
    audio_url = await profile_audio_service._fetch_audio_from_elevenlabs_api(conversation_id)

    if not audio_url:
        print("❌ Failed to fetch audio from ElevenLabs API")
        sys.exit(1)

    print(f"✅ Audio fetched successfully!")
    print(f"   URL prefix: {audio_url[:80]}...")
    print(f"   Total length: {len(audio_url)} characters")

    # Test attaching to profile
    print("\n--- Step 3: Attaching audio to profile ---")
    mock_payload = {
        "data": {
            "conversation_id": conversation_id,
        },
    }

    await profile_audio_service.attach_call_recording_to_profile(
        user_id=user_id,
        payload=mock_payload,
    )

    # Verify it was stored
    print("\n--- Step 4: Verifying storage in Firestore ---")
    profile_doc = fs.collection("user_profiles").document(user_id).get()
    if not profile_doc.exists:
        print(f"❌ No user_profiles document for {user_id}")
        sys.exit(1)

    profile_data = profile_doc.to_dict() or {}
    intro_url = profile_data.get("intro_audio_url")
    thinking_url = profile_data.get("thinking_audio_url")

    if intro_url and thinking_url:
        print(f"✅ Audio URLs stored successfully!")
        print(f"   intro_audio_url: {intro_url[:80]}...")
        print(f"   thinking_audio_url: {thinking_url[:80]}...")
        print(f"\n🎉 Test passed! Audio is now available for user {user_id}")
    else:
        print(f"❌ Audio URLs not found in profile:")
        print(f"   intro_audio_url: {bool(intro_url)}")
        print(f"   thinking_audio_url: {bool(thinking_url)}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test ElevenLabs audio fetching")
    parser.add_argument("--user-id", required=True, help="User ID / WhatsApp ID")
    args = parser.parse_args()

    asyncio.run(test_audio_fetch(args.user_id))


if __name__ == "__main__":
    main()

