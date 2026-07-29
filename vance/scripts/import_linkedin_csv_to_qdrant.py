#!/usr/bin/env python3
"""
Import LinkedIn profiles from CSV to Qdrant vector database.
This script processes the linkdin.csv file and stores profiles in Qdrant collections.
"""

import os
import sys
import time
from typing import Any, Dict, List

import pandas as pd

from utils.qdrant import Search, create_required_indexes, qdrant_client


def load_csv_data(csv_file_path: str) -> pd.DataFrame:
    """Load and validate CSV data."""
    try:
        print(f"📂 Loading CSV file: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        print(f"✅ Loaded {len(df)} profiles from CSV")
        return df
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)


def validate_csv_columns(df: pd.DataFrame) -> bool:
    """Validate required columns exist in CSV."""
    required_columns = [
        "Name",
        "Email",
        "LinkedIn URL",
        "Profile_Summary",
        "Urgent_Needs",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"❌ Missing required columns: {missing_columns}")
        return False

    print("✅ All required columns present")
    return True


def clean_profile_data(row: pd.Series) -> Dict[str, Any]:
    """Clean and prepare profile data for Qdrant."""
    # Clean name
    name = str(row["Name"]).strip() if pd.notna(row["Name"]) else "Unknown"

    # Clean email
    email = str(row["Email"]).strip() if pd.notna(row["Email"]) else ""

    # Clean LinkedIn URL
    linkedin_url = (
        str(row["LinkedIn URL"]).strip() if pd.notna(row["LinkedIn URL"]) else ""
    )

    # Clean profile summary
    profile_summary = (
        str(row["Profile_Summary"]).strip() if pd.notna(row["Profile_Summary"]) else ""
    )

    # Clean urgent needs
    urgent_needs = (
        str(row["Urgent_Needs"]).strip() if pd.notna(row["Urgent_Needs"]) else ""
    )

    # Clean looking for
    looking_for = (
        str(row["Looking For"]).strip() if pd.notna(row.get("Looking For", "")) else ""
    )

    # Clean bio
    bio = str(row["Bio"]).strip() if pd.notna(row.get("Bio", "")) else ""

    # Clean industry tags
    industry_tags = (
        str(row["Industry_Tags"]).strip()
        if pd.notna(row.get("Industry_Tags", ""))
        else ""
    )

    # Clean intent (optional column in CSV)
    intent = str(row["intent"]).strip() if pd.notna(row.get("intent", "")) else ""

    return {
        "name": name,
        "email": email,
        "linkedin_url": linkedin_url,
        "profile_summary": profile_summary,
        "urgent_needs": urgent_needs,
        "looking_for": looking_for,
        "bio": bio,
        "industry_tags": industry_tags,
        "intent": intent,
    }


def create_profile_document(profile_data: Dict[str, Any]) -> str:
    """Create a comprehensive profile document for vector search."""
    name = profile_data["name"]
    email = profile_data["email"]
    linkedin_url = profile_data["linkedin_url"]
    profile_summary = profile_data["profile_summary"]
    urgent_needs = profile_data["urgent_needs"]
    looking_for = profile_data["looking_for"]
    bio = profile_data["bio"]
    industry_tags = profile_data["industry_tags"]

    # Create comprehensive document
    document_parts = []

    if name and name != "Unknown":
        document_parts.append(f"Name: {name}")

    if email:
        document_parts.append(f"Email: {email}")

    if linkedin_url:
        document_parts.append(f"LinkedIn: {linkedin_url}")

    if profile_summary:
        document_parts.append(f"Profile: {profile_summary}")

    if urgent_needs:
        document_parts.append(f"Looking for: {urgent_needs}")

    if looking_for:
        document_parts.append(f"Goals: {looking_for}")

    if bio:
        document_parts.append(f"Bio: {bio}")

    if industry_tags:
        document_parts.append(f"Industry: {industry_tags}")

    return ". ".join(document_parts)


def create_needs_document(profile_data: Dict[str, Any]) -> str:
    """Create a focused needs document for urgent needs search."""
    name = profile_data["name"]
    email = profile_data["email"]
    urgent_needs = profile_data["urgent_needs"]
    looking_for = profile_data["looking_for"]
    industry_tags = profile_data["industry_tags"]

    document_parts = []

    if urgent_needs:
        document_parts.append(f"Looking for: {urgent_needs}")

    if looking_for:
        document_parts.append(f"Goals: {looking_for}")

    if industry_tags:
        document_parts.append(f"Industry: {industry_tags}")

    if name and name != "Unknown":
        document_parts.append(f"Contact: {name}")

    if email:
        document_parts.append(f"Email: {email}")

    return ". ".join(document_parts)


