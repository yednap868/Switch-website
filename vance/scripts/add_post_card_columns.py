"""
Add post-card automated placement pipeline columns.

Idempotent — uses ADD COLUMN IF NOT EXISTS.

    python -m scripts.add_post_card_columns
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from utils.postgres import engine

PLACEMENT_COLUMNS = [
    ("joining_time",               "TEXT"),
    ("joining_otp",                "TEXT"),
    ("backup_workers",             "TEXT DEFAULT '[]'"),
    ("replacement_batch",          "INTEGER DEFAULT 0"),
    ("evening_confirm_sent_at",    "FLOAT"),
    ("morning_nudge_sent_at",      "FLOAT"),
    ("enroute_check_sent_at",      "FLOAT"),
    ("employer_notified_enroute_at", "FLOAT"),
]

USER_COLUMNS = [
    ("chowk_streak",        "INTEGER DEFAULT 0"),
    ("yogdaan_score",       "INTEGER DEFAULT 0"),
    ("switch_priority",     "TEXT DEFAULT ''"),
    ("village",             "TEXT DEFAULT ''"),
    ("job_role",            "TEXT DEFAULT ''"),
    ("acquisition_source",  "TEXT DEFAULT ''"),
]


def run():
    with engine.begin() as conn:
        for col, typ in PLACEMENT_COLUMNS:
            sql = f"ALTER TABLE placements ADD COLUMN IF NOT EXISTS {col} {typ}"
            print(f"[MIGRATION] {sql}")
            conn.execute(text(sql))
        for col, typ in USER_COLUMNS:
            sql = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"
            print(f"[MIGRATION] {sql}")
            conn.execute(text(sql))
    print("[MIGRATION] post_card columns done.")


if __name__ == "__main__":
    run()
