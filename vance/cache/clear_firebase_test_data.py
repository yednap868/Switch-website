#!/usr/bin/env python3
"""
Script to clear Firebase test data for fresh testing.
Use this to reset user data between test runs.
"""

import os
import sys

import firebase_admin
from firebase_admin import credentials, firestore


def clear_firebase_test_data():
    """Clear all test user data from Firebase."""
    try:
        from utils.firebase_init import FIREBASE_AVAILABLE, fs

        if not FIREBASE_AVAILABLE:
            print("❌ Firebase not available")
            return False

        db = fs

        print("🧹 Clearing Firebase test data...")

        # Clear user profiles
        profiles_ref = db.collection("users")
        profiles = profiles_ref.stream()
        deleted_count = 0

        for profile in profiles:
            # Only delete test users (you can add specific criteria)
            profile_data = profile.to_dict()
            wa_id = profile_data.get("wa_id", "")

            # Add your test user filtering logic here
            # For example: if wa_id.startswith('test_') or specific test numbers
            if wa_id:  # Delete all for now, modify as needed
                profile.reference.delete()
                deleted_count += 1

                # Also clear conversation history for this user
                conversations_ref = (
                    db.collection("conversations")
                    .document(wa_id)
                    .collection("messages")
                )
                messages = conversations_ref.stream()
                for message in messages:
                    message.reference.delete()

        print(f"✅ Cleared data for {deleted_count} users")
        print("✅ Firebase cache cleared for testing")

        return True

    except Exception as e:
        print(f"❌ Error clearing Firebase data: {e}")
        return False


if __name__ == "__main__":
    success = clear_firebase_test_data()
    sys.exit(0 if success else 1)
