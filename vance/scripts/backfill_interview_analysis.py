"""
Backfill interview analysis for telephonic_interviews missing transcripts.

Downloads recordings, transcribes via Deepgram, analyzes with Claude,
and saves interview_confirmed + details back to Firestore.

Usage:
    python scripts/backfill_interview_analysis.py [--hours 6] [--dry-run]
"""

import argparse
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.live_connect_service import analyze_conference_recording
from utils.db import fs


def backfill(hours: int, dry_run: bool):
    cutoff = time.time() - 3600 * hours
    interviews = list(
        fs.collection("telephonic_interviews")
        .where("created_at", ">=", cutoff)
        .stream()
    )

    auth_id = os.getenv("VOBIZ_AUTH_ID", "")
    auth_token = os.getenv("VOBIZ_AUTH_TOKEN", "")

    needs_analysis = []
    for doc in interviews:
        iv = doc.to_dict()
        transcript = iv.get("transcript", "")
        rec_url = iv.get("recording_url", "")
        if transcript or not rec_url:
            continue
        needs_analysis.append((doc.id, iv, rec_url))

    print(f"Found {len(interviews)} interviews in last {hours} hours")
    print(f"Need analysis: {len(needs_analysis)}")
    print()

    if dry_run:
        for sid, iv, rec_url in needs_analysis:
            name = iv.get("candidate_name", "") or iv.get("candidate_phone", "")
            biz = iv.get("business_name", "")
            print(f"  [DRY RUN] {sid}: {name} <> {biz} | {rec_url[:60]}...")
        return

    success = 0
    failed = 0

    for i, (sid, iv, rec_url) in enumerate(needs_analysis):
        name = iv.get("candidate_name", "") or iv.get("candidate_phone", "")
        biz = iv.get("business_name", "")
        print(f"[{i+1}/{len(needs_analysis)}] {sid}: {name} <> {biz}")

        try:
            if "vobiz.ai" in rec_url:
                resp = httpx.get(
                    rec_url,
                    headers={"X-Auth-ID": auth_id, "X-Auth-Token": auth_token},
                    timeout=60,
                )
            else:
                resp = httpx.get(rec_url, timeout=60)

            if resp.status_code != 200:
                print(f"  SKIP: download failed ({resp.status_code})")
                failed += 1
                continue

            audio_bytes = resp.content
            content_type = "audio/mpeg" if rec_url.endswith(".mp3") else "audio/wav"
            print(f"  Downloaded {len(audio_bytes)} bytes ({content_type})")

            analyze_conference_recording(sid, audio_bytes, rec_url)
            success += 1
            print(f"  Done")
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

        print()

    print(f"{'='*60}")
    print(f"Backfill complete: {success} analyzed, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill interview analysis")
    parser.add_argument("--hours", type=int, default=6, help="Look back N hours (default: 6)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be analyzed")
    args = parser.parse_args()
    backfill(args.hours, args.dry_run)
