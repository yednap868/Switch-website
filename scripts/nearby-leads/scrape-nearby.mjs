#!/usr/bin/env node
/**
 * Build a lead list of businesses near DLF Cyber Hub, Gurugram, for
 * employer-app signups, using the Google Places API (New).
 *
 * Why tiling: Nearby Search returns at most 20 results per call. A single
 * 2km-radius query in a dense area like Cyber City silently caps out and
 * misses most businesses. We cover the area with a grid of small overlapping
 * circles, dedupe by place id, and that gets us (close to) all of them.
 *
 * Usage:
 *   export GOOGLE_MAPS_API_KEY=your_key_here
 *   node scrape-nearby.mjs                 # full run -> leads.csv
 *   node scrape-nearby.mjs --dry-run       # 1 tile, prints sample, no full crawl
 *   node scrape-nearby.mjs --radius 2000 --step 300
 *
 * Cost note: each tile = 1 Nearby Search call. With phone/website/rating in the
 * field mask you're on the Enterprise SKU (~$35/1000 calls, $200/mo free credit
 * covers ~5–6k calls). --dry-run first to sanity-check before spending.
 */

// --- Config -----------------------------------------------------------------

const args = process.argv.slice(2);
const flag = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i !== -1 && args[i + 1] ? args[i + 1] : def;
};
const has = (name) => args.includes(`--${name}`);

// Default: DLF Cyber Hub, Gurugram. Override with --lat/--lng/--label.
const CENTER = {
  lat: Number(flag('lat', 28.49491)),
  lng: Number(flag('lng', 77.08886)),
};
const LABEL = flag('label', 'DLF Cyber Hub');

const RADIUS_M = Number(flag('radius', 2000)); // coverage radius around center
const STEP_M = Number(flag('step', 300));      // grid spacing; smaller = denser/pricier
const TILE_RADIUS_M = Math.round(STEP_M * 0.8); // per-tile search radius (slight overlap)
const MAX_PER_TILE = 20;                         // API hard cap
const DRY_RUN = has('dry-run');
const OUT = flag('out', 'leads.csv');

const API_KEY = process.env.GOOGLE_MAPS_API_KEY;
if (!API_KEY) {
  console.error('Missing GOOGLE_MAPS_API_KEY env var.');
  console.error('Get one: https://console.cloud.google.com/ -> enable "Places API (New)" -> create key');
  console.error('Then: export GOOGLE_MAPS_API_KEY=...');
  process.exit(1);
}

const ENDPOINT = 'https://places.googleapis.com/v1/places:searchNearby';
// Fields we pull straight from Nearby Search (no separate Details call needed).
const FIELD_MASK = [
  'places.id',
  'places.displayName',
  'places.primaryType',
  'places.types',
  'places.formattedAddress',
  'places.location',
  'places.nationalPhoneNumber',
  'places.internationalPhoneNumber',
  'places.websiteUri',
  'places.rating',
  'places.userRatingCount',
  'places.businessStatus',
  'places.googleMapsUri',
].join(',');

// --- Geo helpers ------------------------------------------------------------

const M_PER_DEG_LAT = 111_320;
const mPerDegLng = (lat) => 111_320 * Math.cos((lat * Math.PI) / 180);

// Build a grid of tile centers covering a RADIUS_M circle around CENTER.
function buildGrid() {
  const tiles = [];
  const latStep = STEP_M / M_PER_DEG_LAT;
  const lngStep = STEP_M / mPerDegLng(CENTER.lat);
  const steps = Math.ceil(RADIUS_M / STEP_M);
  for (let i = -steps; i <= steps; i++) {
    for (let j = -steps; j <= steps; j++) {
      const lat = CENTER.lat + i * latStep;
      const lng = CENTER.lng + j * lngStep;
      // keep tiles whose center is within the coverage circle
      const dy = (lat - CENTER.lat) * M_PER_DEG_LAT;
      const dx = (lng - CENTER.lng) * mPerDegLng(CENTER.lat);
      if (Math.hypot(dx, dy) <= RADIUS_M) tiles.push({ lat, lng });
    }
  }
  return tiles;
}

