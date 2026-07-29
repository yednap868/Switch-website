"""
Script to list all entries in Qdrant collections UserProfiles and UserUrgentNeeds.
Dumps data to JSON file and prints to terminal.
"""

import json
import os
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models

# Load environment variables
QDRANT_DB_URL = os.getenv("QDRANT_BASE_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_DB_URL:
    raise Exception("QDRANT_BASE_URL not set in env")

if not QDRANT_API_KEY:
    raise Exception("QDRANT_API_KEY not set in env")

# Initialize Qdrant client
qdrant_client = QdrantClient(
    url=QDRANT_DB_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,
    https=True,
    grpc_port=6334,
    prefer_grpc=False,
)


def get_all_points_from_collection(collection_name: str) -> list[dict]:
    """
    Retrieve all points from a Qdrant collection.

    Args:
        collection_name: Name of the collection to retrieve points from

    Returns:
        List of dictionaries containing point data
    """
    all_points = []
    offset = None

    try:
        # Check if collection exists
        if not qdrant_client.collection_exists(collection_name):
            print(f"⚠️  Collection '{collection_name}' does not exist")
            return []

        # Get collection info
        collection_info = qdrant_client.get_collection(collection_name)
        total_count = collection_info.points_count
        print(f"📊 Collection '{collection_name}' has {total_count} points")

        # Scroll through all points
        while True:
            results, next_offset = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            if not results:
                break

            for point in results:
                point_data = {
                    "id": point.id,
                    "payload": point.payload,
                }
                all_points.append(point_data)

            # Update offset for next iteration
            offset = next_offset
            if offset is None:
                break

        print(f"✅ Retrieved {len(all_points)} points from '{collection_name}'")

    except Exception as e:
        print(f"❌ Error retrieving points from '{collection_name}': {e}")

    return all_points


def main():
    """Main function to retrieve and export Qdrant data."""
    print("=" * 80)
    print("🚀 Starting Qdrant Collections Export")
    print("=" * 80)
    print()

    # Collections to export
    collections = ["UserProfiles", "UserUrgentNeeds"]

    # Dictionary to store all data
    export_data = {"timestamp": datetime.now().isoformat(), "collections": {}}

    # Retrieve data from each collection
    for collection_name in collections:
        print(f"\n📥 Retrieving data from collection: {collection_name}")
        print("-" * 80)

        points = get_all_points_from_collection(collection_name)
        export_data["collections"][collection_name] = {
            "count": len(points),
            "points": points,
        }

        print()

    # Print summary to terminal
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    for collection_name, collection_data in export_data["collections"].items():
        print(f"  {collection_name}: {collection_data['count']} points")
    print()

    # Print full data to terminal (pretty printed)
    print("=" * 80)
    print("📄 FULL DATA")
    print("=" * 80)
    print(json.dumps(export_data, indent=2, default=str))
    print()

    # Export to JSON file
    output_filename = f"qdrant_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_filename, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    print("=" * 80)
    print(f"✅ Data exported to: {output_filename}")
    print("=" * 80)


if __name__ == "__main__":
    main()
