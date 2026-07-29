"""
Generate candidate intros for job providers who have completed a call.

This script does **NOT** send any messages. It only prints a reviewable
list of providers and their suggested matches so a human can review
before we wire up an automated sending flow.

Usage:
    uv run python -m scripts.send_intros --limit-per-provider 3 > intros_review.json
"""

import argparse
import json
import os
from typing import Any, Dict, List

import firebase_admin
from firebase_admin import credentials, firestore

from services.hybrid_matching_service import MatchedProfile, hybrid_matching_service
from services.claude_profile_service import claude_profile_service


_fs: firestore.Client | None = None


def _get_fs() -> firestore.Client:
    """
    Lazily initialize and return a Firestore client using GOOGLE_APPLICATION_CREDENTIALS.

    This avoids relying on utils.firebase_init / utils.db which may not be
    initialized correctly in CLI contexts.
    """
    global _fs
    if _fs is not None:
        return _fs

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        raise RuntimeError(
            f"GOOGLE_APPLICATION_CREDENTIALS not set or file missing: {cred_path!r}"
        )

    # Reuse existing app if already initialized
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

    _fs = firestore.client()
    return _fs


def _get_user_profile(uid: str) -> dict:
    """Minimal reimplementation of utils.db.get_user_profile using local Firestore client."""
    fs = _get_fs()
    doc_ref = fs.collection("users").document(uid)
    doc = doc_ref.get()
    return doc.to_dict() or {}


def _get_extraction_data(uid: str) -> dict:
    """Minimal reimplementation of utils.db.get_extraction_data using local Firestore client."""
    fs = _get_fs()
    doc_ref = fs.collection("extractions").document(uid)
    doc = doc_ref.get()
    return doc.to_dict() or {}


def _has_completed_call(uid: str) -> bool:
    """
    Return True if the user has at least one completed call.
    Uses the user_calls/{uid}/calls collection.
    """
    try:
        fs = _get_fs()
        calls_ref = fs.collection("user_calls").document(uid).collection("calls")
        docs = list(calls_ref.limit(1).stream())
        return len(docs) > 0
    except Exception as e:
        print(f"⚠️ [INTROS] Error checking call history for {uid}: {e}")
        return False


def _is_job_provider(uid: str, profile: Dict[str, Any], extraction: Dict[str, Any]) -> bool:
    """
    Heuristic: treat user as job provider if Claude intent says so
    OR if extraction data clearly looks like hiring.
    """
    # First, try intent classification using goal / urgent_needs text
    goal = (profile.get("goal") or profile.get("primary_goal") or "").strip()
    urgent_needs = (extraction.get("urgent_needs") or "").strip()
    text_for_intent = urgent_needs or goal

    intent = claude_profile_service.classify_intent(text_for_intent)

    if intent in {"hiring_need", "job_provider"}:
        return True

    # Fallback: use the same logic as should_send_profiles_to_user
    should_send, _reason = claude_profile_service.should_send_profiles_to_user(
        extraction
    )
    return should_send


def _summarize_extraction(extraction: Dict[str, Any]) -> str:
    """
    Build a short human-readable summary of what the provider is hiring for.
    """
    if not extraction:
        return ""

    parts: List[str] = []
    fields_in_order = [
        "job_title",
        "required_skills",
        "experience_level",
        "work_model",
        "office_location",
        "urgent_needs",
        "the_story",
        "current_focus",
    ]

    for key in fields_in_order:
        val = extraction.get(key)
        if not val:
            continue
        text = str(val).strip()
        if not text:
            continue
        if key == "job_title":
            parts.append(f"Role: {text}")
        elif key == "required_skills":
            parts.append(f"Skills: {text}")
        elif key == "experience_level":
            parts.append(f"Experience: {text}")
        elif key == "work_model":
            parts.append(f"Work model: {text}")
        elif key == "office_location":
            parts.append(f"Location: {text}")
        elif key == "urgent_needs":
            parts.append(f"Urgent needs: {text}")
        elif key == "the_story":
            parts.append(f"Story: {text[:140]}{'...' if len(text) > 140 else ''}")
        elif key == "current_focus":
            parts.append(f"Focus: {text[:140]}{'...' if len(text) > 140 else ''}")

    return " | ".join(parts)


