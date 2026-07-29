#!/usr/bin/env python3
"""
Diagnostic script to check Qdrant email field coverage.

This script:
1. Queries all points from UserProfiles and UserUrgentNeeds collections
2. Counts entries with/without email field
3. Reports statistics showing the extent of missing data

Usage:
    python scripts/check_qdrant_emails.py
    # or
    uv run python scripts/check_qdrant_emails.py
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.qdrant import qdrant_client


def check_collection_emails(collection_name: str) -> dict:
    """
    Check email coverage for a single Qdrant collection.

    Args:
        collection_name: Name of the Qdrant collection to check

    Returns:
        Dictionary with statistics about email coverage
    """
    stats = {
        "total": 0,
        "with_email": 0,
        "without_email": 0,
        "empty_email": 0,
        "missing_user_ids": [],
    }

    try:
        info = qdrant_client.get_collection(collection_name)
        print(f"  Collection '{collection_name}' has {info.points_count} points")
    except Exception as e:
        print(f"  Error getting collection info: {e}")
        return stats

    offset = None
    batch_size = 100

    while True:
        try:
            results = qdrant_client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, next_offset = results

            if not points:
                break

            for point in points:
                stats["total"] += 1
                payload = point.payload or {}
                email = payload.get("email", None)
                user_id = payload.get("user_id", "unknown")

                if email is None:
                    stats["without_email"] += 1
                    stats["missing_user_ids"].append(user_id)
                elif email == "":
                    stats["empty_email"] += 1
                    stats["missing_user_ids"].append(user_id)
                else:
                    stats["with_email"] += 1

            offset = next_offset
            if offset is None:
                break

        except Exception as e:
            print(f"  Error scrolling collection: {e}")
            break

    return stats


def main():
    """Main function to check email coverage in Qdrant collections."""
    print("=" * 60)
    print("Qdrant Email Field Coverage Check")
    print("=" * 60)

    collections = ["UserProfiles", "UserUrgentNeeds"]
    all_stats = {}

    for collection in collections:
        print(f"\nChecking {collection}...")
        stats = check_collection_emails(collection)
        all_stats[collection] = stats

        print(f"\n  Results for {collection}:")
        print(f"    Total points:     {stats['total']}")
        print(f"    With email:       {stats['with_email']}")
        print(f"    Without email:    {stats['without_email']}")
        print(f"    Empty email:      {stats['empty_email']}")

        missing_count = stats['without_email'] + stats['empty_email']
        if stats['total'] > 0:
            coverage = (stats['with_email'] / stats['total']) * 100
            print(f"    Email coverage:   {coverage:.1f}%")
        else:
            print(f"    Email coverage:   N/A (no points)")

        if missing_count > 0 and missing_count <= 20:
            print(f"\n  User IDs missing email:")
            for uid in stats['missing_user_ids'][:20]:
                print(f"    - {uid}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_all = sum(s['total'] for s in all_stats.values())
    with_email_all = sum(s['with_email'] for s in all_stats.values())
    missing_all = sum(s['without_email'] + s['empty_email'] for s in all_stats.values())

    print(f"Total points across all collections: {total_all}")
    print(f"Points with email:                   {with_email_all}")
    print(f"Points missing/empty email:          {missing_all}")

    if total_all > 0:
        overall_coverage = (with_email_all / total_all) * 100
        print(f"Overall email coverage:              {overall_coverage:.1f}%")

    if missing_all > 0:
        print(f"\n⚠️  {missing_all} entries need email backfill!")
    else:
        print("\n✅ All entries have email addresses!")

    return all_stats


if __name__ == "__main__":
    main()
