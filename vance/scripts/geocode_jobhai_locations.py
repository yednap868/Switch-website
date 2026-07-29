"""
One-time script to geocode job locations and store lat/lng in PostgreSQL.

Uses OpenStreetMap Nominatim (free, 1 req/sec rate limit).
Groups jobs by unique location to minimize API calls.
Reuses geocode_cache.json from previous runs.

Usage:
    DATABASE_URL=postgresql://... python scripts/geocode_jobhai_locations.py
"""

import json
import os
import sys
import time

import requests
from sqlalchemy import update

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.postgres import get_db
from models.sql_models import Job

CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "geocode_cache.json",
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "SwitchApp/1.0 (job-geocoder)"}


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def geocode(location, city):
    """Geocode a location string using Nominatim. Returns (lat, lng) or None."""
    queries = [
        f"{location}, {city}, India",
        f"{location}, India",
        f"{city}, India",
    ]
    for query in queries:
        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "in"},
                headers=HEADERS,
                timeout=10,
            )
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception as e:
            print(f"    Geocode error for '{query}': {e}")
        time.sleep(1.1)
    return None


def main():
    print("Loading jobs from PostgreSQL...")
    db = get_db()
    try:
        jobs = db.query(Job.job_id, Job.location, Job.city, Job.lat).all()
        print(f"Found {len(jobs)} jobs")

        already_geocoded = sum(1 for j in jobs if j.lat is not None)
        print(f"{already_geocoded} already have lat/lng")

        location_groups = {}
        for job in jobs:
            if job.lat is not None:
                continue
            loc = (job.location or "").strip()
            city = (job.city or "").strip()
            key = f"{loc}|{city}"
            if key not in location_groups:
                location_groups[key] = {"location": loc, "city": city}

        print(f"{len(location_groups)} unique locations to geocode")
        if not location_groups:
            print("Nothing to do.")
            return

        cache = load_cache()
        print(f"Loaded cache with {len(cache)} entries")

        from_cache = 0
        api_calls = 0
        failed = 0

        for i, (key, info) in enumerate(location_groups.items()):
            loc = info["location"]
            city = info["city"]

            if key in cache:
                coords = cache[key]
                from_cache += 1
            else:
                coords = geocode(loc, city)
                cache[key] = coords
                api_calls += 1
                if api_calls % 50 == 0:
                    save_cache(cache)
                    print(f"  Progress: {i+1}/{len(location_groups)}, {api_calls} API calls, cache saved")

            if coords:
                lat, lng = coords
                db.execute(
                    update(Job)
                    .where(Job.location == loc)
                    .where(Job.city == city)
                    .where(Job.lat.is_(None))
                    .values(lat=lat, lng=lng)
                )
            else:
                failed += 1

            if (i + 1) % 200 == 0:
                db.commit()
                print(f"  {i+1}/{len(location_groups)} locations done, committed")

        db.commit()
        save_cache(cache)

        final_count = db.query(Job).filter(Job.lat.isnot(None)).count()
        print(f"\nDone! {final_count}/{len(jobs)} jobs now have coordinates")
        print(f"  From cache: {from_cache}, API calls: {api_calls}, Failed: {failed}")
    finally:
        db.close()


if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    main()
