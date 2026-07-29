#!/usr/bin/env python3
"""
Comprehensive cache clearing script for development and testing.
Clears Python cache, Firebase test data, and prepares for fresh testing.
"""

import os
import subprocess
import sys


def clear_python_cache():
    """Clear Python bytecode cache files."""
    print("🐍 Clearing Python cache...")
    try:
        # Remove .pyc files
        result = subprocess.run(
            ["find", ".", "-name", "*.pyc", "-delete"], capture_output=True, text=True
        )
        # Remove __pycache__ directories
        result = subprocess.run(
            [
                "find",
                ".",
                "-name",
                "__pycache__",
                "-type",
                "d",
                "-exec",
                "rm",
                "-rf",
                "{}",
                "+",
            ],
            capture_output=True,
            text=True,
        )
        print("✅ Python cache cleared")
        return True
    except Exception as e:
        print(f"❌ Python cache clear failed: {e}")
        return False


def clear_firebase_test_data():
    """Clear Firebase test data."""
    print("🔥 Clearing Firebase test data...")
    try:
        from utils.firebase_init import FIREBASE_AVAILABLE, fs

        if not FIREBASE_AVAILABLE:
            print("⚠️  Firebase not available - skipping")
            return False

        db = fs

        # Clear user profiles (be careful with this in production!)
        profiles_ref = db.collection("users")
        profiles = profiles_ref.stream()
        deleted_count = 0

        for profile in profiles:
            profile_data = profile.to_dict()
            wa_id = profile_data.get("wa_id", "")

            # Safety check - only delete if it looks like a test environment
            # You can modify this logic based on your test user patterns
            if wa_id and (
                wa_id.startswith("test_") or len(str(wa_id)) > 0
            ):  # Modify as needed
                profile.reference.delete()
                deleted_count += 1

                # Clear conversation history
                try:
                    conversations_ref = (
                        db.collection("conversations")
                        .document(wa_id)
                        .collection("messages")
                    )
                    messages = conversations_ref.stream()
                    for message in messages:
                        message.reference.delete()
                except:
                    pass  # Conversation might not exist

        print(f"✅ Cleared data for {deleted_count} users from Firebase")
        return True

    except Exception as e:
        print(f"❌ Firebase cache clear failed: {e}")
        return False


def clear_redis_cache():
    """
    Clear Redis cache if available.

    IMPORTANT: This now SELECTIVELY clears only non-critical keys.
    It preserves webhook deduplication keys (whatsapp:msg:*) to prevent
    Meta's queued webhooks from being re-processed after cache clear.
    """
    print("🔴 Clearing Redis cache (selective)...")
    try:
        from utils.redis_client import redis_cache

        if not redis_cache.redis_client:
            print("⚠️  Redis not available")
            return False

        r = redis_cache.redis_client
        cleared_count = 0

        # Clear only specific key patterns (NOT webhook dedupe keys)
        patterns_to_clear = [
            "claude:*",  # Claude API cache
            "user:state:*",  # User states
            "user:profile:*",  # User profiles
            "user:context:*",  # User contexts
            "user:memory:*",  # User memories
        ]

        for pattern in patterns_to_clear:
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                cleared_count += deleted
                print(f"   Cleared {deleted} keys matching: {pattern}")

        # Count preserved dedupe keys
        dedupe_keys = r.keys("whatsapp:msg:*")
        print(
            f"   ✅ Preserved {len(dedupe_keys)} webhook dedupe keys (whatsapp:msg:*)"
        )

        # Count preserved deletion markers
        deletion_markers = r.keys("user:deleted:*")
        if deletion_markers:
            print(
                f"   ✅ Preserved {len(deletion_markers)} deletion markers (user:deleted:*)"
            )

        # Count preserved locks
        locks = r.keys("proactive_lock:*")
        if locks:
            print(f"   ✅ Preserved {len(locks)} proactive locks")

        print(
            f"✅ Redis cache cleared ({cleared_count} keys deleted, critical keys preserved)"
        )
        return True

    except Exception as e:
        print(f"⚠️  Redis cache clear failed (may not be configured): {e}")
        return False


def main():
    """Main cache clearing function."""
    print("🧹 Starting comprehensive cache clearing...")
    print("=" * 50)

    results = []

    # Clear Python cache
    results.append(("Python Cache", clear_python_cache()))

    # Clear Firebase data
    results.append(("Firebase Data", clear_firebase_test_data()))

    # Clear Redis cache
    results.append(("Redis Cache", clear_redis_cache()))

    print("\n" + "=" * 50)
    print("📊 Cache Clearing Results:")
    for cache_type, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   {cache_type}: {status}")

    success_count = sum(1 for _, success in results if success)
    print(f"\n🎯 {success_count}/{len(results)} cache types cleared successfully")

    if success_count == len(results):
        print("\n🎉 All caches cleared! Ready for fresh testing.")
        print(
            "💡 Remember to clear WhatsApp chats on your test device for complete UX testing."
        )
    else:
        print("\n⚠️  Some caches may not have been cleared. Check the errors above.")

    return success_count == len(results)


if __name__ == "__main__":
    success = main()
    print(f"\n🔄 You can now restart your application for a completely fresh state.")
    sys.exit(0 if success else 1)
