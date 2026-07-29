#!/usr/bin/env python3
"""
Generate rich worker profiles from healthy Jyoti conversation transcripts.

Reads jyoti_healthy_transcripts.json (from export_jyoti_healthy_transcripts.py),
generates a blue-collar employer-facing profile per worker via Claude, and saves to:
  - Firestore: switch_worker_profiles/{phone}

Profile format (blue-collar adapted from white-collar vance.so profiles):
  - pitch:      2-3 sentence employer-facing summary
  - strengths:  4-6 concrete, specific strengths
  - work_history: structured [{role, employer, duration}]
  - best_roles: top 2-3 job types this person fits
  - quick_facts: key stats (experience, salary, area, availability)
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import Anthropic
from utils.db import fs


INPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jyoti_healthy_transcripts.json")
COLLECTION = "switch_worker_profiles"


def build_profile_prompt(worker: dict) -> str:
    profile = worker.get("profile", {})
    known = worker.get("known_details", {})
    summary = worker.get("summary", "")
    transcript = worker.get("transcript_text", "")
    name = worker.get("name") or profile.get("name") or "Worker"

    # Build a compact facts block
    facts = []
    if profile.get("experience_years"):
        facts.append(f"Experience: {profile['experience_years']}")
    if profile.get("previous_roles"):
        facts.append(f"Past roles: {', '.join(profile['previous_roles'])}")
    if profile.get("previous_employers"):
        facts.append(f"Past employers: {', '.join(profile['previous_employers'])}")
    if profile.get("desired_role"):
        facts.append(f"Wants: {profile['desired_role']}")
    if profile.get("city"):
        facts.append(f"City: {profile['city']}")
    if profile.get("preferred_areas"):
        facts.append(f"Preferred areas: {', '.join(profile['preferred_areas'])}")
    if profile.get("salary_min") or profile.get("salary_max"):
        lo = profile.get("salary_min", 0)
        hi = profile.get("salary_max", 0)
        if lo and hi:
            facts.append(f"Salary expectation: ₹{lo:,}–₹{hi:,}/month")
        elif lo:
            facts.append(f"Salary expectation: ₹{lo:,}+/month")
    if profile.get("languages"):
        facts.append(f"Languages: {', '.join(profile['languages'])}")
    if profile.get("availability"):
        facts.append(f"Availability: {profile['availability']}")
    if profile.get("employment_status"):
        facts.append(f"Currently: {profile['employment_status']}")
    if profile.get("education"):
        facts.append(f"Education: {profile['education']}")
    for k, v in known.items():
        if v and k not in ("name", "phone"):
            facts.append(f"{k.replace('_', ' ').title()}: {v}")

    facts_block = "\n".join(f"- {f}" for f in facts) if facts else "(no structured data)"

    transcript_section = ""
    if transcript:
        # Trim to 2500 chars to stay within prompt budget
        trimmed = transcript[:2500]
        if len(transcript) > 2500:
            trimmed += "\n[transcript trimmed]"
        transcript_section = f"\n\nFull conversation transcript:\n{trimmed}"
    elif summary:
        transcript_section = f"\n\nCall summary: {summary}"

    return f"""You are building a concise, employer-facing profile card for a blue-collar job candidate in India (Gurgaon/Delhi NCR).
Employers using this are hiring for roles like: waiter, delivery rider, warehouse picker, security guard, store helper, kitchen helper, cashier, factory worker.

Candidate name: {name}

Known facts:
{facts_block}{transcript_section}

Return a JSON object with exactly these keys:

- "pitch": A 2–3 sentence employer-friendly summary. Lead with experience level and role, then what makes them reliable or hireable, then current situation/availability. Be concrete — avoid generic phrases. Write in third person. Example: "Rahul has 2 years of experience as a delivery rider with Zomato in Gurgaon. He handled 40+ deliveries daily and maintained a 4.8 rating. Currently unemployed and available immediately, looking for ₹13,000/month."

