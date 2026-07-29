"""
Import jobseeker phone numbers from CSV files into Firestore switch_users collection.

Reads phone-number-only CSVs and creates minimal switch_users documents
with isAvailable=True so they can be found by search_matching_candidates().

Sources:
- jobsekkeer(Sheet1).csv — general jobseekers
- restauarnt staff(Sheet1) (1).csv — restaurant staff candidates
- security guards(Sheet1).csv — security guard candidates

Usage:
    python scripts/import_jobseeker_phones.py
"""

import os
import re
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def normalize_phone(phone: str) -> str:
    """Normalize phone number to 91XXXXXXXXXX format."""
    cleaned = re.sub(r"[^\d]", "", phone)
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


def parse_phones_from_file(filepath: str) -> list[str]:
    """Read phone numbers from a CSV file (one phone per line, may have headers)."""
    phones = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip header-like lines
            digits = re.sub(r"[^\d]", "", line)
            if len(digits) < 10:
                continue
            phones.append(normalize_phone(line))
    return phones


def import_phones(phones: list[str], source_tag: str, preferred_roles: list[str] = None):
    """Import phone numbers into switch_users, skipping existing docs."""
    created = 0
    skipped = 0
    now = time.time()

    for phone in phones:
        if not phone or len(phone) < 12:
            continue

        doc_ref = fs.collection("switch_users").document(phone)
        existing = doc_ref.get()

        if existing.exists:
            skipped += 1
            continue

        doc_data = {
            "user_id": phone,
            "phone": phone,
            "profile": {
                "phone": phone,
                "name": "",
                "isAvailable": True,
                "verified": False,
                "joinedDate": time.strftime("%b %Y"),
                "totalApplied": 0,
                "interviews": 0,
                "hired": 0,
                "profileComplete": 0,
                "preferredRoles": preferred_roles or [],
                "location": "",
                "experience": "",
            },
            "applications": [],
            "source": source_tag,
            "created_at": now,
            "updated_at": now,
        }

        doc_ref.set(doc_data)
        created += 1

    print(f"  {source_tag}: {created} created, {skipped} skipped (already exist)")
    return created, skipped


def main():
    downloads = os.path.expanduser("~/Downloads")

    files = [
        {
            "path": os.path.join(downloads, "jobsekkeer(Sheet1).csv"),
            "tag": "csv_jobseeker",
            "roles": [],
        },
        {
            "path": os.path.join(downloads, "restauarnt staff(Sheet1) (1).csv"),
            "tag": "csv_restaurant_staff",
            "roles": ["Waiter", "Helper", "Kitchen", "Captain"],
        },
        {
            "path": os.path.join(downloads, "security guards(Sheet1).csv"),
            "tag": "csv_security_guard",
            "roles": ["Security Guard"],
        },
    ]

    total_created = 0
    total_skipped = 0

    for f in files:
        path = f["path"]
        if not os.path.exists(path):
            print(f"  SKIP: {path} not found")
            continue

        phones = parse_phones_from_file(path)
        print(f"  Parsed {len(phones)} phones from {os.path.basename(path)}")

        created, skipped = import_phones(phones, f["tag"], f["roles"])
        total_created += created
        total_skipped += skipped

    print(f"\nDone. Total: {total_created} created, {total_skipped} skipped.")


if __name__ == "__main__":
    main()
