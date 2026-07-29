#!/usr/bin/env python3
"""
Sync Firestore extractions to Qdrant UserUrgentNeeds collection.

This script:
1. Fetches all users from Firestore 'users' collection
2. For each user, fetches their extraction data from 'extractions/{phone_id}'
3. Upserts the data into Qdrant 'UserUrgentNeeds' collection with proper structure

Usage:
    python sync_extractions_to_qdrant.py
    # or
    uv run python sync_extractions_to_qdrant.py
"""

import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Import Firebase and Qdrant utilities
from utils.firebase_init import FIREBASE_AVAILABLE, fs
from utils.qdrant import (
    Search,
    create_required_indexes,
    ensure_collections_exist,
    qdrant_client,
)
from utils.db import get_extraction_data


def fetch_all_users() -> List[Dict[str, Any]]:
    """
    Fetch all users from Firestore 'users' collection.

    Returns:
        List of user dictionaries with uid, name, email, linkedin_url, user_type
    """
    if not FIREBASE_AVAILABLE or not fs:
        print("Firebase not available")
        return []

    print("Fetching all users from Firestore...")
    users = []

    try:
        users_ref = fs.collection("users")
        users_docs = users_ref.stream()

        for doc in users_docs:
            user_data = doc.to_dict()
            if user_data:
                users.append(
                    {
                        "uid": doc.id,
                        "name": user_data.get("name", ""),
                        "email": user_data.get("email", ""),
                        "linkedin_url": user_data.get("linkedin_url", ""),
                        "user_type": user_data.get("user_type", "general"),
                    }
                )

        print(f"Found {len(users)} users in Firestore")
        return users

    except Exception as e:
        print(f"Error fetching users: {e}")
        return []


def classify_intent(extraction_data: Dict[str, Any]) -> str:
    """
    Classify user intent based on extraction data.

    Args:
        extraction_data: Dictionary containing extraction fields

    Returns:
        Intent string: "job_seeker_need", "job_provider_need", or "general"
    """
    # Combine relevant fields for analysis
    text_to_analyze = " ".join(
        [
            str(extraction_data.get("urgent_needs", "")),
            str(extraction_data.get("current_focus", "")),
            str(extraction_data.get("top_priorities", "")),
        ]
    ).lower()

    # Job seeker keywords
    job_seeker_keywords = [
        "looking for job",
        "job search",
        "seeking employment",
        "find a job",
        "new role",
        "new position",
        "career change",
        "job opportunity",
        "looking for work",
        "employment",
        "full-time",
        "part-time",
        "remote work",
        "job seeker",
        "searching for",
        "open to opportunities",
    ]

    # Job provider keywords
    job_provider_keywords = [
        "hiring",
        "recruit",
        "looking for candidates",
        "need developers",
        "need engineers",
        "building a team",
        "expanding team",
        "open positions",
        "job openings",
        "talent acquisition",
        "looking to hire",
        "need talent",
    ]

    # Check for job provider intent first (more specific)
    for keyword in job_provider_keywords:
        if keyword in text_to_analyze:
            return "job_provider_need"

    # Check for job seeker intent
    for keyword in job_seeker_keywords:
        if keyword in text_to_analyze:
            return "job_seeker_need"

    # Default to general
    return "general"


def build_document_text(extraction_data: Dict[str, Any]) -> str:
    """
    Build searchable document text from extraction data.

    Follows the same pattern as utils/qdrant.py:Search.add() method.

    Args:
        extraction_data: Dictionary containing extraction fields

    Returns:
        Pipe-separated, lowercase document string
    """
    document_parts = []

    for key, value in extraction_data.items():
        if value:
            value_str = str(value).strip()
            # Skip empty values, "n/a", "none", etc.
            if value_str and value_str.lower() not in ["n/a", "none", "null", ""]:
                # Format: "key: value"
                formatted_key = " ".join(word.capitalize() for word in key.split("_"))
                document_parts.append(f"{formatted_key}: {value_str}")

    return " | ".join(document_parts).lower() if document_parts else ""


def generate_deterministic_uuid(user_id: str) -> str:
    """
    Generate a deterministic UUID based on user_id.
    This ensures the same user always gets the same point ID.

    Args:
        user_id: The user's phone number or identifier

    Returns:
        UUID hex string
    """
    # Use UUID5 with a namespace to generate deterministic UUID
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace
    return uuid.uuid5(namespace, f"urgent_needs_{user_id}").hex


