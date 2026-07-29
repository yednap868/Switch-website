"""
Firebase initialization module.
Ensures Firebase is properly initialized for the entire application.
"""

import base64
import json
import os
import tempfile

import firebase_admin
from firebase_admin import credentials, firestore

FIREBASE_AVAILABLE = False
fs = None


def initialize_firebase():
    """Initialize Firebase with proper credentials."""
    global FIREBASE_AVAILABLE, fs

    if FIREBASE_AVAILABLE:
        return True

    try:
        # Check if already initialized
        if firebase_admin._apps:
            FIREBASE_AVAILABLE = True
            fs = firestore.client()
            return True

        # Try loading credentials from JSON env var first (for Railway/cloud)
        cred = None
        cred_json_env = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if cred_json_env:
            try:
                cred_dict = json.loads(cred_json_env)
            except json.JSONDecodeError:
                cred_dict = json.loads(base64.b64decode(cred_json_env))
            cred = credentials.Certificate(cred_dict)
            # Also write to a temp file for libraries that need GOOGLE_APPLICATION_CREDENTIALS path
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
                json.dump(cred_dict, tmp)
                tmp.close()
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
            print("✅ [FIREBASE] Loaded credentials from FIREBASE_CREDENTIALS_JSON env var")

        # Fall back to file-based credentials
        if not cred:
            cred_paths = [
                "relay-15824-ef77fd8f9190.json",
                "relay-15824-firebase-adminsdk-fbsvc-bc0efb42d8.json",
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "relay-15824-ef77fd8f9190.json",
                ),
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "relay-15824-firebase-adminsdk-fbsvc-bc0efb42d8.json",
                ),
                os.getenv("FIREBASE_CREDENTIALS_PATH"),
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            ]

            cred_path = None
            for path in cred_paths:
                if path and os.path.exists(path):
                    cred_path = path
                    break

            if not cred_path:
                print("⚠️ [FIREBASE] Credentials file not found")
                return False

            cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

        fs = firestore.client()

        FIREBASE_AVAILABLE = True
        print("✅ [FIREBASE] Successfully initialized")
        return True

    except Exception as e:
        print(f"❌ [FIREBASE] Initialization failed: {e}")
        return False


# Initialize on import
initialize_firebase()
