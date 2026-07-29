"""
Add KYC-v2 columns to job_applications table.

create_tables() does NOT ALTER existing tables, so these columns need
explicit ALTER TABLE on deploy. Run once after the video-kyc-v2 merge.

Idempotent — uses ADD COLUMN IF NOT EXISTS.

    python -m scripts.add_kyc_columns
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from utils.postgres import engine

KYC_COLUMNS = [
    ("kyc_video_url",   "TEXT"),
    ("kyc_transcript",  "TEXT"),
    ("kyc_structured",  "TEXT"),
    ("kyc_summary",     "TEXT"),
    ("kyc_agent_name",  "TEXT"),
    ("kyc_is_first",    "BOOLEAN DEFAULT TRUE"),
]


def run():
    with engine.begin() as conn:
        for col, typ in KYC_COLUMNS:
            sql = f"ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS {col} {typ}"
            print(f"[KYC_MIGRATION] {sql}")
            conn.execute(text(sql))
    print("[KYC_MIGRATION] Done.")


if __name__ == "__main__":
    run()
