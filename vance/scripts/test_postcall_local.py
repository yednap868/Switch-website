#!/usr/bin/env python3
"""
Test script for hitting the post-call webhook endpoint locally.
Usage: python scripts/test_postcall_local.py
"""

import requests
import json

# Test payload mimicking ElevenLabs post-call webhook
payload = {
    "call_id": "test-call-123",
    "conversation_id": "conv-abc-456",
    "user_id": "918766335252",  # Use a real user_id from your Firestore
    "duration": 245,
    "transcript": """
    Agent: Hi, this is Vance. How can I help you today?
    User: I'm looking to hire some engineers for my startup.
    Agent: Great! What kind of engineers are you looking for?
    User: We need backend developers with Python and cloud experience.
    Agent: What's your company name and what do you do?
    User: It's DeepLock, we're building AI security tools.
    Agent: And what's your budget range for these hires?
    User: Around 20-30 LPA for senior engineers.
    Agent: Perfect. Any specific skills you're prioritizing?
    User: AWS, Kubernetes, and ideally some ML experience.
    """,
    "conversation_transcript": """
    Agent: Hi, this is Vance. How can I help you today?
    User: I'm looking to hire some engineers for my startup.
    Agent: Great! What kind of engineers are you looking for?
    User: We need backend developers with Python and cloud experience.
    """,
    "agent_messages": [
        "Hi, this is Vance. How can I help you today?",
        "Great! What kind of engineers are you looking for?",
        "What's your company name and what do you do?",
        "And what's your budget range for these hires?",
        "Perfect. Any specific skills you're prioritizing?",
    ],
    "user_messages": [
        "I'm looking to hire some engineers for my startup.",
        "We need backend developers with Python and cloud experience.",
        "It's DeepLock, we're building AI security tools.",
        "Around 20-30 LPA for senior engineers.",
        "AWS, Kubernetes, and ideally some ML experience.",
    ],
    "key_insights": {
        "hiring_intent": True,
        "role_type": "backend engineer",
        "budget": "20-30 LPA",
    },
    "data": {
        "user_id": "918766335252",
    },
    "conversation_initiation_client_data": {
        "dynamic_variables": {
            "user_id": "918766335252",
            "user_name": "Test User",
        }
    },
}


def test_webhook(base_url: str = "http://localhost:8000"):
    """Hit the post-call webhook endpoint."""
    url = f"{base_url}/elevenlabs/webhook/post-call"

    print(f"🎯 Hitting: {url}")
    print(f"📦 Payload keys: {list(payload.keys())}")
    print("-" * 50)

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"📬 Status: {response.status_code}")
        print(f"📄 Response: {response.json()}")
        print("-" * 50)
        print("✅ Request sent! Check your server logs for background task output.")

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed. Is the server running at {base_url}?")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    test_webhook(base_url)
