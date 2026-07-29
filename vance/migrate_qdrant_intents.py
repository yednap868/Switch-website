#!/usr/bin/env python
"""
Migration script to add intent classification to existing Qdrant users.

This script:
1. Retrieves all users from UserProfiles and UserUrgentNeeds collections
2. Classifies their intent based on extraction_data/document
3. Updates their metadata with the intent field

Usage:
    python migrate_qdrant_intents.py [--dry-run]

Options:
    --dry-run    Show what would be updated without making changes
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

# Load environment variables
from dotenv import load_dotenv

load_dotenv("env_vars.sh")

from services.claude_profile_service import claude_profile_service
from utils.qdrant import qdrant_client, ensure_collections_exist


def classify_user_intent(extraction_data: Dict, document: str = "") -> str:
    """
    Classify user intent from extraction data or document.

    Args:
        extraction_data: User's extraction data dict
        document: Fallback document text

    Returns:
        Intent string (e.g., "job_seeker_need", "hiring_need", "general")
    """
    # Build text from extraction data
    extraction_text_parts = []

    if extraction_data and isinstance(extraction_data, dict):
        for key, value in extraction_data.items():
            if value:
                value_str = str(value).strip()
                if value_str and value_str.lower() not in ["n/a", "none", "null", ""]:
                    extraction_text_parts.append(value_str)

    # Fallback to document if no extraction data
    if not extraction_text_parts and document:
        extraction_text_parts.append(document)

    extraction_text = " ".join(extraction_text_parts)

    if not extraction_text or len(extraction_text.strip()) < 3:
        return "general"

    try:
        intent = claude_profile_service.classify_intent(extraction_text)
        return intent
    except Exception as e:
        print(f"⚠️ Intent classification failed: {e}, using 'general'")
        return "general"


def migrate_collection(collection_name: str, dry_run: bool = False) -> Dict[str, int]:
    """
    Migrate a single Qdrant collection to add intent fields.

    Args:
        collection_name: Name of the collection to migrate

    Returns:
        Dict with migration stats: {"updated": int, "skipped": int, "errors": int}
    """
    stats = {"updated": 0, "skipped": 0, "errors": 0}

    try:
        # Check if collection exists
        if not qdrant_client.collection_exists(collection_name):
            print(f"⚠️ Collection '{collection_name}' does not exist, skipping")
            return stats

        # Get collection info
        collection_info = qdrant_client.get_collection(collection_name)
        total_points = collection_info.vectors_count

        if total_points == 0:
            print(f"ℹ️ Collection '{collection_name}' is empty, skipping")
            return stats

        print(f"\n📊 Migrating '{collection_name}': {total_points} points")

        # Scroll through all points
        offset = None
        batch_size = 100
        processed = 0

        while True:
            # Scroll to get next batch
            result = qdrant_client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,  # Don't need vectors for metadata update
            )

            points, next_offset = result

            if not points:
                break

            # Process each point
            for point in points:
                try:
                    payload = point.payload
                    point_id = point.id

                    # Check if intent already exists and is valid
                    existing_intent = payload.get("intent", "")
                    if existing_intent and existing_intent != "general":
                        stats["skipped"] += 1
                        processed += 1
                        continue

                    # Get extraction data or document
                    extraction_data = payload.get("extraction_data", {})
                    document = payload.get("document", "")

                    # Classify intent
                    intent = classify_user_intent(extraction_data, document)

                    if dry_run:
                        # Just log what would be updated
                        name = payload.get("name", "Unknown")
                        print(
                            f"  [DRY-RUN] Would update {name} (ID: {point_id}) with intent: {intent}"
                        )
                    else:
                        # Update the point in Qdrant
                        qdrant_client.set_payload(
                            collection_name=collection_name,
                            payload={"intent": intent},
                            points=[point_id],
                        )

                    stats["updated"] += 1
                    processed += 1

                    # Progress indicator
                    if processed % 10 == 0:
                        print(f"  Processed {processed}/{total_points}...")

                except Exception as e:
                    stats["errors"] += 1
                    print(f"  ❌ Error processing point {point_id}: {e}")
                    processed += 1

            # Check if we're done
            if next_offset is None:
                break

            offset = next_offset

        print(
            f"✅ Completed '{collection_name}': {stats['updated']} updated, {stats['skipped']} skipped, {stats['errors']} errors"
        )

    except Exception as e:
        print(f"❌ Error migrating collection '{collection_name}': {e}")
        stats["errors"] += 1

    return stats


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate Qdrant users with intent classification"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  QDRANT INTENT MIGRATION")
    print("  Adding intent classification to existing users")
    if args.dry_run:
        print("  ⚠️  DRY RUN MODE - No changes will be made")
    print("=" * 70)

    # Ensure collections exist
    print("\n1️⃣ Ensuring collections exist...")
    try:
        ensure_collections_exist()
    except Exception as e:
        print(f"❌ Error ensuring collections: {e}")
        sys.exit(1)

    # Migrate both collections
    print("\n2️⃣ Starting migration...")
    total_stats = {"updated": 0, "skipped": 0, "errors": 0}

    collections = ["UserProfiles", "UserUrgentNeeds"]

    for collection_name in collections:
        stats = migrate_collection(collection_name, dry_run=args.dry_run)
        total_stats["updated"] += stats["updated"]
        total_stats["skipped"] += stats["skipped"]
        total_stats["errors"] += stats["errors"]

    # Summary
    print("\n" + "=" * 70)
    print("  MIGRATION SUMMARY")
    print("=" * 70)
    action = "Would update" if args.dry_run else "Updated"
    print(f"  ✅ {action}: {total_stats['updated']} users")
    print(f"  ⏭️  Skipped: {total_stats['skipped']} users (already had intent)")
    print(f"  ❌ Errors: {total_stats['errors']} users")
    print("=" * 70)

    if args.dry_run:
        print("\n⚠️ This was a dry run. Run without --dry-run to apply changes.")
    elif total_stats["errors"] > 0:
        print("\n⚠️ Some errors occurred. Check the logs above for details.")
        sys.exit(1)
    else:
        print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    main()
