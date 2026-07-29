#!/usr/bin/env node
/**
 * B2B lead list for SELLING Switch staffing services.
 * Targets businesses that hire blue-collar/support staff (restaurants, retail,
 * salons, gyms, hotels, clinics, offices) across specific Gurgaon areas.
 *
 * Source: OpenStreetMap Overpass API (free, no key, legal).
 * NOTE: OSM phone coverage is sparse. For owner/contact numbers on (almost)
 * every business, use the Google Places version (scrape-nearby.mjs) with a key.
 *
 * Usage: node b2b-leads-osm.mjs   ->  b2b-leads.csv
 */

// Each target area with an approximate center + search radius (metres).
const AREAS = [
  { name: 'Galleria Market', lat: 28.46742, lng: 77.09353, r: 700 },
  { name: 'DLF Phase 1',     lat: 28.47600, lng: 77.09800, r: 1100 },
  { name: 'DLF Phase 2',     lat: 28.49200, lng: 77.09000, r: 1000 },
  { name: 'DLF Phase 3',     lat: 28.49300, lng: 77.09900, r: 1300 },
  { name: 'Sikanderpur',     lat: 28.48100, lng: 77.09450, r: 800 },
  { name: 'U Block DLF 3',   lat: 28.49050, lng: 77.10150, r: 600 },
]

const ENDPOINTS = [
  'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass-api.de/api/interpreter',
]

// Business types worth selling staffing to (they employ helpers/guards/cooks/etc.)
function queryFor(a) {
  const around = `(around:${a.r},${a.lat},${a.lng})`
  return `
[out:json][timeout:90];
(
  nwr["shop"]${around};
  nwr["office"]${around};
  nwr["amenity"~"^(restaurant|cafe|fast_food|bar|pub|food_court|ice_cream|bank|pharmacy|clinic|dentist|doctors|hospital|cinema|nightclub|spa|marketplace|fuel|car_rental|car_wash|coworking_space)$"]${around};
  nwr["leisure"~"^(fitness_centre|sports_centre|spa)$"]${around};
  nwr["healthcare"]${around};
  nwr["tourism"~"^(hotel|guest_house|hostel|motel)$"]${around};
);
out center tags;
`
}

async function fetchArea(a) {
  const body = 'data=' + encodeURIComponent(queryFor(a))
  for (const url of ENDPOINTS) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })
      if (!res.ok) continue
      const json = await res.json()
      return json.elements || []
    } catch { /* try next mirror */ }
  }
  return []
}

const cell = (v) => {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

function category(t) {
  return t.shop || t.office || t.amenity || t.leisure || t.healthcare || t.tourism || 'other'
}
// Rough proxy for "how much staff they hire" — helps prioritise outreach.
function staffPotential(cat) {
  const high = ['restaurant', 'hotel', 'hospital', 'fast_food', 'cafe', 'bar', 'pub', 'supermarket', 'mall', 'department_store', 'nightclub', 'food_court', 'clinic']
  const med = ['bank', 'pharmacy', 'beauty', 'hairdresser', 'fitness_centre', 'spa', 'company', 'it', 'consulting', 'gym', 'cinema', 'jewelry']
  if (high.includes(cat)) return 'HIGH'
  if (med.includes(cat)) return 'MED'
  return 'LOW'
}

async function main() {
  const seen = new Map() // osm id -> row
  for (const a of AREAS) {
    process.stdout.write(`Querying ${a.name} ... `)
    const els = await fetchArea(a)
    let added = 0
    for (const el of els) {
      const t = el.tags || {}
      const name = t.name || t['name:en'] || t.brand
      if (!name) continue
      const id = `${el.type}/${el.id}`
      if (seen.has(id)) continue
      const cat = category(t)
      seen.set(id, {
        name,
        area: a.name,
        category: cat,
        staff_potential: staffPotential(cat),
        phone: t.phone || t['contact:phone'] || t['contact:mobile'] || '',
        website: t.website || t['contact:website'] || '',
        address: [t['addr:housenumber'], t['addr:street'], t['addr:suburb']].filter(Boolean).join(', '),
        maps: `https://www.openstreetmap.org/${id}`,
      })
      added++
    }
    console.log(`${els.length} objects, ${added} new businesses`)
  }

  const rank = { HIGH: 0, MED: 1, LOW: 2 }
  const rows = [...seen.values()].sort((x, y) =>
    rank[x.staff_potential] - rank[y.staff_potential] || x.area.localeCompare(y.area)
  )

  const headers = ['name', 'area', 'category', 'staff_potential', 'phone', 'website', 'address', 'maps']
  const csv = [headers.join(','), ...rows.map(r => headers.map(h => cell(r[h])).join(','))].join('\n')
  const { writeFileSync } = await import('node:fs')
  writeFileSync('b2b-leads.csv', csv)

  const byArea = {}, byPot = {}
  for (const r of rows) { byArea[r.area] = (byArea[r.area] || 0) + 1; byPot[r.staff_potential] = (byPot[r.staff_potential] || 0) + 1 }
  console.log('\n===== B2B LEADS =====')
  console.log(`Total businesses : ${rows.length}`)
  console.log(`With phone       : ${rows.filter(r => r.phone).length}`)
  console.log(`With website     : ${rows.filter(r => r.website).length}`)
  console.log('\nBy area:'); for (const [k, v] of Object.entries(byArea)) console.log(`  ${String(v).padStart(4)}  ${k}`)
  console.log('\nBy staffing potential:'); for (const k of ['HIGH', 'MED', 'LOW']) console.log(`  ${String(byPot[k] || 0).padStart(4)}  ${k}`)
  console.log('\nSaved -> b2b-leads.csv')
}

main().catch(e => { console.error('Error:', e.message); process.exit(1) })
