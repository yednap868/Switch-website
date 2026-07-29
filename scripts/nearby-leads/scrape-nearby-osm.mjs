#!/usr/bin/env node
/**
 * Free, no-API-key lead list of businesses near DLF Cyber Hub, Gurugram,
 * using OpenStreetMap's Overpass API. ToS-compliant, no scraping, no billing.
 *
 * Coverage of phone/website is patchier than Google's, but it's great for a
 * headcount and a starting outreach list.
 *
 * Usage:
 *   node scrape-nearby-osm.mjs                 # 2km radius -> leads-osm.csv
 *   node scrape-nearby-osm.mjs --radius 4000
 */

const args = process.argv.slice(2);
const flag = (n, d) => {
  const i = args.indexOf(`--${n}`);
  return i !== -1 && args[i + 1] ? args[i + 1] : d;
};
const CENTER = {
  lat: Number(flag('lat', 28.49491)), // default: DLF Cyber Hub, Gurugram
  lng: Number(flag('lng', 77.08886)),
};
const LABEL = flag('label', 'DLF Cyber Hub');
const RADIUS_M = Number(flag('radius', 2000));
const OUT = flag('out', 'leads-osm.csv');

// Mirrors — we try them in order if one is busy/rate-limited.
const ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
];

// What counts as "a business" worth contacting. nwr = node|way|relation.
const around = `(around:${RADIUS_M},${CENTER.lat},${CENTER.lng})`;
const QUERY = `
[out:json][timeout:90];
(
  nwr["shop"]${around};
  nwr["office"]${around};
  nwr["craft"]${around};
  nwr["amenity"~"^(restaurant|cafe|fast_food|bar|pub|food_court|ice_cream|bank|pharmacy|clinic|dentist|doctors|hospital|veterinary|fuel|car_rental|car_wash|driving_school|coworking_space|marketplace|nightclub|cinema|spa)$"]${around};
  nwr["leisure"~"^(fitness_centre|sports_centre|spa)$"]${around};
  nwr["healthcare"]${around};
  nwr["tourism"~"^(hotel|guest_house|hostel|motel)$"]${around};
);
out center tags;
`;

function dist(lat, lng) {
  const R = 6371000;
  const dLat = ((lat - CENTER.lat) * Math.PI) / 180;
  const dLng = ((lng - CENTER.lng) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((CENTER.lat * Math.PI) / 180) *
      Math.cos((lat * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

async function fetchOverpass() {
  let lastErr;
  for (const url of ENDPOINTS) {
    try {
      process.stdout.write(`Querying ${new URL(url).host} ... `);
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'data=' + encodeURIComponent(QUERY),
      });
      if (!res.ok) {
        console.log(`HTTP ${res.status}`);
        lastErr = new Error(`HTTP ${res.status}`);
        continue;
      }
      const json = await res.json();
      console.log('ok');
      return json.elements || [];
    } catch (e) {
      console.log(`failed (${e.message})`);
      lastErr = e;
    }
  }
  throw lastErr || new Error('All Overpass mirrors failed');
}

const csvCell = (v) => {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

function category(t) {
  return (
    t.shop || t.office || t.craft || t.amenity || t.leisure ||
    t.healthcare || t.tourism || 'other'
  );
}

function address(t) {
  return [t['addr:housenumber'], t['addr:street'], t['addr:suburb'], t['addr:city']]
    .filter(Boolean)
    .join(', ');
}

async function main() {
  console.log(`Center: ${CENTER.lat},${CENTER.lng} (${LABEL}) | radius ${RADIUS_M}m\n`);
  const els = await fetchOverpass();

  // Dedupe by name+category (OSM sometimes maps one place as multiple objects).
  const seen = new Map();
  let named = 0;
  for (const el of els) {
    const t = el.tags || {};
    const name = t.name || t['name:en'] || t['brand'];
    if (!name) continue; // unnamed POIs aren't useful leads
    named++;
    const lat = el.lat ?? el.center?.lat;
    const lng = el.lon ?? el.center?.lon;
    const row = {
      name,
      category: category(t),
      phone: t.phone || t['contact:phone'] || t['contact:mobile'] || '',
      website: t.website || t['contact:website'] || '',
      address: address(t),
      distance_m: lat != null ? dist(lat, lng) : '',
      osm: `https://www.openstreetmap.org/${el.type}/${el.id}`,
    };
    const key = `${name.toLowerCase()}|${row.category}`;
    if (!seen.has(key)) seen.set(key, row);
  }

  const rows = [...seen.values()].sort((a, b) => (a.distance_m || 0) - (b.distance_m || 0));

  const headers = ['name', 'category', 'phone', 'website', 'address', 'distance_m', 'osm'];
  const csv = [
    headers.join(','),
    ...rows.map((r) => headers.map((h) => csvCell(r[h])).join(',')),
  ].join('\n');

  const { writeFileSync } = await import('node:fs');
  writeFileSync(OUT, csv);

  // Breakdown by category
  const byCat = {};
  for (const r of rows) byCat[r.category] = (byCat[r.category] || 0) + 1;
  const top = Object.entries(byCat).sort((a, b) => b[1] - a[1]);

  console.log(`\n===== RESULTS (within ${RADIUS_M}m of ${LABEL}) =====`);
  console.log(`Raw OSM objects returned : ${els.length}`);
  console.log(`Named businesses         : ${named}`);
  console.log(`Unique businesses        : ${rows.length}`);
  console.log(`  with phone             : ${rows.filter((r) => r.phone).length}`);
  console.log(`  with website           : ${rows.filter((r) => r.website).length}`);
  console.log(`\nTop categories:`);
  for (const [cat, n] of top.slice(0, 15)) console.log(`  ${String(n).padStart(4)}  ${cat}`);
  console.log(`\nSaved -> ${OUT}`);
}

main().catch((e) => {
  console.error('Error:', e.message);
  process.exit(1);
});
