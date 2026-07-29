"""
Load jobs from CSV into PostgreSQL jobs table.
Run once after deploy to seed job data.

Usage:
    DATABASE_URL=postgresql://... python scripts/load_jobs_to_postgres.py
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.postgres import create_tables, get_db
from models.sql_models import Job

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jobhai_all_ncr_with_phones_20260217_144213.csv",
)


def load_jobs(csv_path: str = CSV_PATH):
    create_tables()

    db = get_db()
    try:
        existing_count = db.query(Job).count()
        if existing_count > 0:
            print(f"[LOADER] {existing_count} jobs already exist — skipping load")
            return

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                job = Job(
                    job_id=row.get("Job ID", ""),
                    title=row.get("Title", ""),
                    company=row.get("Company", ""),
                    category=row.get("Category", ""),
                    location=row.get("Location", ""),
                    city=row.get("City", ""),
                    salary_min=int(row.get("Min Salary", 0) or 0),
                    salary_max=int(row.get("Max Salary", 0) or 0),
                    openings=int(row.get("Openings", 0) or 0),
                    job_type=row.get("Job Type", "Full Time"),
                    shift=row.get("Shift", ""),
                    min_exp=int(row.get("Min Exp", 0) or 0),
                    max_exp=int(row.get("Max Exp", 0) or 0),
                    perks=row.get("Perks", ""),
                    phone=row.get("Phone", ""),
                    job_url=row.get("Job URL", ""),
                    company_id=row.get("Company ID", ""),
                    created_at=time.time(),
                )
                db.add(job)
                count += 1

                if count % 100 == 0:
                    db.flush()
                    print(f"  Loaded {count} jobs...")

        db.commit()
        print(f"[LOADER] Loaded {count} jobs into PostgreSQL")
    finally:
        db.close()


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    load_jobs()
