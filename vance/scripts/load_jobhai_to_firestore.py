"""
One-time script to load jobhai CSV data into Firestore jobhai_jobs collection.

Usage:
    python scripts/load_jobhai_to_firestore.py
"""

import csv
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jobhai_all_ncr_with_phones_20260217_144213.csv",
)

COLLECTION = "jobhai_jobs"


def load_csv_to_firestore():
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}")
        return

    batch = fs.batch()
    count = 0
    batch_size = 0

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_id = row.get("Job ID", "").strip()
            if not job_id:
                continue

            phone = row.get("Phone", "").strip()
            if not phone:
                continue

            doc = {
                "job_id": job_id,
                "title": row.get("Title", "").strip(),
                "company": row.get("Company", "").strip(),
                "category": row.get("Category", "").strip(),
                "location": row.get("Location", "").strip(),
                "city": row.get("City", "").strip(),
                "salary_min": int(row.get("Min Salary", "0").strip() or "0"),
                "salary_max": int(row.get("Max Salary", "0").strip() or "0"),
                "openings": int(row.get("Openings", "0").strip() or "0"),
                "phone": phone,
                "perks": row.get("Perks", "").strip(),
                "job_url": row.get("Job URL", "").strip(),
                "company_id": row.get("Company ID", "").strip(),
                "job_type": row.get("Job Type", "").strip(),
                "shift": row.get("Shift", "").strip(),
            }

            ref = fs.collection(COLLECTION).document(job_id)
            batch.set(ref, doc)
            batch_size += 1
            count += 1

            # Firestore batches limited to 500 operations
            if batch_size >= 400:
                batch.commit()
                print(f"  Committed {count} docs so far...")
                batch = fs.batch()
                batch_size = 0

    if batch_size > 0:
        batch.commit()

    print(f"Loaded {count} jobs into Firestore collection '{COLLECTION}'")


if __name__ == "__main__":
    load_csv_to_firestore()
