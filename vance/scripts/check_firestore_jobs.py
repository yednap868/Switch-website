"""
Quick script to check all jobs and businesses in Firestore.

Usage:
    uv run python scripts/check_firestore_jobs.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def check():
    print("=" * 60)
    print("BUSINESSES in Firestore")
    print("=" * 60)
    biz_count = 0
    for doc in fs.collection("businesses").stream():
        biz = doc.to_dict()
        biz_count += 1
        print(f"  [{doc.id}] {biz.get('name')} — {biz.get('area')}")

    print(f"\nTotal businesses: {biz_count}")

    print("\n" + "=" * 60)
    print("JOBS in Firestore")
    print("=" * 60)
    job_count = 0
    open_count = 0
    for doc in fs.collection("jobs").stream():
        job = doc.to_dict()
        job_count += 1
        status = job.get("status")
        if status == "OPEN":
            open_count += 1
        biz_id = job.get("business_id", "")
        biz_doc = fs.collection("businesses").document(biz_id).get()
        biz_name = biz_doc.to_dict().get("name", "???") if biz_doc.exists else "???"
        salary = job.get("salary_max", 0)
        salary_str = f"₹{salary:,}" if salary else "—"
        timing = job.get("interview_timing", "not set")
        print(f"  [{status}] {job.get('role')} at {biz_name} — {job.get('location')} — {salary_str} — timing: {timing}")

    print(f"\nTotal jobs: {job_count} (OPEN: {open_count})")

    print("\n" + "=" * 60)
    print("SWITCH_JOBS in Firestore")
    print("=" * 60)
    sj_count = 0
    sj_open = 0
    for doc in fs.collection("switch_jobs").stream():
        sj = doc.to_dict()
        sj_count += 1
        status = sj.get("status")
        if status == "OPEN":
            sj_open += 1
        print(f"  [{doc.id}] [{status}] {sj.get('role')} — biz_id={sj.get('business_id')} — {sj.get('location')} — salary_max={sj.get('salary_max')}")
        print(f"    keys: {list(sj.keys())}")

    print(f"\nTotal switch_jobs: {sj_count} (OPEN: {sj_open})")


if __name__ == "__main__":
    check()
