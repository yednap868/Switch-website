"""
Seed script to add Cyberhub business listings and job openings.

Usage:
    python scripts/seed_cyberhub_jobs.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs
from models.switch_models import Business, Job, JobStatus, BusinessType


def seed():
    businesses = [
        {
            "name": "Burma Burma",
            "area": "Cyberhub, Gurgaon",
            "address": "Burma Burma, Cyberhub, DLF Cyber City, Gurgaon",
            "business_type": BusinessType.RESTAURANT,
            "jobs": [
                {"role": "CAPTAIN", "positions_count": 1, "salary_min": 22000, "salary_max": 22000, "interview_timing": "Kal shaam 4 baje"},
            ],
        },
        {
            "name": "Chilis",
            "area": "Cyberhub, Gurgaon",
            "address": "Chilis, Cyberhub, DLF Cyber City, Gurgaon",
            "business_type": BusinessType.RESTAURANT,
            "jobs": [
                {"role": "BARTENDER", "positions_count": 1, "salary_min": 0, "salary_max": 0, "interview_timing": "Kal shaam 4 baje"},
                {"role": "ASSISTANT BARTENDER", "positions_count": 1, "salary_min": 0, "salary_max": 0, "interview_timing": "Kal shaam 4 baje"},
                {"role": "STEWARD", "positions_count": 1, "salary_min": 0, "salary_max": 0, "interview_timing": "Kal shaam 4 baje"},
            ],
        },
        {
            "name": "Soi 7",
            "area": "Cyberhub, Gurgaon",
            "address": "Soi 7, Cyberhub, DLF Cyber City, Gurgaon",
            "business_type": BusinessType.RESTAURANT,
            "jobs": [
                {"role": "HOSTESS", "positions_count": 1, "salary_min": 0, "salary_max": 0, "interview_timing": "Kal shaam 4 baje"},
                {"role": "CLEANER", "positions_count": 1, "salary_min": 0, "salary_max": 0, "interview_timing": "Kal shaam 4 baje"},
            ],
        },
    ]

    for biz in businesses:
        business_id = f"business_{biz['name'].lower().replace(' ', '_')}"

        business = Business(
            id=business_id,
            phone="",
            name=biz["name"],
            contact_person="",
            business_type=biz["business_type"],
            area=biz["area"],
            address=biz["address"],
        )
        fs.collection("businesses").document(business_id).set(business.model_dump())
        print(f"✅ Created business: {biz['name']}")

        for job_info in biz["jobs"]:
            job_id = f"job_{business_id}_{job_info['role'].lower().replace(' ', '_')}"
            job = Job(
                id=job_id,
                business_id=business_id,
                role=job_info["role"],
                positions_count=job_info["positions_count"],
                positions_filled=0,
                salary_min=job_info["salary_min"],
                salary_max=job_info["salary_max"],
                experience_required="",
                location="Cyberhub, Gurgaon",
                interview_address=biz["address"],
                interview_timing=job_info.get("interview_timing"),
                status=JobStatus.OPEN,
            )
            fs.collection("jobs").document(job_id).set(job.model_dump())
            salary_str = f"₹{job_info['salary_max']:,}" if job_info["salary_max"] else "TBD"
            print(f"   📋 Created job: {job_info['role']} at {biz['name']} — {salary_str}")

    print("\n🎉 Done! All Cyberhub businesses and jobs seeded.")


if __name__ == "__main__":
    seed()
