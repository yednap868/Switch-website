#!/usr/bin/env python3
"""
Safe user deletion script that prevents auto-messages from queued webhooks.

This script properly deletes user data while setting deletion markers to prevent
Meta's queued/retry webhooks from creating a new user and sending messages.

CRITICAL: This prevents the bug where Redis FLUSHDB clears dedupe keys but Meta
still has webhooks queued, causing the agent to send messages after deletion.
"""

import os
import sys
import time


def safe_delete_user(wa_id: str, reason: str = "manual_deletion"):
    """
    Safely delete a user with proper guards to prevent webhook issues.

    Args:
        wa_id: WhatsApp ID of the user to delete
        reason: Reason for deletion (for logging)

    Returns:
        bool: True if successful, False otherwise
    """
    from utils.firebase_init import FIREBASE_AVAILABLE, fs
    from utils.redis_client import redis_cache

    if not FIREBASE_AVAILABLE:
        print(f"❌ Firebase not available")
        return False

    print(f"🗑️ Starting safe deletion of user {wa_id}")
    print(f"   Reason: {reason}")

    try:
        # STEP 1: Set deletion marker in Redis (24 hours - matches Meta's retry window)
        # This prevents any queued webhooks from Meta from recreating the user
        if redis_cache.redis_client:
            deletion_marker = f"user:deleted:{wa_id}"
            redis_cache.redis_client.setex(deletion_marker, 86400, "1")  # 24 hours
            print(f"✅ Set deletion marker (24h TTL): {deletion_marker}")

            # Also set proactive lock for immediate protection (15 minutes)
            lock_key = f"proactive_lock:{wa_id}"
            redis_cache.redis_client.setex(lock_key, 900, "1")  # 15 minutes
            print(f"✅ Set proactive lock (15m TTL): {lock_key}")
        else:
            print(f"⚠️  Redis not available - deletion markers not set!")
            print(
                f"   WARNING: User may receive messages if Meta sends queued webhooks"
            )

        # STEP 2: Delete Firebase user document
        deleted_users = 0
        for doc in fs.collection("users").where("wa_id", "==", wa_id).stream():
            user_data = doc.to_dict()
            print(f"📄 Deleting user doc: {doc.id}")
            print(f"   Name: {user_data.get('name', 'N/A')}")
            print(f"   Email: {user_data.get('email', 'N/A')}")
            doc.reference.delete()
            deleted_users += 1

        if deleted_users == 0:
            print(f"⚠️  No user found with wa_id: {wa_id}")
        else:
            print(f"✅ Deleted {deleted_users} user document(s)")

        # STEP 3: Delete conversation history
        deleted_messages = 0
        try:
            conv_ref = (
                fs.collection("conversations").document(wa_id).collection("messages")
            )
            for msg in conv_ref.stream():
                msg.reference.delete()
                deleted_messages += 1

            if deleted_messages > 0:
                print(f"✅ Deleted {deleted_messages} conversation messages")
        except Exception as e:
            print(f"⚠️  Error deleting conversations: {e}")

        # STEP 4: Clear user-specific Redis keys (NOT webhook dedupe keys!)
        if redis_cache.redis_client:
            user_keys_deleted = 0

            # Clear only user-specific keys, NOT whatsapp:msg:* (those are for dedupe)
            keys_to_delete = [
                f"user:state:{wa_id}",
                f"user:profile:{wa_id}",
                f"user:context:{wa_id}",
                f"user:memory:{wa_id}",
            ]

            for key in keys_to_delete:
                if redis_cache.redis_client.delete(key):
                    user_keys_deleted += 1

            if user_keys_deleted > 0:
                print(f"✅ Deleted {user_keys_deleted} user-specific Redis keys")

            # CRITICAL: Do NOT delete whatsapp:msg:* keys - those prevent duplicates!
            print(
                f"ℹ️  Preserved webhook dedupe keys (whatsapp:msg:*) to prevent duplicates"
            )

        print(f"\n🎉 Successfully deleted user {wa_id}")
        print(f"   Deletion marker active for 24 hours")
        print(f"   Any queued webhooks will be safely ignored")

        return True

    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        import traceback

        traceback.print_exc()
        return False


def bulk_delete_test_users(prefix: str = "test_"):
    """
    Safely delete all test users (wa_id starts with prefix).

    Args:
        prefix: Prefix to identify test users (default: "test_")
    """
    from utils.firebase_init import FIREBASE_AVAILABLE, fs

    if not FIREBASE_AVAILABLE:
        print(f"❌ Firebase not available")
        return

    print(f"🔍 Finding all users with wa_id starting with '{prefix}'")

    try:
        users_to_delete = []
        for doc in fs.collection("users").stream():
            user_data = doc.to_dict()
            wa_id = user_data.get("wa_id", "")
            if wa_id.startswith(prefix):
                users_to_delete.append(wa_id)

        if not users_to_delete:
            print(f"✅ No test users found")
            return

        print(f"📋 Found {len(users_to_delete)} test users:")
        for wa_id in users_to_delete:
            print(f"   - {wa_id}")

        confirm = input(
            f"\n⚠️  Delete all {len(users_to_delete)} test users? (yes/no): "
        )
        if confirm.lower() != "yes":
            print("❌ Deletion cancelled")
            return

        for wa_id in users_to_delete:
            safe_delete_user(wa_id, reason=f"bulk_test_cleanup_{prefix}")
            time.sleep(0.1)  # Small delay between deletions

        print(f"\n🎉 Bulk deletion complete: {len(users_to_delete)} users")

    except Exception as e:
        print(f"❌ Error during bulk deletion: {e}")


def main():
    """CLI for safe user deletion."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python safe_delete_user.py <wa_id>              # Delete single user")
        print(
            "  python safe_delete_user.py --bulk <prefix>      # Delete users by prefix"
        )
        print("\nExamples:")
        print("  python safe_delete_user.py 918368828660")
        print("  python safe_delete_user.py --bulk test_")
        sys.exit(1)

    if sys.argv[1] == "--bulk":
        prefix = sys.argv[2] if len(sys.argv) > 2 else "test_"
        bulk_delete_test_users(prefix)
    else:
        wa_id = sys.argv[1]
        success = safe_delete_user(wa_id)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