// --- API --------------------------------------------------------------------

async function searchTile(tile, attempt = 1) {
  const body = {
    maxResultCount: MAX_PER_TILE,
    locationRestriction: {
      circle: {
        center: { latitude: tile.lat, longitude: tile.lng },
        radius: TILE_RADIUS_M,
      },
    },
    rankPreference: 'DISTANCE',
  };
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Goog-Api-Key': API_KEY,
      'X-Goog-FieldMask': FIELD_MASK,
    },
    body: JSON.stringify(body),
  });

  if (res.status === 429 && attempt <= 5) {
    const wait = 1000 * attempt;
    await new Promise((r) => setTimeout(r, wait));
    return searchTile(tile, attempt + 1);
  }
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt.slice(0, 300)}`);
  }
  const json = await res.json();
  return json.places || [];
}

// --- CSV --------------------------------------------------------------------

const csvCell = (v) => {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

function toCsv(rows) {
  const headers = [
    'name', 'primary_type', 'all_types', 'phone', 'website',
    'address', 'rating', 'reviews', 'status', 'maps_url', 'place_id',
  ];
  const lines = [headers.join(',')];
  for (const p of rows) {
    lines.push([
      p.displayName?.text,
      p.primaryType,
      (p.types || []).join('|'),
      p.nationalPhoneNumber || p.internationalPhoneNumber,
      p.websiteUri,
      p.formattedAddress,
      p.rating,
      p.userRatingCount,
      p.businessStatus,
      p.googleMapsUri,
      p.id,
    ].map(csvCell).join(','));
  }
  return lines.join('\n');
}

// --- Main -------------------------------------------------------------------

async function main() {
  const grid = buildGrid();
  console.log(`Center: ${CENTER.lat},${CENTER.lng} (${LABEL})`);
  console.log(`Coverage radius: ${RADIUS_M}m | grid step: ${STEP_M}m | tile radius: ${TILE_RADIUS_M}m`);
  console.log(`Tiles to query: ${DRY_RUN ? 1 : grid.length}` + (DRY_RUN ? ' (dry run)' : ''));

  const seen = new Map(); // place id -> place
  const tiles = DRY_RUN ? grid.slice(0, 1) : grid;
  let done = 0;

  for (const tile of tiles) {
    let places;
    try {
      places = await searchTile(tile);
    } catch (e) {
      console.error(`\n  tile error: ${e.message}`);
      continue;
    }
    for (const p of places) if (p.id && !seen.has(p.id)) seen.set(p.id, p);
    done++;
    process.stdout.write(`\r  queried ${done}/${tiles.length} tiles | unique businesses: ${seen.size}   `);
  }
  process.stdout.write('\n');

  const all = [...seen.values()];

  if (DRY_RUN) {
    console.log(`\nSample (${all.length} from 1 tile):`);
    for (const p of all.slice(0, 10)) {
      console.log(`  - ${p.displayName?.text} [${p.primaryType || '?'}] ${p.nationalPhoneNumber || 'no phone'} ${p.websiteUri || ''}`);
    }
    console.log('\nLooks right? Run without --dry-run for the full crawl.');
    return;
  }

  const withPhone = all.filter((p) => p.nationalPhoneNumber || p.internationalPhoneNumber).length;
  const withSite = all.filter((p) => p.websiteUri).length;

  const { writeFileSync } = await import('node:fs');
  writeFileSync(OUT, toCsv(all));

  console.log(`\n===== RESULTS =====`);
  console.log(`Total unique businesses : ${all.length}`);
  console.log(`  with phone number     : ${withPhone}`);
  console.log(`  with website          : ${withSite}`);
  console.log(`Saved -> ${OUT}`);
  console.log(`API calls made          : ${tiles.length}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
