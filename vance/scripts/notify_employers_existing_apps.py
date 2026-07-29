"""
One-time script: Send WhatsApp notifications to employers for all existing
job applications where candidates have applied.

Sends ONE message per job (with top candidate summary), not one per candidate,
to avoid spamming employers.

Run on server:
  cd /path/to/Vance-1
  PYTHONPATH=. python scripts/notify_employers_existing_apps.py --dry-run   # preview
  PYTHONPATH=. python scripts/notify_employers_existing_apps.py             # send
"""

import sys
import time

from models.sql_models import Job, JobApplication, User
from services.employer_match_service import (
    EMPLOYER_TEMPLATE_NAME,
    _normalize_wa_phone,
    _send_via_switch,
)
from utils.postgres import get_db
from utils.whatsapp.components import MsgComponents

FRONTEND_HOST = "app.switchlocally.com"

DRY_RUN = "--dry-run" in sys.argv


def main():
    db = get_db()
    try:
        apps = db.query(JobApplication).all()
        print(f"Total applications in DB: {len(apps)}")

        # Group by job_id
        job_apps = {}
        for a in apps:
            if a.job_id not in job_apps:
                job_apps[a.job_id] = []
            job_apps[a.job_id].append(a)

        print(f"Unique jobs with applications: {len(job_apps)}")
        print()

        sent = 0
        skipped = 0
        failed = 0

        for job_id, applications in sorted(job_apps.items(), key=lambda x: -len(x[1])):
            job = db.query(Job).filter_by(job_id=job_id).first()
            if not job:
                print(f"  SKIP job {job_id} — deleted from DB")
                skipped += 1
                continue

            employer_phone = (job.phone or "").strip()
            if not employer_phone:
                print(f"  SKIP job {job_id} ({job.company} - {job.title}) — no employer phone")
                skipped += 1
                continue

            wa_phone = _normalize_wa_phone(employer_phone)

            # Build summary: top candidate name + total count
            candidate_names = []
            for app in applications:
                candidate = db.query(User).filter_by(phone=app.user_id).first()
                name = candidate.name if candidate else "Candidate"
                exp = (candidate.experience if candidate else "") or "Not specified"
                loc = (candidate.location if candidate else "") or "NCR"
                candidate_names.append(f"{name} | {exp} | {loc}")

            n = len(candidate_names)
            # Use first candidate as the summary, mention total count
            if n == 1:
                summary = candidate_names[0]
            else:
                summary = f"{candidate_names[0]} (+{n - 1} more)"

            approval_url = f"https://{FRONTEND_HOST}/hire"

            print(f"JOB: {job.company} - {job.title} ({job_id}) | employer={wa_phone} | {n} candidates")
            print(f"  summary: {summary}")

            if DRY_RUN:
                print(f"  [DRY RUN] Would send to {wa_phone}")
                sent += 1
                print()
                continue

            payload = MsgComponents.template_scaffold(
                to=wa_phone,
                template_name=EMPLOYER_TEMPLATE_NAME,
                language_code="en",
                body_parameters=[
                    job.title or "Open Position",
                    summary,
                    approval_url,
                ],
            )
            result = _send_via_switch(payload)

            if result.get("status") == "success":
                print(f"  SENT to {wa_phone}")
                sent += 1
            else:
                print(f"  FAILED: {result.get('error')}")
                failed += 1

            time.sleep(1)
            print()

        print(f"=== DONE ===")
        print(f"Sent: {sent} | Skipped: {skipped} | Failed: {failed}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