- "strengths": Array of 4–6 short strings. Each should be a specific, concrete strength — not generic. Examples: "2+ years Haldiram kitchen experience", "Hindi + basic English speaker", "Lives in Sector 45 — 10 min from DLF Cyber Hub", "Available from Monday, no notice period", "Handled cash counter independently".

- "work_history": Array of objects, one per past job. Each: {{"role": "...", "employer": "...", "duration": "..."}}.  Use empty string if unknown. Only include real past jobs — do not fabricate.

- "best_roles": Array of 2–3 job type strings this person is best suited for, from this list only: [waiter, kitchen-helper, delivery-rider, warehouse-picker, security-guard, store-helper, cashier, office-cleaner, factory-helper, iti-fitter, iti-mechanical, iti-machinist, iti-welder, factory-supervisor].

- "quick_facts": Object with these keys (use empty string / 0 if unknown):
    - "experience": e.g. "2 years", "fresher", "6 months"
    - "salary_min": integer monthly minimum in ₹ (0 if unknown)
    - "salary_max": integer monthly maximum in ₹ (0 if unknown)
    - "city": current city
    - "area": preferred locality/area
    - "availability": "immediate", "1 week", "notice period", or ""
    - "languages": comma-separated string e.g. "Hindi, English"
    - "education": e.g. "10th pass", "12th pass", "ITI", "graduate", ""

Rules:
- Be specific. Use real details from the transcript/facts — don't invent.
- If the transcript shows the worker was enthusiastic, mention it. If they have a specific employer name, use it.
- Keep pitch under 60 words.
- Return ONLY valid JSON, no markdown.
"""


def generate_profile(client: Anthropic, worker: dict) -> dict:
    prompt = build_profile_prompt(worker)
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠️  Claude generation failed: {e}")
        return {}


def save_to_firestore(phone: str, worker: dict, generated: dict):
    profile = worker.get("profile", {})
    doc = {
        "phone": phone,
        "name": worker.get("name") or profile.get("name") or "",
        "total_calls": worker.get("total_calls", 0),
        "last_outcome": worker.get("last_outcome", ""),
        "last_call_at": worker.get("last_call_at") or 0,
        "conversation_id": worker.get("conversation_id", ""),
        "call_summary": worker.get("summary", ""),
        "raw_profile": profile,
        "pitch": generated.get("pitch", ""),
        "strengths": generated.get("strengths", []),
        "work_history": generated.get("work_history", []),
        "best_roles": generated.get("best_roles", []),
        "quick_facts": generated.get("quick_facts", {}),
        "generated_at": time.time(),
    }
    fs.collection(COLLECTION).document(phone).set(doc, merge=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max workers to process (0 = all)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N records")
    args = parser.parse_args()

    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        print("   Run export_jyoti_healthy_transcripts.py first.")
        sys.exit(1)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        workers = json.load(f)

    if args.offset:
        workers = workers[args.offset:]
    if args.limit:
        workers = workers[:args.limit]

    print(f"📂 Loaded {len(workers)} workers from {INPUT_FILE}")

    client = Anthropic(api_key=api_key)
    created = 0
    skipped = 0

    for i, worker in enumerate(workers, 1):
        phone = worker["phone"]
        name = worker.get("name") or worker.get("profile", {}).get("name") or "?"
        print(f"\n[{i}/{len(workers)}] {phone} | {name}")

        if not worker.get("transcript_text") and not worker.get("summary") and not worker.get("profile"):
            print("  ⚠️  No data to work with — skipping")
            skipped += 1
            continue

        generated = generate_profile(client, worker)
        if not generated:
            skipped += 1
            continue

        save_to_firestore(phone, worker, generated)
        created += 1
        print(f"  ✅ Saved to {COLLECTION}/{phone}")
        print(f"     Pitch: {generated.get('pitch', '')[:80]}...")
        print(f"     Best roles: {generated.get('best_roles', [])}")

        # Respect rate limits
        if i < len(workers):
            time.sleep(0.5)

    print(f"\n✅ Done. Profiles generated: {created}, skipped: {skipped}")
    print(f"   Firestore collection: {COLLECTION}")


if __name__ == "__main__":
    main()