def sync_user_to_qdrant(
    user_data: Dict[str, Any], extraction_data: Dict[str, Any]
) -> bool:
    """
    Sync a single user's extraction data to Qdrant UserUrgentNeeds collection.

    Args:
        user_data: User information (uid, name, email, linkedin_url)
        extraction_data: Extraction data from Firestore

    Returns:
        True if successful, False otherwise
    """
    try:
        uid = user_data["uid"]

        # Build document text for embedding
        document_text = build_document_text(extraction_data)

        if not document_text:
            print(f"  Skipping {uid}: No content to embed")
            return False

        # Classify intent
        intent = classify_intent(extraction_data)

        # Generate deterministic point ID
        point_id = generate_deterministic_uuid(uid)

        # Prepare metadata - check both users and extractions for email
        metadata = {
            "name": user_data.get("name", ""),
            "email": user_data.get("email", "") or extraction_data.get("email", ""),
            "linkedin_url": user_data.get("linkedin_url", ""),
            "intent": intent,
        }

        # Use Search class to add to Qdrant (handles embedding generation)
        search = Search("UserUrgentNeeds")
        search.add(
            user_id=uid,
            datalist=[
                {
                    "id": point_id,
                    "extraction_data": extraction_data,
                    "metadata": metadata,
                }
            ],
        )

        return True

    except Exception as e:
        print(f"  Error syncing user {user_data.get('uid', 'unknown')}: {e}")
        return False


def get_collection_count(collection_name: str) -> int:
    """Get the number of points in a Qdrant collection."""
    try:
        info = qdrant_client.get_collection(collection_name)
        return info.points_count
    except Exception:
        return 0


def verify_sync() -> bool:
    """Verify the sync by testing search functionality."""
    try:
        print("\nVerifying sync...")

        # Test search
        search = Search("UserUrgentNeeds")
        results = search.query("job seeking developer", limit=3)

        print(f"  Search test returned {len(results)} results")

        if results:
            print("  Sample result:")
            sample = results[0]
            metadata = sample.get("metadata", {})
            print(f"    Name: {metadata.get('name', 'N/A')}")
            print(f"    Intent: {metadata.get('intent', 'N/A')}")
            print(f"    User ID: {metadata.get('user_id', 'N/A')}")

        return True

    except Exception as e:
        print(f"  Verification error: {e}")
        return False


def main():
    """Main function to sync Firestore extractions to Qdrant."""
    print("=" * 60)
    print("Firestore Extractions to Qdrant UserUrgentNeeds Sync")
    print("=" * 60)

    # Check Firebase availability
    if not FIREBASE_AVAILABLE:
        print("ERROR: Firebase is not available. Check credentials.")
        sys.exit(1)

    # Ensure Qdrant collections exist
    print("\nEnsuring Qdrant collections exist...")
    ensure_collections_exist()

    # Create required indexes
    print("\nCreating required indexes...")
    create_required_indexes()

    # Get initial collection count
    initial_count = get_collection_count("UserUrgentNeeds")
    print(f"\nInitial UserUrgentNeeds count: {initial_count}")

    # Fetch all users
    users = fetch_all_users()

    if not users:
        print("No users found. Exiting.")
        sys.exit(0)

    # Process each user
    print(f"\nProcessing {len(users)} users...")
    print("-" * 40)

    stats = {
        "processed": 0,
        "synced": 0,
        "skipped_no_extraction": 0,
        "failed": 0,
    }

    for i, user_data in enumerate(users, 1):
        uid = user_data["uid"]
        name = user_data.get("name", "Unknown")

        print(f"[{i}/{len(users)}] Processing: {name} ({uid})")
        stats["processed"] += 1

        # Fetch extraction data
        extraction_data = get_extraction_data(uid)

        if not extraction_data:
            print(f"  No extraction data found, skipping")
            stats["skipped_no_extraction"] += 1
            continue

        # Sync to Qdrant
        if sync_user_to_qdrant(user_data, extraction_data):
            stats["synced"] += 1
        else:
            stats["failed"] += 1

    # Get final collection count
    final_count = get_collection_count("UserUrgentNeeds")

    # Print summary
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    print(f"  Total users processed: {stats['processed']}")
    print(f"  Successfully synced:   {stats['synced']}")
    print(f"  Skipped (no data):     {stats['skipped_no_extraction']}")
    print(f"  Failed:                {stats['failed']}")
    print(f"\n  Collection count before: {initial_count}")
    print(f"  Collection count after:  {final_count}")
    print(f"  Net change:              {final_count - initial_count}")

    # Verify
    verify_sync()

    print("\nSync complete!")


if __name__ == "__main__":
    main()
