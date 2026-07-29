#!/usr/bin/env python
"""
Utility script to backfill Qdrant UserUrgentNeeds from Firestore extractions.

It:
- Reads all documents from the Firestore `extractions` collection (doc id = user phone/uid)
- Combines `urgent_needs` and `top_priorities` into a single document string
- Classifies intent
- Upserts into the `UserUrgentNeeds` collection in Qdrant with full metadata + extraction_data

Usage:
    python migrate_extractions_to_qdrant.py [--dry-run] [--limit N]
"""

import argparse
import sys
import uuid
from typing import Dict, List

from dotenv import load_dotenv

# Load env vars early
load_dotenv("env_vars.sh")

from services.claude_profile_service import claude_profile_service
from utils.db import fs
from utils.qdrant import Search, ensure_collections_exist


def get_all_extractions() -> List[Dict]:
    """Fetch all docs from the extractions collection."""
    docs = []
    try:
        ref = fs.collection("extractions")
        for doc in ref.stream():
            data = doc.to_dict() or {}
            data["uid"] = doc.id
            docs.append(data)
        print(f"✅ Found {len(docs)} extraction docs")
    except Exception as e:
        print(f"❌ Error fetching extractions: {e}")
    return docs


def get_user_profile(uid: str) -> Dict:
    """Fetch user profile from Firestore users collection."""
    try:
        doc_ref = fs.collection("users").document(uid)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict() or {}
    except Exception as e:
        print(f"⚠️ Error fetching user profile for {uid}: {e}")
    return {}


def classify_intent_from_text(text: str) -> str:
    """Classify intent using Claude; fallback to general on error."""
    try:
        if not text or len(text.strip()) < 3:
            return "general"
        return claude_profile_service.classify_intent(text)
    except Exception as e:
        print(f"⚠️ Intent classification failed: {e}, using general")
        return "general"


def build_document(extraction: Dict) -> str:
    """Combine urgent_needs and top_priorities into a single document string."""
    parts = []
    urgent = extraction.get("urgent_needs")
    if urgent:
        parts.append(str(urgent))
    top = extraction.get("top_priorities")
    if top:
        parts.append(str(top))
    return " | ".join(parts).strip()


def migrate_extraction(doc: Dict, dry_run: bool = False) -> bool:
    """Migrate a single extraction doc to Qdrant UserUrgentNeeds."""
    uid = doc.get("uid")
    if not uid:
        return False

    extraction_data = {k: v for k, v in doc.items() if k != "uid"}
    document = build_document(extraction_data)
    if not document:
        print(f"  ⚠️ Skipping {uid}: no urgent_needs/top_priorities")
        return False

    # Fetch profile metadata
    profile = get_user_profile(uid)
    name = profile.get("name", "") or extraction_data.get("name", "") or "Unknown"
    email = profile.get("email", "") or extraction_data.get("email", "")
    linkedin_url = ""
    ln = profile.get("linkedin") if isinstance(profile.get("linkedin"), dict) else None
    if ln:
        linkedin_url = ln.get("linkedin_url", "")
    linkedin_url = profile.get("linkedin_url", linkedin_url)

    # Classify intent on the combined text (fallback to general)
    intent = classify_intent_from_text(document)

    payload = {
        "id": str(uuid.uuid4().int % 1_000_000 + 1_000_000),
        "document": document,
        "metadata": {
            "name": name,
            "email": email,
            "linkedin_url": linkedin_url,
            "intent": intent,
            "user_id": uid,
            "urgent_needs": extraction_data.get("urgent_needs", ""),
        },
        "extraction_data": extraction_data,
    }

    if dry_run:
        print(f"  [DRY-RUN] Would upsert urgent need for {uid} (intent={intent})")
        return True

    try:
        Search("UserUrgentNeeds").add(user_id=uid, datalist=[payload])
        print(f"  ✅ Upserted urgent need for {uid} (intent={intent})")
        return True
    except Exception as e:
        print(f"  ❌ Error upserting for {uid}: {e}")
        return False


def migrate_all(dry_run: bool = False, limit: int = None):
    """Run the migration across all extraction docs."""
    ensure_collections_exist()

    extractions = get_all_extractions()
    if not extractions:
        print("❌ No extractions found")
        sys.exit(1)

    if limit:
        extractions = extractions[:limit]
        print(f"📊 Limiting to first {len(extractions)} docs")

    stats = {"processed": 0, "success": 0, "skipped": 0, "errors": 0}

    for doc in extractions:
        stats["processed"] += 1
        uid = doc.get("uid")
        ok = migrate_extraction(doc, dry_run=dry_run)
        if ok:
            stats["success"] += 1
        else:
            stats["skipped"] += 1

        if stats["processed"] % 25 == 0:
            print(
                f"  Progress: {stats['processed']}/{len(extractions)} "
                f"(success: {stats['success']}, skipped: {stats['skipped']})"
            )

    print("\n" + "=" * 70)
    action = "Would upsert" if dry_run else "Upserted"
    print(f"  {action}: {stats['success']} users")
    print(f"  Skipped: {stats['skipped']} users")
    print(f"  Errors: {stats['errors']} users")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Qdrant UserUrgentNeeds from Firestore extractions"
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Qdrant")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of docs")
    args = parser.parse_args()

    migrate_all(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
