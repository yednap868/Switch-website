"""
Bolna Voice AI integration for Switch employer outbound calls.
Triggers AI-powered calls to employers when candidates apply for jobs.
"""

import os
import sys
import threading
import time

import requests

from models.sql_models import Job, User, EmployerCall
from utils.postgres import get_db

BOLNA_API_KEY = os.getenv("BOLNA_API_KEY", "")
BOLNA_API_URL = "https://api.bolna.ai/call"
EMPLOYER_AGENT_ID = os.getenv("BOLNA_EMPLOYER_AGENT_ID", "")

if BOLNA_API_KEY and EMPLOYER_AGENT_ID:
    print(f"[BOLNA] Initialized — agent={EMPLOYER_AGENT_ID[:8]}..., key={BOLNA_API_KEY[:8]}...", flush=True)
else:
    print(f"[BOLNA] WARNING: Missing credentials — key={'set' if BOLNA_API_KEY else 'MISSING'}, agent={'set' if EMPLOYER_AGENT_ID else 'MISSING'}", flush=True)


def call_employer(job_id: str, user_id: str):
    """Trigger Bolna outbound call to employer about an interested candidate.

    Runs in a background thread to avoid blocking the apply response.
    """
    print(f"[BOLNA] Spawning employer call thread for job={job_id}, user={user_id}", flush=True)
    thread = threading.Thread(
        target=_call_employer_sync,
        args=(job_id, user_id),
        daemon=True,
    )
    thread.start()


def _call_employer_sync(job_id: str, user_id: str):
    try:
        print(f"[BOLNA] Thread started for job={job_id}", flush=True)

        db = get_db()
        try:
            job_row = db.query(Job).filter_by(job_id=job_id).first()
            if not job_row:
                print(f"[BOLNA] Job {job_id} not found, skipping employer call", flush=True)
                return
            job = job_row.to_dict()

            employer_phone = (job.get("phone") or "").strip()
            if not employer_phone:
                print(f"[BOLNA] No employer phone for job {job_id}, skipping call", flush=True)
                return

            if not employer_phone.startswith("+"):
                if len(employer_phone) == 10:
                    employer_phone = f"+91{employer_phone}"
                else:
                    employer_phone = f"+{employer_phone}"

            user_row = db.query(User).filter_by(phone=user_id).first()
            candidate_name = "Candidate"
            candidate_experience = "Not specified"
            candidate_location = "NCR"
            candidate_phone = user_id
            if user_row:
                candidate_name = user_row.name or "Candidate"
                candidate_experience = user_row.experience or "Not specified"
                candidate_location = user_row.location or "NCR"
                candidate_phone = user_row.phone or user_id
        finally:
            db.close()

        if not BOLNA_API_KEY or not EMPLOYER_AGENT_ID:
            print(f"[BOLNA] Missing API key or agent ID, skipping call to {employer_phone}", flush=True)
            return

        payload = {
            "agent_id": EMPLOYER_AGENT_ID,
            "recipient_phone_number": employer_phone,
            "user_data": {
                "candidate_name": candidate_name or "Candidate",
                "candidate_experience": candidate_experience or "Fresher",
                "candidate_location": candidate_location or "NCR",
                "candidate_phone": candidate_phone or user_id,
                "job_role": job.get("title", ""),
                "job_company": job.get("company", ""),
                "job_salary": f"{job.get('salary_min', 0)}-{job.get('salary_max', 0)}",
                "job_location": job.get("location", ""),
            },
        }

        print(f"[BOLNA] Calling employer {employer_phone} for {job.get('title')} at {job.get('company')}", flush=True)

        resp = requests.post(
            BOLNA_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {BOLNA_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            execution_id = data.get("execution_id", "")
            print(f"[BOLNA] Employer call queued: {employer_phone} for job {job_id}, execution={execution_id}", flush=True)

            db = get_db()
            try:
                call_record = EmployerCall(
                    execution_id=execution_id or job_id,
                    job_id=job_id,
                    user_id=user_id,
                    employer_phone=employer_phone,
                    status="queued",
                    created_at=time.time(),
                )
                db.add(call_record)
                db.commit()
            finally:
                db.close()
        else:
            print(f"[BOLNA] Employer call failed: {resp.status_code} {resp.text}", flush=True)

    except Exception as e:
        print(f"[BOLNA] Error calling employer for job {job_id}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
