#!/usr/bin/env python3
"""
Export full transcripts of healthy Jyoti conversations from Firestore + ElevenLabs.

"Healthy" = at least 3 user turns + 100 chars of user speech (worker actually engaged).

Usage:
    source env_vars.sh && uv run python scripts/export_jyoti_healthy_transcripts.py [--limit N]
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elevenlabs import ElevenLabs
from utils.db import fs


OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jyoti_healthy_transcripts.json")
MIN_USER_TURNS = 3
MIN_USER_CHARS = 100


def fetch_transcript(client: ElevenLabs, conversation_id: str):
    """Returns (turns_list, is_healthy) where turns are {role, text, time_secs}."""
    if not conversation_id:
        return [], False
    try:
        result = client.conversational_ai.conversations.get(conversation_id=conversation_id)
        raw_turns = getattr(result, "transcript", None) or []
        turns = []
        for t in raw_turns:
            turns.append({
                "role": getattr(t, "role", ""),
                "text": getattr(t, "message", "").strip(),
                "time_secs": getattr(t, "time_in_call_secs", 0),
            })

        user_turns = [t for t in turns if t["role"] == "user" and t["text"]]
        user_chars = sum(len(t["text"]) for t in user_turns)
        is_healthy = len(user_turns) >= MIN_USER_TURNS and user_chars >= MIN_USER_CHARS
        return turns, is_healthy
    except Exception as e:
        print(f"  ⚠️  ElevenLabs fetch failed for {conversation_id}: {e}")
        return [], False


def turns_to_text(turns: list) -> str:
    lines = []
    for t in turns:
        role = "Jyoti" if t["role"] == "agent" else "Worker"
        if t["text"]:
            lines.append(f"{role}: {t['text']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max records to check (0 = all)")
    args = parser.parse_args()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not set — source env_vars.sh first")
        sys.exit(1)

    el_client = ElevenLabs(api_key=api_key)

    print("🔍 Loading switch_caller_memory from Firestore...")
    all_docs = list(fs.collection("switch_caller_memory").stream())
    print(f"   {len(all_docs)} total records")

    if args.limit:
        all_docs = all_docs[:args.limit]
        print(f"   Limited to first {args.limit}")

    results = []
    healthy_count = 0
    skipped = 0

    for i, doc in enumerate(all_docs, 1):
        data = doc.to_dict()
        phone = doc.id
        conv_id = data.get("last_conversation_id", "")
        name = data.get("name", "")
        outcome = data.get("last_outcome", "unknown")
        profile = data.get("profile", {})
        known = data.get("known_details", {})
        summary = data.get("last_conversation_summary", "")

        print(f"[{i}/{len(all_docs)}] {phone} | conv_id={conv_id[:30]}...")

        turns, is_healthy = fetch_transcript(el_client, conv_id)

        if not is_healthy:
            user_turns = sum(1 for t in turns if t["role"] == "user" and t["text"])
            print(f"  ⏭  Skipped (user_turns={user_turns}, total_turns={len(turns)})")
            skipped += 1
            time.sleep(0.2)
            continue

        healthy_count += 1
        transcript_text = turns_to_text(turns)
        print(f"  ✅ Healthy — {len(turns)} turns, {len(transcript_text)} chars")

        results.append({
            "phone": phone,
            "name": name,
            "total_calls": data.get("total_calls", 0),
            "last_outcome": outcome,
            "last_call_at": data.get("last_call_at") or 0,
            "last_call_at_human": datetime.fromtimestamp(data.get("last_call_at", 0)).strftime("%Y-%m-%d %H:%M") if data.get("last_call_at") else "",
            "conversation_id": conv_id,
            "summary": summary,
            "profile": profile,
            "known_details": known,
            "transcript_turns": turns,
            "transcript_text": transcript_text,
        })

        time.sleep(0.25)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Export complete")
    print(f"   Healthy conversations: {healthy_count}")
    print(f"   Skipped (thin):        {skipped}")
    print(f"   Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
