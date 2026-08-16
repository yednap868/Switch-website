#!/usr/bin/env python3
"""
Scrape an outbound call sheet of SME companies (manufacturing / factories,
warehouses & logistics, SME offices & corporates, retail & showrooms) across
Gurgaon using the Google Places API (New), and write it in the same format as
the hospitality call sheet produced by scrape-outbound.py.

USAGE
  export GOOGLE_MAPS_API_KEY="your-key"       # Places API (New) must be enabled
  python3 outreach/scrape-sme.py                       # ~1000 leads (default)
  python3 outreach/scrape-sme.py --target 500          # fewer leads
  python3 outreach/scrape-sme.py --out outreach/my-sheet.csv

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

# SME categories -> the segment label + roles Switch can staff.
# Multiple search phrases per segment widen coverage (Places matches loosely).
CATEGORIES = [
    # Manufacturing / Factories
    ("Manufacturing company", "Helper, Machine Operator, Packer, Loader"),
    ("Factory",               "Helper, Machine Operator, Packer, Loader"),
    ("Industrial unit",       "Helper, Machine Operator, Packer, Loader"),
    # Warehouses / Logistics
    ("Warehouse",             "Picker, Packer, Loader, Forklift Operator"),
    ("Logistics company",     "Picker, Packer, Loader, Delivery Helper"),
    ("Distribution center",   "Picker, Packer, Loader, Forklift Operator"),
    # Offices / Corporate (SME)
    ("Corporate office",      "Receptionist, Office Assistant, Housekeeping, Security Guard"),
    ("Software company",      "Receptionist, Office Assistant, Housekeeping, Security Guard"),
    ("Business services company", "Receptionist, Office Assistant, Housekeeping, Security Guard"),
    # Retail / Showrooms
    ("Retail showroom",       "Sales Associate, Cashier, Store Helper, Security Guard"),
    ("Wholesale distributor", "Sales Associate, Loader, Store Helper"),
]

# Gurgaon localities to canvass, weighted toward the industrial / commercial
# belts where SMEs cluster.
LOCALITIES = [
    # Industrial belts
    "Udyog Vihar Gurgaon", "IMT Manesar Gurgaon", "Sector 37 Industrial Area Gurgaon",
    "Pace City Sector 37 Gurgaon", "Khandsa Industrial Area Gurgaon",
    "Kadipur Industrial Area Gurgaon", "Begumpur Khatola Gurgaon",
    "Sector 18 Industrial Area Gurgaon", "Dundahera Gurgaon", "Molahera Gurgaon",
    "Binola Industrial Area Gurgaon", "Bilaspur Industrial Area Gurgaon",
    # Commercial / office belts
    "Cyber City Gurgaon", "Cyber Hub Gurgaon", "Golf Course Road Gurgaon",
    "Sohna Road Gurgaon", "MG Road Gurgaon", "Golf Course Extension Road Gurgaon",
    "DLF Phase 1 Gurgaon", "DLF Phase 3 Gurgaon", "DLF Phase 5 Gurgaon",
    "Sector 44 Gurgaon", "Sector 48 Gurgaon", "Sector 32 Gurgaon",
    # New Gurgaon / Dwarka Expressway
    "New Gurgaon Sector 82 Gurgaon", "Sector 83 Gurgaon", "Sector 84 Gurgaon",
    "Dwarka Expressway Gurgaon", "Sector 90 Gurgaon", "Manesar Gurgaon",
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
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--out", default="outreach/gurgaon-sme-callsheet.csv")
    args = ap.parse_args()

    if not API_KEY:
        sys.exit("ERROR: set GOOGLE_MAPS_API_KEY (Places API New must be enabled).")

    header = ["Priority", "Business Name", "Type", "phone_number", "Rating", "Reviews",
              "Address", "Maps Link", "Website", "Status", "Roles Needed",
              "Headcount", "Next Follow-up", "Notes"]
    seen, rows = set(), []

    # Locality-outer, category-inner => interleaves segments so the sheet is a
    # mix of factories, warehouses, offices & retail rather than 1000 of the
    # first category.
    for loc in LOCALITIES:
        if len(rows) >= args.target:
            break
        for cat, roles in CATEGORIES:
            if len(rows) >= args.target:
                break
            q = f"{cat} in {loc}"
            print(f"[{len(rows):>4}/{args.target}] {q}")
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
    print(f"\nDone. Wrote {len(rows)} SME leads with phone numbers -> {args.out}")


if __name__ == "__main__":
    main()
