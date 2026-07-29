# Nearby business leads — DLF Cyber Hub

Builds a CSV lead list of businesses within ~2km of DLF Cyber Hub, Gurugram,
for employer-app outreach. Uses the **Google Places API (New)** — ToS-compliant,
no HTML scraping, no IP bans.

## Setup (one time)

1. Go to https://console.cloud.google.com/ → create/select a project.
2. **Enable billing** (required even for free tier — $200/mo credit covers thousands of calls).
3. APIs & Services → Library → enable **Places API (New)**.
4. Credentials → Create credentials → API key. (Optionally restrict it to Places API.)
5. Copy the key.

## Run

```bash
cd scripts/nearby-leads
export GOOGLE_MAPS_API_KEY=your_key_here

# 1. Sanity check first — 1 tile, no real spend, prints a sample:
node scrape-nearby.mjs --dry-run

# 2. Full crawl -> leads.csv
node scrape-nearby.mjs

# Tweak coverage / density / cost:
node scrape-nearby.mjs --radius 2000 --step 300   # defaults
node scrape-nearby.mjs --radius 5000 --step 350   # wider area
node scrape-nearby.mjs --step 200                 # denser (more calls, fewer misses)
```

## How it works

Nearby Search caps at **20 results per call**, so one big 2km query would miss
most businesses in a dense zone. Instead the script lays a grid of small
overlapping search circles over the area, queries each, and **dedupes by Google
place id**. `--step` controls grid spacing: smaller = more thorough but more API
calls. Default 300m over a 2km radius ≈ 130–140 tiles ≈ 130–140 API calls.

## Output: `leads.csv`

`name, primary_type, all_types, phone, website, address, rating, reviews,
status, maps_url, place_id`

Filter in Sheets/Excel: e.g. keep rows with a phone, sort by `reviews` to
prioritize established businesses, or filter `primary_type` to your worker
categories (restaurant, salon, gym, retail…).

## Cost

The field mask requests phone/website/rating → Enterprise SKU (~$35/1000 calls).
A default run (~140 calls) ≈ $5, fully inside the $200/mo free credit.
Always `--dry-run` first.