def import_profiles_to_qdrant(df: pd.DataFrame) -> bool:
    """Import profiles to Qdrant collections."""
    try:
        print("🔧 Creating collections first...")
        create_collections()

        print("🔧 Creating required indexes...")
        create_required_indexes()

        print("📊 Starting profile import to Qdrant...")

        # Initialize search instances with error handling
        try:
            profiles_search = Search("UserProfiles")
            needs_search = Search("UserUrgentNeeds")
        except Exception as e:
            print(f"❌ Error initializing search instances: {e}")
            print("🔄 Retrying with direct Qdrant client...")
            return import_profiles_direct(df)

        imported_count = 0
        failed_count = 0

        for index, row in df.iterrows():
            try:
                # Clean profile data
                profile_data = clean_profile_data(row)

                # Skip if no name or email
                if (
                    not profile_data["name"]
                    or profile_data["name"] == "Unknown"
                    or not profile_data["email"]
                ):
                    print(f"⏭️ Skipping row {index + 1}: Missing name or email")
                    continue

                # Create documents
                profile_document = create_profile_document(profile_data)
                needs_document = create_needs_document(profile_data)

                # Create unique user ID (Qdrant requires integer or UUID)
                user_id = index + 1
                user_id_str = f"csv_user_{user_id}"

                # Prepare metadata
                profile_metadata = {
                    "name": profile_data["name"],
                    "email": profile_data["email"],
                    "linkedin_url": profile_data["linkedin_url"],
                    "goal": profile_data["urgent_needs"],
                    "looking_for": profile_data["looking_for"],
                    "industry_tags": profile_data["industry_tags"],
                    "intent": profile_data.get("intent", ""),
                    "user_id": user_id_str,
                    "source": "linkedin_csv",
                    "import_date": time.time(),
                }

                needs_metadata = {
                    "name": profile_data["name"],
                    "email": profile_data["email"],
                    "linkedin_url": profile_data["linkedin_url"],
                    "urgent_needs": profile_data["urgent_needs"],
                    "looking_for": profile_data["looking_for"],
                    "industry_tags": profile_data["industry_tags"],
                    "intent": profile_data.get("intent", ""),
                    "user_id": user_id_str,
                    "source": "linkedin_csv",
                    "import_date": time.time(),
                }

                # Store in UserProfiles collection
                profiles_search.add(
                    user_id_str,
                    [
                        {
                            "id": user_id,  # Use integer ID for Qdrant
                            "document": profile_document,
                            "metadata": profile_metadata,
                        }
                    ],
                )

                # Store in UserUrgentNeeds collection
                needs_search.add(
                    user_id_str,
                    [
                        {
                            "id": user_id
                            + 1000000,  # Use different range to avoid conflicts
                            "document": needs_document,
                            "metadata": needs_metadata,
                        }
                    ],
                )

                imported_count += 1
                print(f"✅ Imported: {profile_data['name']} ({profile_data['email']})")

            except Exception as e:
                failed_count += 1
                print(f"❌ Failed to import row {index + 1}: {e}")
                continue

        print(f"\n🎯 Import Summary:")
        print(f"   ✅ Successfully imported: {imported_count}")
        print(f"   ❌ Failed imports: {failed_count}")
        print(f"   📊 Total processed: {len(df)}")

        return imported_count > 0

    except Exception as e:
        print(f"❌ Error importing to Qdrant: {e}")
        return False


def import_profiles_direct(df: pd.DataFrame) -> bool:
    """Import profiles directly using Qdrant client (fallback method)."""
    try:
        print("🔄 Using direct Qdrant client import...")

        # Create collections if they don't exist
        create_collections()

        imported_count = 0
        failed_count = 0

        for index, row in df.iterrows():
            try:
                # Clean profile data
                profile_data = clean_profile_data(row)

                # Skip if no name or email
                if (
                    not profile_data["name"]
                    or profile_data["name"] == "Unknown"
                    or not profile_data["email"]
                ):
                    print(f"⏭️ Skipping row {index + 1}: Missing name or email")
                    continue

                # Create documents
                profile_document = create_profile_document(profile_data)
                needs_document = create_needs_document(profile_data)

                # Create unique user ID (Qdrant requires positive integer or UUID)
                user_id = index + 1

                # Prepare metadata
                profile_metadata = {
                    "name": profile_data["name"],
                    "email": profile_data["email"],
                    "linkedin_url": profile_data["linkedin_url"],
                    "goal": profile_data["urgent_needs"],
                    "looking_for": profile_data["looking_for"],
                    "industry_tags": profile_data["industry_tags"],
                    "intent": profile_data.get("intent", ""),
                    "user_id": f"csv_user_{user_id}",
                    "source": "linkedin_csv",
                    "import_date": time.time(),
                }

                needs_metadata = {
                    "name": profile_data["name"],
                    "email": profile_data["email"],
                    "linkedin_url": profile_data["linkedin_url"],
                    "urgent_needs": profile_data["urgent_needs"],
                    "looking_for": profile_data["looking_for"],
                    "industry_tags": profile_data["industry_tags"],
                    "intent": profile_data.get("intent", ""),
                    "user_id": f"csv_user_{user_id}",
                    "source": "linkedin_csv",
                    "import_date": time.time(),
                }

                # Create simple embeddings (hash-based)
                profile_embedding = create_simple_embedding(profile_document)
                needs_embedding = create_simple_embedding(needs_document)

                # Store in UserProfiles collection
                qdrant_client.upsert(
                    collection_name="UserProfiles",
                    points=[
                        {
                            "id": user_id,
                            "vector": profile_embedding,
                            "payload": {
                                "document": profile_document,
                                **profile_metadata,
                            },
                        }
                    ],
                )

                # Store in UserUrgentNeeds collection (use different range to avoid conflicts)
                qdrant_client.upsert(
                    collection_name="UserUrgentNeeds",
                    points=[
                        {
                            "id": user_id
                            + 1000000,  # Use different range starting from 1M
                            "vector": needs_embedding,
                            "payload": {"document": needs_document, **needs_metadata},
                        }
                    ],
                )

                imported_count += 1
                print(f"✅ Imported: {profile_data['name']} ({profile_data['email']})")

            except Exception as e:
                failed_count += 1
                print(f"❌ Failed to import row {index + 1}: {e}")
                continue

        print(f"\n🎯 Import Summary:")
        print(f"   ✅ Successfully imported: {imported_count}")
        print(f"   ❌ Failed imports: {failed_count}")
        print(f"   📊 Total processed: {len(df)}")

        return imported_count > 0

    except Exception as e:
        print(f"❌ Error in direct import: {e}")
        return False


