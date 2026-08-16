#!/usr/bin/env python3
"""
Scrape an outbound call sheet (restaurants / hotels / PGs / hostels / cafes /
banquets / cloud kitchens) across Gurgaon using the Google Places API (New),
and write it in the same format as the cyberhub call sheets.

USAGE
  export GOOGLE_MAPS_API_KEY="your-key"      # Places API (New) must be enabled
  python3 outreach/scrape-outbound.py                 # ~300 leads (default)
  python3 outreach/scrape-outbound.py --target 500    # more leads
  python3 outreach/scrape-outbound.py --out outreach/my-sheet.csv

NOTES
  - Real data only. Rows without a phone number are skipped.
  - De-duplicated by Google place id.
  - Text Search returns up to 60 results per query (3 pages of 20), so we run
    many category x locality queries to reach the target.
"""
import os, sys, csv, json, time, re, argparse, urllib.request, urllib.error


def norm_phone(p):
    """Return a clean +91 E.164 number, or '' if none."""
    if not p:
        return ""
    d = re.sub(r"\D", "", p)
    if not d:
        return ""
    if d.startswith("91") and len(d) == 12:
        return "+" + d
    d = d.lstrip("0")
    return "+91" + d if d else ""

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.nationalPhoneNumber",
    "places.rating", "places.userRatingCount", "places.formattedAddress",
    "places.googleMapsUri", "places.websiteUri", "places.primaryType",
    "nextPageToken",
])

# Business categories -> the "Priority"/segment label + roles Switch can staff
CATEGORIES = [
    ("Restaurant",     "Waiter, Kitchen Helper, Cook, Dishwasher"),
    ("Hotel",          "Housekeeping, F&B Steward, Kitchen Helper, Security"),
    ("PG / Paying Guest", "Cook, Housekeeping, Caretaker"),
    ("Hostel",         "Cook, Housekeeping, Caretaker"),
    ("Cafe",           "Barista, Waiter, Kitchen Helper"),
    ("Banquet Hall",   "Waiter, Bartender, Housekeeping, Helper"),
    ("Cloud Kitchen",  "Kitchen Helper, Cook, Dishwasher, Packer"),
]

# Gurgaon localities to canvass (add/remove as needed)
LOCALITIES = [
    "Sector 14 Gurgaon", "Sector 15 Gurgaon", "Sector 29 Gurgaon",
    "Sector 31 Gurgaon", "Sector 39 Gurgaon", "Sector 43 Gurgaon",
    "Sector 44 Gurgaon", "Sector 45 Gurgaon", "Sector 47 Gurgaon",
    "Sector 49 Gurgaon", "Sector 50 Gurgaon", "Sector 52 Gurgaon",
    "Sector 54 Gurgaon", "Sector 56 Gurgaon", "Sector 57 Gurgaon",
    "DLF Phase 1 Gurgaon", "DLF Phase 3 Gurgaon", "DLF Phase 5 Gurgaon",
    "Cyber City Gurgaon", "Cyber Hub Gurgaon", "Udyog Vihar Gurgaon",
    "Sohna Road Gurgaon", "Golf Course Road Gurgaon", "MG Road Gurgaon",
    "Sushant Lok Gurgaon", "Palam Vihar Gurgaon", "Sector 22 Gurgaon",
    "New Gurgaon Sector 82", "Sector 65 Gurgaon", "Sector 67 Gurgaon",
]


def post(body, retries=3):
    data = json.dumps(body).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="ignore")
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"  ! HTTP {e.code}: {msg[:200]}", file=sys.stderr)
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            print(f"  ! {e}", file=sys.stderr)
            return None


def search(query):
    """Yield place dicts for a text query, following up to 3 pages."""
    body = {"textQuery": query, "pageSize": 20}
    for _ in range(3):
        res = post(body)
        if not res:
            return
        for p in res.get("places", []):
            yield p
        token = res.get("nextPageToken")
        if not token:
            return
        time.sleep(2)  # nextPageToken needs a short delay to activate
        body = {"textQuery": query, "pageSize": 20, "pageToken": token}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=300)
    ap.add_argument("--out", default="outreach/gurgaon-hospitality-callsheet.csv")
    args = ap.parse_args()

    if not API_KEY:
        sys.exit("ERROR: set GOOGLE_MAPS_API_KEY (Places API New must be enabled).")

    header = ["Priority", "Business Name", "Type", "phone_number", "Rating", "Reviews",
              "Address", "Maps Link", "Website", "Status", "Roles Needed",
              "Headcount", "Next Follow-up", "Notes"]
    seen, rows = set(), []

    # Locality-outer, category-inner => interleaves segments so the sheet is a
    # mix of restaurants, hotels, PGs, hostels, cafes, banquets & cloud kitchens
    # rather than 300 of the first category.
    for loc in LOCALITIES:
        if len(rows) >= args.target:
            break
        for cat, roles in CATEGORIES:
            if len(rows) >= args.target:
                break
            q = f"{cat} in {loc}"
            print(f"[{len(rows):>3}/{args.target}] {q}")
            for p in search(q):
                pid = p.get("id")
                phone = p.get("nationalPhoneNumber")
                if not pid or pid in seen or not phone:
                    continue          # real, dialable, unique only
                seen.add(pid)
                rows.append([
                    cat,
                    p.get("displayName", {}).get("text", ""),
                    p.get("primaryType", ""),
                    norm_phone(phone),
                    p.get("rating", ""),
                    p.get("userRatingCount", ""),
                    p.get("formattedAddress", ""),
                    p.get("googleMapsUri", ""),
                    p.get("websiteUri", ""),
                    "New", roles, "", "", "",
                ])
                if len(rows) >= args.target:
                    break
        if len(rows) >= args.target:
            break

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"\nDone. Wrote {len(rows)} leads with phone numbers -> {args.out}")


if __name__ == "__main__":
    main()
