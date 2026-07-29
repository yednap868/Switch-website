# pylint: disable=no-member

import math
import os
import uuid
from typing import Optional

import numpy as np
from qdrant_client import QdrantClient
from sklearn.cluster import KMeans

QDRANT_DB_URL = os.getenv("QDRANT_BASE_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if os.getenv("QDRANT_BASE_URL") is None:
    raise Exception("QDRANT_BASE_URL not set in env")

if os.getenv("QDRANT_API_KEY") is None:
    raise Exception("QDRANT_API_KEY not set in env")


# Configure Qdrant client with proper timeout and SSL settings
import ssl

from qdrant_client.http import models

# Create SSL context with proper timeout settings
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

qdrant_client = QdrantClient(
    url=QDRANT_DB_URL,
    api_key=QDRANT_API_KEY,
    timeout=60,  # 60 second timeout
    https=True,
    grpc_port=6334,
    prefer_grpc=False,  # Use HTTP instead of gRPC for better reliability
    # Note: ssl_context parameter may not be supported in all versions
)
# Note: Removed set_model to avoid vector parameter conflicts
# qdrant_client.set_model(embedding_model_name="BAAI/bge-small-en")


def create_required_indexes():
    """
    Create required indexes for Qdrant collections.
    This fixes the 'Index required but not found' error.
    """
    try:
        from qdrant_client.http import models

        # Create index for linkedin_url in UserProfiles collection
        try:
            qdrant_client.create_payload_index(
                collection_name="UserProfiles",
                field_name="linkedin_url",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            print("✅ Created linkedin_url index for UserProfiles")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✅ linkedin_url index already exists for UserProfiles")
            else:
                print(f"⚠️ Could not create linkedin_url index for UserProfiles: {e}")

        # Create index for linkedin_url in UserUrgentNeeds collection
        try:
            qdrant_client.create_payload_index(
                collection_name="UserUrgentNeeds",
                field_name="linkedin_url",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            print("✅ Created linkedin_url index for UserUrgentNeeds")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✅ linkedin_url index already exists for UserUrgentNeeds")
            else:
                print(f"⚠️ Could not create linkedin_url index for UserUrgentNeeds: {e}")

        # Create index for intent field in UserProfiles collection
        try:
            qdrant_client.create_payload_index(
                collection_name="UserProfiles",
                field_name="intent",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            print("✅ Created intent index for UserProfiles")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✅ intent index already exists for UserProfiles")
            else:
                print(f"⚠️ Could not create intent index for UserProfiles: {e}")

        # Create index for intent field in UserUrgentNeeds collection
        try:
            qdrant_client.create_payload_index(
                collection_name="UserUrgentNeeds",
                field_name="intent",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            print("✅ Created intent index for UserUrgentNeeds")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✅ intent index already exists for UserUrgentNeeds")
            else:
                print(f"⚠️ Could not create intent index for UserUrgentNeeds: {e}")

        # Create indexes for job seeker extraction data fields (for hybrid matching)
        job_seeker_indexes = [
            ("extraction_data.current_location", models.PayloadSchemaType.TEXT),
            ("extraction_data.core_skills", models.PayloadSchemaType.TEXT),
            ("extraction_data.work_experience", models.PayloadSchemaType.TEXT),
            ("extraction_data.relocation_openness", models.PayloadSchemaType.TEXT),
            ("extraction_data.target_role", models.PayloadSchemaType.TEXT),
        ]

        for collection in ["UserProfiles", "UserUrgentNeeds"]:
            for field_name, field_type in job_seeker_indexes:
                try:
                    qdrant_client.create_payload_index(
                        collection_name=collection,
                        field_name=field_name,
                        field_schema=field_type,
                    )
                    print(f"✅ Created {field_name} index for {collection}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"✅ {field_name} index already exists for {collection}")
                    else:
                        print(
                            f"⚠️ Could not create {field_name} index for {collection}: {e}"
                        )

    except Exception as e:
        print(f"❌ Error creating indexes: {e}")


def ensure_collections_exist():
    """
    Ensure required Qdrant collections exist, create them if they don't.
    This prevents 404 errors when collections are missing.
    """
    try:
        from qdrant_client.http import models

        required_collections = ["UserProfiles", "UserUrgentNeeds"]

        for collection_name in required_collections:
            try:
                # Check if collection exists
                collection_exists = qdrant_client.collection_exists(collection_name)

                if not collection_exists:
                    print(
                        f"⚠️ [QDRANT] Collection '{collection_name}' does not exist, creating..."
                    )
                    qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=models.VectorParams(
                            size=384,  # Standard size for sentence-transformers all-MiniLM-L6-v2
                            distance=models.Distance.COSINE,
                        ),
                    )
                    print(f"✅ [QDRANT] Created collection '{collection_name}'")
                else:
                    print(f"✅ [QDRANT] Collection '{collection_name}' exists")

            except Exception as e:
                print(
                    f"❌ [QDRANT] Error checking/creating collection '{collection_name}': {e}"
                )

    except Exception as e:
        print(f"❌ [QDRANT] Error ensuring collections exist: {e}")


def _find_cutoff_using_kmeans_clustering(distances: list[float], n_clusters: int = 2):
    """Simple distance cutoff calculation."""
    if not distances:
        return 0.0
    return max(distances) * 0.8  # Simple 80% threshold


class Search:
    def __init__(self, collection_name: Optional[str] = None):
        self.collection_name = collection_name if collection_name else "default"

    def add(self, user_id: str, datalist: list[dict]):
        """Add documents to Qdrant collection with complete dynamic extraction data."""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # Initialize model with proper parallelism settings
                import os

                from sentence_transformers import SentenceTransformer

                os.environ["TOKENIZERS_PARALLELISM"] = "false"

                model = SentenceTransformer("all-MiniLM-L6-v2")

                points = []
                for data in datalist:
                    doc_id = data.get("id") or uuid.uuid4().hex

                    # NEW: Build combined document from ALL extraction fields dynamically
                    document_parts = []

                    # Get extraction data (dynamic fields)
                    extraction_data = data.get("extraction_data", {})

                    if extraction_data and isinstance(extraction_data, dict):
                        # Iterate through ALL extraction fields dynamically
                        for key, value in extraction_data.items():
                            if value:
                                value_str = str(value).strip()
                                # Skip empty values, "n/a", "none", etc.
                                if value_str and value_str.lower() not in [
                                    "n/a",
                                    "none",
                                    "null",
                                    "",
                                ]:
                                    # Format: "key: value"
                                    formatted_key = " ".join(
                                        word.capitalize() for word in key.split("_")
                                    )
                                    document_parts.append(
                                        f"{formatted_key}: {value_str}"
                                    )

                    # Fallback: If no extraction data, use the "document" field
                    if not document_parts and "document" in data:
                        document_parts.append(data["document"])

                    # Combine all parts for embedding
                    combined_document = (
                        " | ".join(document_parts).lower() if document_parts else ""
                    )

                    if not combined_document:
                        print(
                            f"⚠️ [QDRANT] No content to embed for user {user_id}, skipping"
                        )
                        continue

                    # Generate embedding from combined document
                    embedding = model.encode(combined_document).tolist()

                    # Build payload with metadata and complete extraction data
                    payload = {
                        "user_id": user_id,
                        "document": combined_document,  # Combined text for search
                        **data.get(
                            "metadata", {}
                        ),  # Include all metadata (name, email, linkedin, goal, intent)
                    }

                    # Store complete extraction data in payload for retrieval
                    if extraction_data:
                        payload["extraction_data"] = extraction_data

                    points.append(
                        {"id": doc_id, "vector": embedding, "payload": payload}
                    )

                if points:
                    qdrant_client.upsert(
                        collection_name=self.collection_name, points=points
                    )
                    print(
                        f"✅ [QDRANT] Stored {len(points)} points with complete extraction data in {self.collection_name}"
                    )
                else:
                    print(f"⚠️ [QDRANT] No valid points to store for user {user_id}")

                return  # Success, exit retry loop

            except Exception as e:
                print(
                    f"❌ [QDRANT] Error adding (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    import time

                    time.sleep(retry_delay * (2**attempt))
                else:
                    print(f"❌ [QDRANT] Failed after {max_retries} attempts")

    def query(self, query: str, limit: int = 3) -> list[dict]:
        """Search for documents in Qdrant with retry logic."""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # Initialize model with proper parallelism settings
                import os

                from sentence_transformers import SentenceTransformer

                os.environ["TOKENIZERS_PARALLELISM"] = "false"

                model = SentenceTransformer("all-MiniLM-L6-v2")
                query_embedding = model.encode(query).tolist()

                # Use query_points for qdrant-client >= 1.7
                response = qdrant_client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True,
                )

                if not response or not response.points:
                    return []

                ret = []
                for result in response.points:
                    ret.append(
                        {
                            "id": result.id,
                            "document": result.payload.get("document", ""),
                            "metadata": result.payload,
                            "distance": result.score,
                        }
                    )

                return ret
            except Exception as e:
                print(
                    f"Error querying Qdrant (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    import time

                    time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                else:
                    print(f"Failed to query Qdrant after {max_retries} attempts")
                    return []

    def search_by_metadata(self, filter: dict, limit: int = 1) -> list[dict]:
        """Search by metadata filters with retry logic."""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                results = qdrant_client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter,
                    limit=limit,
                )

                if not results or not results[0]:
                    return []

                return [result.payload for result in results[0]]
            except Exception as e:
                print(
                    f"Error searching by metadata (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    import time

                    time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                else:
                    print(f"Failed to search by metadata after {max_retries} attempts")
                    return []
