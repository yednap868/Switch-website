#!/usr/bin/env node
/**
 * Separate B2B sheet: RESIDENTIAL clients that hire blue-collar/support staff —
 * PGs, hostels, guest houses, apartment societies, gated communities, condos.
 * These need cleaners, cooks, guards, property managers (the Great-PG case).
 *
 * Source: leads-google.csv (the Google Places crawl).
 * Output: residential-b2b.csv  (A->Z, phone-first; PG/hostel ranked above societies)
 *
 * Usage: node build-residential-b2b.mjs
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

const rows = parseCSV(readFileSync('leads-google.csv', 'utf8')).filter(r => r.length > 1)
const head = rows.shift()
const idx = Object.fromEntries(head.map((h, i) => [h, i]))
const get = (r, k) => (r[idx[k]] ?? '').trim()

// Google place types that signal residential occupancy with staff needs
const RES_TYPE = /\b(apartment_building|apartment_complex|housing_complex|condominium|housing_development|lodging|guest_house|hostel|dormitory|extended_stay_hotel|bed_and_breakfast)\b/
// name signals (PGs & societies are often only identifiable by name)
const PG_NAME  = /\b(pg|paying guest|boys hostel|girls hostel|co.?living|coliving|nest|stanza|zolo|your.?space|oxfordcaps|hello world|colive)\b/i
const SOC_NAME = /\b(apartment|apartments|residency|residences|society|towers?|heights|enclave|estate|greens?|gardens?|homes?|villas?|condos?|floors?|niwas|vihar|kunj|residenc)\b/i
// exclude full hotels/resorts (those are in switch-targets as hospitality, not residential)
const HOTEL    = /\b(hotel|resort_hotel|motel|inn)\b/

function classify(name, primary, all) {
  const t = `${primary} ${all}`.toLowerCase().replace(/\|/g, ' ')
  const isHotel = HOTEL.test(t) && !/guest_house|lodging|hostel/.test(t)
  if (PG_NAME.test(name)) return 'PG / Co-living'
  if (/\b(hostel|dormitory)\b/.test(t)) return 'Hostel'
  if (/\b(guest_house|bed_and_breakfast|extended_stay)\b/.test(t)) return 'Guest House'
  if (/\b(apartment_building|apartment_complex|housing_complex|condominium|housing_development)\b/.test(t))
    return 'Apartment Society'
  if (/\blodging\b/.test(t) && !isHotel) return 'Lodging / PG'
  if (SOC_NAME.test(name) && !isHotel) return 'Apartment Society'
  return null
}

// A pinned private home/flat is NOT a staffing client. Keep an "Apartment Society"
// row only if it reads like a real complex: society/tower keywords, OR has a
// website, OR has enough reviews to be a managed building (not one family's pin).
const REAL_SOCIETY = /\b(tower|towers|apartment|apartments|residency|residences|society|heights|enclave|estate|court|condominium|condo|greens?|block\s|park|niwas|kunj|villa|villas|mansion|suites?|floors?)\b/i
function isRealSociety(name, website, reviews) {
  if (REAL_SOCIETY.test(name)) return true
  if (website) return true
  if (Number(reviews) >= 15) return true
  return false
}

// merge verified web numbers (only real, source-checked) if present
const enrich = existsSync('residential-enrich.json')
  ? JSON.parse(readFileSync('residential-enrich.json', 'utf8')) : {}

const RANK = { 'PG / Co-living': 0, 'Lodging / PG': 1, 'Hostel': 2, 'Guest House': 3, 'Apartment Society': 4 }
const list = []
for (const r of rows) {
  const name = get(r, 'name')
  if (!name) continue
  const kind = classify(name, get(r, 'primary_type'), get(r, 'all_types'))
  if (!kind) continue
  const website = get(r, 'website'), reviews = get(r, 'reviews')
  // drop pinned private homes from the society bucket
  if (kind === 'Apartment Society' && !isRealSociety(name, website, reviews)) continue

  const gPhone = get(r, 'phone')
  const e = enrich[name]
  const phone = gPhone || (e ? e.phone : '')
  const phone_source = gPhone ? 'google' : (e ? 'web-verified' : '')
  list.push({
    name,
    type: kind,
    staff_needs: /PG|Lodging|Hostel|Guest/.test(kind)
      ? 'cleaner, cook, warden, guard' : 'cleaner, guard, gardener, property mgr',
    phone,
    phone_source,
    contact: e?.contact || '',
    source_note: e ? e.source : '',
    website,
    rating: get(r, 'rating'),
    reviews,
    address: get(r, 'address'),
    maps_url: get(r, 'maps_url'),
  })
}

const cols = ['name','type','staff_needs','phone','phone_source','contact','source_note','website','rating','reviews','address','maps_url']
const toCSV = (rs) => [cols.join(','), ...rs.map(r => cols.map(c => cell(r[c])).join(','))].join('\n') + '\n'

// phone-first, then PG/co-living/hostels above societies, then A->Z
const sorted = [...list].sort((a, b) =>
  (Number(!!b.phone) - Number(!!a.phone)) ||
  (RANK[a.type] - RANK[b.type]) ||
  a.name.toLowerCase().localeCompare(b.name.toLowerCase()))
writeFileSync('residential-b2b.csv', toCSV(sorted))

const byType = list.reduce((m, r) => (m[r.type] = (m[r.type]||0)+1, m), {})
const withPh = list.filter(r => r.phone).length
const g = list.filter(r => r.phone_source === 'google').length
const w = list.filter(r => r.phone_source === 'web-verified').length
console.log(`residential-b2b.csv  ${list.length} residential B2B targets (private-home pins dropped)`)
console.log(`   with phone: ${withPh}  (google-listed ${g} · web-verified ${w})`)
for (const [k, v] of Object.entries(byType).sort((a,b)=>RANK[a[0]]-RANK[b[0]]))
  console.log(`   ${k.padEnd(18)} ${v}`)
// callable-only residential subset
const callable = sorted.filter(r => r.phone)
writeFileSync('residential-callable.csv', toCSV(callable))
console.log(`residential-callable.csv  ${callable.length} with a phone (ready to dial)`)