async def _find_matches_for_provider(
    uid: str, extraction: Dict[str, Any], limit_per_provider: int
) -> List[MatchedProfile]:
    """
    Use existing hybrid_matching_service to find candidate job seekers
    for a single job provider.
    """
    try:
        matches = await hybrid_matching_service.find_job_seeker_matches(
            job_provider_data=extraction,
            limit=limit_per_provider,
            job_provider_uid=uid,
        )
        return matches or []
    except Exception as e:
        print(f"❌ [INTROS] Error finding matches for {uid}: {e}")
        return []


async def generate_intros(limit_per_provider: int = 3) -> List[Dict[str, Any]]:
    """
    Main entry: scan all users, pick job providers with a completed call,
    and compute suggested job seeker matches for review.

    Returns a list of dicts suitable for JSON export.
    """
    print("🔍 [INTROS] Scanning users for eligible job providers...")
    fs = _get_fs()
    users_ref = fs.collection("users")
    user_docs = list(users_ref.stream())

    all_suggestions: List[Dict[str, Any]] = []
    processed = 0

    for doc in user_docs:
        uid = doc.id
        user_data = doc.to_dict() or {}

        processed += 1
        if processed % 50 == 0:
            print(f"🔄 [INTROS] Processed {processed} users...")

        # Skip obviously bad IDs
        if not uid or uid == "default" or len(uid) < 5:
            continue

        # Require at least one completed call
        if not _has_completed_call(uid):
            continue

        profile = _get_user_profile(uid)
        extraction = _get_extraction_data(uid)

        if not extraction:
            continue

        # Only keep job providers
        if not _is_job_provider(uid, profile, extraction):
            continue

        provider_name = profile.get("name") or user_data.get("name") or "Unknown"
        provider_email = profile.get("email") or user_data.get("email") or ""
        provider_summary = _summarize_extraction(extraction)

        matches = await _find_matches_for_provider(
            uid=uid, extraction=extraction, limit_per_provider=limit_per_provider
        )

        if not matches:
            continue

        suggestions_for_provider: Dict[str, Any] = {
            "provider_uid": uid,
            "provider_name": provider_name,
            "provider_email": provider_email,
            "provider_summary": provider_summary,
            "matches": [],
        }

        for m in matches:
            suggestions_for_provider["matches"].append(
                {
                    "seeker_uid": m.uid,
                    "seeker_name": m.name,
                    "seeker_email": m.email,
                    "target_role": m.target_role,
                    "core_skills": m.core_skills,
                    "work_experience": m.work_experience,
                    "current_location": m.current_location,
                    "salary_expectations": m.salary_expectations,
                    "match_score": m.match_score,
                    "match_reason": m.match_reason,
                }
            )

        all_suggestions.append(suggestions_for_provider)

    print(f"✅ [INTROS] Generated suggestions for {len(all_suggestions)} providers")
    return all_suggestions


def main():
    parser = argparse.ArgumentParser(
        description="Generate reviewable intro suggestions for job providers."
    )
    parser.add_argument(
        "--limit-per-provider",
        type=int,
        default=3,
        help="Maximum number of matches per job provider (default: 3)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output instead of a single line",
    )

    args = parser.parse_args()

    import asyncio

    suggestions = asyncio.run(generate_intros(limit_per_provider=args.limit_per_provider))

    if args.pretty:
        print(json.dumps(suggestions, indent=2, sort_keys=False))
    else:
        print(json.dumps(suggestions))


if __name__ == "__main__":
    main()