def create_collections():
    """Create Qdrant collections if they don't exist."""
    try:
        from qdrant_client.http import models

        # Create UserProfiles collection
        try:
            if not qdrant_client.collection_exists("UserProfiles"):
                qdrant_client.create_collection(
                    collection_name="UserProfiles",
                    vectors_config=models.VectorParams(
                        size=384, distance=models.Distance.COSINE
                    ),
                )
                print("✅ Created UserProfiles collection")
            else:
                print("✅ UserProfiles collection already exists")
        except Exception as e:
            print(f"⚠️ Could not create UserProfiles collection: {e}")

        # Create UserUrgentNeeds collection
        try:
            if not qdrant_client.collection_exists("UserUrgentNeeds"):
                qdrant_client.create_collection(
                    collection_name="UserUrgentNeeds",
                    vectors_config=models.VectorParams(
                        size=384, distance=models.Distance.COSINE
                    ),
                )
                print("✅ Created UserUrgentNeeds collection")
            else:
                print("✅ UserUrgentNeeds collection already exists")
        except Exception as e:
            print(f"⚠️ Could not create UserUrgentNeeds collection: {e}")

    except Exception as e:
        print(f"❌ Error creating collections: {e}")


def create_simple_embedding(text: str, size: int = 384) -> list:
    """Create a simple embedding from text."""
    # Simple hash-based embedding
    hash_val = hash(text) % 10000
    embedding = []
    for i in range(size):
        val = (hash_val + i * 17) % 1000 / 1000.0
        embedding.append(val)
    return embedding


def verify_import() -> bool:
    """Verify the import by checking collection counts."""
    try:
        print("\n🔍 Verifying import...")

        # Check UserProfiles collection
        profiles_info = qdrant_client.get_collection("UserProfiles")
        profiles_count = profiles_info.points_count
        print(f"📊 UserProfiles collection: {profiles_count} profiles")

        # Check UserUrgentNeeds collection
        needs_info = qdrant_client.get_collection("UserUrgentNeeds")
        needs_count = needs_info.points_count
        print(f"📊 UserUrgentNeeds collection: {needs_count} profiles")

        # Test search functionality
        print("\n🔍 Testing search functionality...")
        test_search = Search("UserProfiles")
        test_results = test_search.query("founder investor", limit=3)
        print(f"✅ Search test returned {len(test_results)} results")

        if test_results:
            print("📝 Sample search result:")
            sample = test_results[0]
            print(f"   Name: {sample['metadata'].get('name', 'N/A')}")
            print(f"   Email: {sample['metadata'].get('email', 'N/A')}")
            print(f"   Source: {sample['metadata'].get('source', 'N/A')}")

        return profiles_count > 0 and needs_count > 0

    except Exception as e:
        print(f"❌ Error verifying import: {e}")
        return False


def main():
    """Main function to import LinkedIn CSV to Qdrant."""
    print("🚀 LinkedIn CSV to Qdrant Importer")
    print("=" * 50)

    # Check if CSV file exists
    csv_file_path = "linkdin.csv"
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        sys.exit(1)

    # Load CSV data
    df = load_csv_data(csv_file_path)

    # Validate columns
    if not validate_csv_columns(df):
        sys.exit(1)

    # Import to Qdrant
    success = import_profiles_to_qdrant(df)

    if not success:
        print("❌ Import failed")
        sys.exit(1)

    # Verify import
    if verify_import():
        print("\n🎉 Import completed successfully!")
        print("📊 Profiles are now available for search in Qdrant")
    else:
        print("\n⚠️ Import completed but verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
