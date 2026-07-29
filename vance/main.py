# pylint: disable=no-member
import base64
import json
import os
import tempfile

from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(dotenv_path=".env")

# Write Firebase credentials JSON to a temp file BEFORE any other imports.
# This must happen first because gmail/cred.py uses google.auth.default()
# at import time which requires GOOGLE_APPLICATION_CREDENTIALS to be set.
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    _cred_written = False
    # Try raw JSON first
    _raw = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
    if _raw:
        try:
            _cred_dict = json.loads(_raw)
            _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(_cred_dict, _tmp)
            _tmp.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name
            _cred_written = True
            print(f"[STARTUP] Firebase credentials from JSON env var → {_tmp.name}")
        except Exception as e:
            print(f"[STARTUP] FIREBASE_CREDENTIALS_JSON parse failed: {e}")
    # Try base64-encoded credentials
    _b64 = os.getenv("FIREBASE_CREDENTIALS_BASE64", "").strip()
    if _b64 and not _cred_written:
        try:
            _decoded = base64.b64decode(_b64).decode("utf-8")
            _cred_dict = json.loads(_decoded)
            _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(_cred_dict, _tmp)
            _tmp.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name
            _cred_written = True
            print(f"[STARTUP] Firebase credentials from BASE64 env var → {_tmp.name}")
        except Exception as e:
            print(f"[STARTUP] FIREBASE_CREDENTIALS_BASE64 parse failed: {e}")

import uvicorn

from api.app import get_fastapi_app
from utils.postgres import create_tables

# Get the FastAPI app
app = get_fastapi_app()

# Create PostgreSQL tables (idempotent)
create_tables()

# Additive schema migrations (ALTER TABLE is outside create_tables' scope).
try:
    from scripts.add_kyc_columns import run as _add_kyc_columns
    _add_kyc_columns()
except Exception as _e:
    print(f"[STARTUP] add_kyc_columns migration skipped: {_e}")

try:
    from scripts.add_post_card_columns import run as _add_post_card_columns
    _add_post_card_columns()
except Exception as _e:
    print(f"[STARTUP] add_post_card_columns migration skipped: {_e}")


def main():
    """
    Starts supporting threads for reminders and morning briefs and starts the API server.
    """
    config = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=2,  # Set to 2 workers as requested
        log_level="debug",
    )
    server = uvicorn.Server(config)

    server.run()


if __name__ == "__main__":
    main()
