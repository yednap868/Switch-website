// Text Search (New) for cloud kitchens around Gurugram / DLF Cyber Hub.
// Usage: GOOGLE_MAPS_API_KEY=key node scrape-cloud-kitchens.mjs
import fs from 'node:fs';

const KEY = process.env.GOOGLE_MAPS_API_KEY;
if (!KEY) { console.error('Set GOOGLE_MAPS_API_KEY'); process.exit(1); }

const ENDPOINT = 'https://places.googleapis.com/v1/places:searchText';
// Bias results to a circle around DLF Cyber Hub, Gurugram.
const CENTER = { latitude: 28.4949, longitude: 77.0895 };
const RADIUS = 8000; // metres

const QUERIES = [
  'cloud kitchen in Gurugram',
  'cloud kitchen near DLF Cyber Hub Gurugram',
  'cloud kitchen Udyog Vihar Gurugram',
  'cloud kitchen Sector 24 Gurugram',
  'cloud kitchen Sector 29 Gurugram',
  'cloud kitchen MG Road Gurugram',
  'delivery only kitchen Gurugram',
  'central kitchen Gurugram',
  'tiffin service Gurugram',
  'catering kitchen Gurugram',
];

const FIELDS = [
  'places.displayName','places.primaryType','places.types',
  'places.nationalPhoneNumber','places.internationalPhoneNumber',
  'places.formattedAddress','places.rating','places.userRatingCount',
  'places.websiteUri','places.googleMapsUri','places.id',
  'nextPageToken',
].join(',');

async function search(textQuery, pageToken) {
  const body = { textQuery, locationBias: { circle: { center: CENTER, radius: RADIUS } }, pageSize: 20 };
  if (pageToken) body.pageToken = pageToken;
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': KEY, 'X-Goog-FieldMask': FIELDS },
    body: JSON.stringify(body),
  });
  if (!res.ok) { console.error('HTTP', res.status, await res.text()); return { places: [] }; }
  return res.json();
}

const byId = new Map();
for (const q of QUERIES) {
  let token, page = 0;
  do {
    const data = await search(q, token);
    for (const p of (data.places || [])) byId.set(p.id, p);
    token = data.nextPageToken; page++;
    if (token) await new Promise(r => setTimeout(r, 1500)); // token needs a moment to activate
  } while (token && page < 3); // up to 60 results per query
  console.error(`"${q}" -> running total ${byId.size}`);
}

const rows = [['Business Name','Primary Type','Phone','Rating','Reviews','Address','Maps Link','Website']];
for (const p of byId.values()) {
  const phone = p.nationalPhoneNumber || p.internationalPhoneNumber || '';
  rows.push([
    p.displayName?.text || '', p.primaryType || '', phone,
    p.rating ?? '', p.userRatingCount ?? '',
    p.formattedAddress || '', p.googleMapsUri || '', p.websiteUri || '',
  ]);
}
const esc = s => { s = (s == null ? '' : String(s)); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
const out = rows.map(r => r.map(esc).join(',')).join('\n');
fs.writeFileSync(new URL('./cloud-kitchens-google.csv', import.meta.url), out);
const withPhone = rows.slice(1).filter(r => r[2]).length;
console.error(`\nWrote ${rows.length - 1} unique places (${withPhone} with phone) -> cloud-kitchens-google.csv`);
