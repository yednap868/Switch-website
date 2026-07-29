#!/usr/bin/env python3
"""
Script to create required Firebase indexes for optimal query performance.
Run this to create composite indexes that improve query performance.
"""

import time
import webbrowser


def create_firebase_indexes():
    """Guide user through creating Firebase composite indexes."""

    print("🔥 Firebase Index Creation Helper")
    print("=" * 50)

    indexes = [
        {
            "name": "Voice Call History Index",
            "collection": "conversations/{userId}/messages",
            "fields": ["type", "timestamp"],
            "description": "Required for voice call history queries",
            "url": "https://console.firebase.google.com/v1/r/project/relay-15824/firestore/indexes?create_composite=Ckxwcm9qZWN0cy9yZWxheS0xNTgyNC9kYXRhYmFzZXMvKGRlZmF1bHQpL2NvbGxlY3Rpb25Hcm91cHMvbWVzc2FnZXMvaW5kZXhlcy9fEAEaCAoEdHlwZRABGg0KCXRpbWVzdGFtcBACGgwKCF9fbmFtZV9fEAI",
        }
    ]

    print("📋 Required Firebase Composite Indexes:")
    print()

    for i, index in enumerate(indexes, 1):
        print(f"{i}. {index['name']}")
        print(f"   Collection: {index['collection']}")
        print(f"   Fields: {', '.join(index['fields'])}")
        print(f"   Purpose: {index['description']}")
        print()

    print("🚀 To create these indexes:")
    print("1. Open the Firebase Console")
    print("2. Go to Firestore Database")
    print("3. Click on 'Indexes' in the left sidebar")
    print("4. Click 'Create Index'")
    print("5. Fill in the collection and fields as shown above")
    print()

    # Open the index creation URL
    if indexes:
        print("🔗 Opening index creation URL...")
        time.sleep(2)
        webbrowser.open(indexes[0]["url"])

    print()
    print("💡 Note: Index creation can take 5-10 minutes to complete.")
    print("   The app will use fallback queries until indexes are ready.")
    print()
    print("✅ Index creation URLs opened in browser!")


if __name__ == "__main__":
    create_firebase_indexes()
