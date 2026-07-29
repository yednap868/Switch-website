"""
Migration: create the upi_payments table.

This script is idempotent — safe to run multiple times.
The table is also created automatically when the server starts via create_tables().
Run manually if you need to create the table before the next deploy:

    cd /Users/alt/Vance-1
    source env_vars.sh
    python scripts/add_upi_payments_table.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.postgres import engine, create_tables
from models.sql_models import UPIPayment, Base


def run():
    if engine is None:
        print("ERROR: DATABASE_URL not set. Source env_vars.sh first.")
        sys.exit(1)

    Base.metadata.create_all(bind=engine, tables=[UPIPayment.__table__])
    print("✓ upi_payments table created (or already exists)")

    from sqlalchemy import inspect, text
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("upi_payments")]
    print(f"  Columns: {', '.join(cols)}")

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM upi_payments")).scalar()
        print(f"  Existing rows: {result}")


if __name__ == "__main__":
    run()
