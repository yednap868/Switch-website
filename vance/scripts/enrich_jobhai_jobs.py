"""
One-time script to enrich jobs in PostgreSQL with AI-generated descriptions.

Groups jobs by unique (title, category) pairs (~135 combos), batch-calls Claude Haiku
to generate worker-friendly descriptions, requirements, benefits, and logo emoji.
Then applies templates to all ~3,368 job rows.

Usage:
    DATABASE_URL=postgresql://... ANTHROPIC_API_KEY=... python scripts/enrich_jobhai_jobs.py
"""

import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import Anthropic
from sqlalchemy import update
from utils.postgres import get_db
from models.sql_models import Job

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jobhai_all_ncr_with_phones_20260217_144213.csv",
)
BATCH_SIZE = 10

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def load_csv_experience():
    """Load min_exp/max_exp from CSV keyed by job_id."""
    exp_map = {}
    if not os.path.exists(CSV_PATH):
        print(f"CSV not found: {CSV_PATH}, skipping experience backfill")
        return exp_map
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_id = row.get("Job ID", "").strip()
            if not job_id:
                continue
            min_exp = row.get("Min Exp", "0").strip() or "0"
            max_exp = row.get("Max Exp", "0").strip() or "0"
            exp_map[job_id] = {
                "min_exp": int(min_exp),
                "max_exp": int(max_exp),
            }
    return exp_map


def get_all_jobs():
    """Load all jobs from PostgreSQL."""
    db = get_db()
    try:
        rows = db.query(Job).all()
        jobs = []
        for row in rows:
            jobs.append({
                "job_id": row.job_id,
                "title": row.title or "",
                "category": row.category or "",
                "description": row.description or "",
                "min_exp": row.min_exp,
                "max_exp": row.max_exp,
            })
        return jobs
    finally:
        db.close()


def group_by_title_category(jobs):
    """Group jobs by (title, category) and return groups dict."""
    groups = {}
    for job in jobs:
        title = job.get("title", "").strip()
        category = job.get("category", "").strip()
        key = (title, category)
        if key not in groups:
            groups[key] = []
        groups[key].append(job)
    return groups


def generate_templates(job_types):
    """Call Claude Haiku to generate descriptions for a batch of job types.

    Args:
        job_types: list of dicts with 'title' and 'category'

    Returns:
        list of dicts with title, category, description, requirements, benefits, logo
    """
    job_list_text = "\n".join(
        f"{i+1}. Title: {jt['title']}, Category: {jt['category']}"
        for i, jt in enumerate(job_types)
    )

    prompt = f"""You are generating job descriptions for blue-collar workers in India.
For each job type below, generate:
1. "description": 2-3 sentences in simple Hinglish (Hindi-English mix) about what the job involves. Keep it practical and worker-friendly.
2. "requirements": Array of 3-5 simple requirements (documents needed, physical fitness, skills, etc.)
3. "benefits": Array of 3-5 benefits that workers care about (salary on time, PF, food, accommodation, etc.)
4. "logo": A single emoji that best represents this job type

Job types:
{job_list_text}

Respond with a JSON array. Each element must have: title, category, description, requirements, benefits, logo.
Only output the JSON array, no other text."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return json.loads(text)


def apply_enrichments(templates_map):
    """Apply generated templates to all job rows in PostgreSQL using bulk UPDATEs by title+category."""
    db = get_db()
    total_updated = 0

    try:
        for (title, category), template in templates_map.items():
            result = db.execute(
                update(Job)
                .where(Job.title == title)
                .where(Job.category == category)
                .where((Job.description == "") | (Job.description.is_(None)))
                .values(
                    description=template["description"],
                    requirements=json.dumps(template["requirements"]),
                    benefits=json.dumps(template["benefits"]),
                    logo=template["logo"],
                )
            )
            total_updated += result.rowcount
            if result.rowcount > 0:
                print(f"  {title}/{category}: {result.rowcount} rows")

        db.commit()
        print(f"Total updated: {total_updated} rows")
    finally:
        db.close()


def main():
    print("Loading jobs from PostgreSQL...")
    jobs = get_all_jobs()
    print(f"Found {len(jobs)} jobs")

    print("Loading experience data from CSV...")
    exp_map = load_csv_experience()
    print(f"Loaded experience data for {len(exp_map)} jobs")

    print("Grouping by (title, category)...")
    groups = group_by_title_category(jobs)
    print(f"Found {len(groups)} unique (title, category) combinations")

    already_enriched = sum(
        1 for job in jobs if job.get("description")
    )
    if already_enriched == len(jobs):
        print("All jobs already enriched. Nothing to do.")
        return

    if already_enriched > 0:
        print(f"{already_enriched}/{len(jobs)} already enriched, processing remaining")

    unenriched_groups = {}
    for (title, category), group_jobs in groups.items():
        unenriched = [j for j in group_jobs if not j.get("description")]
        if unenriched:
            unenriched_groups[(title, category)] = unenriched

    job_types = [
        {"title": title, "category": category}
        for (title, category) in unenriched_groups.keys()
    ]

    print(f"Generating AI descriptions for {len(job_types)} job types...")
    templates_map = {}
    batches = [
        job_types[i : i + BATCH_SIZE]
        for i in range(0, len(job_types), BATCH_SIZE)
    ]

    for i, batch_types in enumerate(batches):
        print(f"  Batch {i+1}/{len(batches)} ({len(batch_types)} types)...")
        try:
            results = generate_templates(batch_types)
            for idx, item in enumerate(results):
                if idx < len(batch_types):
                    key = (batch_types[idx]["title"], batch_types[idx]["category"])
                else:
                    key = (item["title"], item["category"])
                templates_map[key] = item
        except Exception as e:
            print(f"  Error in batch {i+1}: {e}")
            for jt in batch_types:
                templates_map[(jt["title"], jt["category"])] = {
                    "description": f"{jt['title']} ki job hai. Company mein kaam karna hoga.",
                    "requirements": ["Valid ID proof", "Basic communication skills"],
                    "benefits": ["Regular salary", "Safe workplace"],
                    "logo": "\U0001F4BC",
                    "_fallback": True,
                }
        time.sleep(0.5)

    print(f"Generated templates for {len(templates_map)} job types")

    print("Applying enrichments to PostgreSQL...")
    apply_enrichments(templates_map)
    print("Done!")


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    main()
