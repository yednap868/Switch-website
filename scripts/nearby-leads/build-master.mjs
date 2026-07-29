#!/usr/bin/env node
/**
 * Build ONE clean A-to-Z master lead sheet from all sources:
 *   - leads-all.csv      (wide 3km OSM scrape: every business near Cyber Hub)
 *   - b2b-leads.csv      (adds `area` + `staff_potential` rating)
 *   - ready-to-call.csv  (web-verified phones)
 *
 * Dedupes by normalised name, prefers the most reliable phone, sorts A->Z.
 * Output: master-leads.csv  (+ a callable-only subset: master-callable.csv)
 *
 * Usage: node build-master.mjs
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs'

function parseCSV(text) {
  const rows = []
  let row = [], field = '', q = false
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    if (q) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++ }
      else if (c === '"') q = false
      else field += c
    } else if (c === '"') q = true
    else if (c === ',') { row.push(field); field = '' }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = '' }
    else if (c === '\r') { /* skip */ }
    else field += c
  }
  if (field.length || row.length) { row.push(field); rows.push(row) }
  return rows
}
const cell = (v) => {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
const load = (f) => {
  if (!existsSync(f)) return []
  const rows = parseCSV(readFileSync(f, 'utf8')).filter(r => r.length > 1)
  const head = rows.shift()
  const idx = Object.fromEntries(head.map((h, i) => [h, i]))
  return rows.map(r => Object.fromEntries(Object.keys(idx).map(k => [k, r[idx[k]] ?? ''])))
}
const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '').trim()

// staff-potential heuristic for rows that only exist in the OSM map
const HIGH = /restaurant|cafe|fast_food|bar|pub|food_court|hotel|hostel|mall|hospital|clinic|spa|fitness|gym|supermarket|bakery|nightclub|guest_house|resort|banquet|cloud_kitchen/
const MED  = /salon|hairdresser|beauty|pharmacy|dentist|doctors|bank|coworking|cinema|office|company|consulting|car_wash|car_rental|fuel/
const rate = (cat) => HIGH.test(cat) ? 'HIGH' : MED.test(cat) ? 'MED' : 'LOW'

const all = load('leads-all.csv')      // name,category,phone,website,address,distance_m,osm
const b2b = load('b2b-leads.csv')      // name,area,category,staff_potential,phone,...
const rtc = load('ready-to-call.csv')  // verified phones

// index the enrichment sources by normalised name
const b2bByName = new Map(b2b.map(r => [norm(r.name), r]))
const rtcByName = new Map(rtc.map(r => [norm(r.name), r]))

const master = new Map()
const consider = [...all, ...b2b]
for (const r of consider) {
  const key = norm(r.name)
  if (!key) continue
  const b = b2bByName.get(key)
  const v = rtcByName.get(key)
  const phone = (v?.phone || r.phone || b?.phone || '').trim()
  const cur = master.get(key)
  const rec = {
    name: (r.name || b?.name || '').trim(),
    category: (r.category || b?.category || '').trim(),
    staff_potential: b?.staff_potential || rate(r.category || b?.category || ''),
    phone,
    phone_verified: v?.phone ? 'web-verified' : (phone ? 'osm' : ''),
    website: (r.website || b?.website || '').trim(),
    area: (b?.area || '').trim(),
    address: (r.address || b?.address || '').trim(),
    maps: r.osm || b?.maps || '',
  }
  // merge: keep the record that has a phone / more info
  if (!cur) master.set(key, rec)
  else {
    if (!cur.phone && rec.phone) cur.phone = rec.phone, cur.phone_verified = rec.phone_verified
    if (!cur.website && rec.website) cur.website = rec.website
    if (!cur.address && rec.address) cur.address = rec.address
    if (!cur.area && rec.area) cur.area = rec.area
  }
}

const POT = { HIGH: 0, MED: 1, LOW: 2 }
const list = [...master.values()].sort((a, b) =>
  a.name.toLowerCase().localeCompare(b.name.toLowerCase()))

const cols = ['name','category','staff_potential','phone','phone_verified','website','area','address','maps']
const toCSV = (rows) => [cols.join(','), ...rows.map(r => cols.map(c => cell(r[c])).join(','))].join('\n') + '\n'

writeFileSync('master-leads.csv', toCSV(list))
const callable = list.filter(r => r.phone)
  .sort((a, b) => (POT[a.staff_potential] - POT[b.staff_potential]) ||
                  a.name.toLowerCase().localeCompare(b.name.toLowerCase()))
writeFileSync('master-callable.csv', toCSV(callable))

const byPot = list.reduce((m, r) => (m[r.staff_potential] = (m[r.staff_potential]||0)+1, m), {})
console.log(`master-leads.csv     ${list.length} unique businesses (A->Z)`)
console.log(`  HIGH ${byPot.HIGH||0} · MED ${byPot.MED||0} · LOW ${byPot.LOW||0}`)
console.log(`master-callable.csv  ${callable.length} with a phone (ready to dial)`)
console.log(`  of those, HIGH potential: ${callable.filter(r=>r.staff_potential==='HIGH').length}`)
