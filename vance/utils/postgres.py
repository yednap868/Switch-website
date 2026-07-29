"""
PostgreSQL database utilities for Switch app.
Uses SQLAlchemy ORM with connection from DATABASE_URL env var.
"""

import json
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models.sql_models import Base

_database_url = os.getenv("DATABASE_URL", "")

# Railway uses postgres:// but SQLAlchemy requires postgresql://
if _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(_database_url, pool_pre_ping=True) if _database_url else None

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False) if engine else None


def get_db() -> Session:
    """Return a new database session. Caller must close it."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not set — cannot create PostgreSQL session")
    return SessionLocal()


def create_tables():
    """Create all tables if they don't exist. Idempotent."""
    if engine is None:
        print("[POSTGRES] DATABASE_URL not set — skipping table creation")
        return
    Base.metadata.create_all(bind=engine)
    # Add columns that SQLAlchemy won't auto-add to existing tables
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE employer_profiles ADD COLUMN IF NOT EXISTS lat FLOAT"))
            conn.execute(text("ALTER TABLE employer_profiles ADD COLUMN IF NOT EXISTS lng FLOAT"))
            for col in [
                "checkin_selfie TEXT", "checkin_lat FLOAT", "checkin_lng FLOAT",
                "checkin_otp TEXT", "checkin_at FLOAT", "checkin_location_verified BOOLEAN",
                "verify_token TEXT", "employer_verified_at FLOAT",
                "razorpay_order_id TEXT", "razorpay_payment_id TEXT",
                "payment_amount INTEGER DEFAULT 200000", "payment_status TEXT", "payment_at FLOAT",
                "first_day_checkin_token TEXT", "first_day_checkin_at FLOAT",
                "first_day_selfie TEXT", "first_day_location_verified BOOLEAN",
                "joining_date TEXT", "attendance_day_count INTEGER DEFAULT 0",
                "candidate_bonus_status TEXT DEFAULT 'pending'",
                "job_lat FLOAT", "job_lng FLOAT",
            ]:
                conn.execute(text(f"ALTER TABLE placements ADD COLUMN IF NOT EXISTS {col}"))
            for col in [
                "gender TEXT DEFAULT ''", "date_of_birth TEXT DEFAULT ''",
                "expected_salary_min INTEGER", "expected_salary_max INTEGER",
                "previous_company TEXT DEFAULT ''", "previous_role TEXT DEFAULT ''",
                "work_duration TEXT DEFAULT ''",
                "active_job_key TEXT", "joining_date TEXT", "joining_details TEXT",
                "checked_in BOOLEAN DEFAULT false",
                "training_progress TEXT DEFAULT '{}'",
                "switch_priority TEXT DEFAULT ''",
                "village TEXT DEFAULT ''",
                "job_role TEXT DEFAULT ''",
                "acquisition_source TEXT DEFAULT ''",
                "contacts_phones TEXT DEFAULT '[]'",
                "chowk_streak INTEGER DEFAULT 0",
                "yogdaan_score INTEGER DEFAULT 0",
            ]:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col}"))
            for col in [
                "kyc_verified_at DOUBLE PRECISION",
                "kyc_photo_url TEXT",
                "kyc_conversation_id TEXT",
                "kyc_answers TEXT",
            ]:
                conn.execute(text(f"ALTER TABLE job_applications ADD COLUMN IF NOT EXISTS {col}"))
            for col in [
                "joining_time TEXT",
                "joining_otp TEXT",
                "backup_workers TEXT DEFAULT '[]'",
                "replacement_batch INTEGER DEFAULT 0",
                "evening_confirm_sent_at DOUBLE PRECISION",
                "morning_nudge_sent_at DOUBLE PRECISION",
                "enroute_check_sent_at DOUBLE PRECISION",
                "employer_notified_enroute_at DOUBLE PRECISION",
            ]:
                conn.execute(text(f"ALTER TABLE placements ADD COLUMN IF NOT EXISTS {col}"))
            conn.commit()
    except Exception as e:
        print(f"[POSTGRES] Auto-migrate warning: {e}")
    print("[POSTGRES] All tables created / verified")


def parse_json_col(val):
    """Deserialize a JSON text column. Returns [] or {} on failure."""
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []
