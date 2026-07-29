#!/usr/bin/env node
/**
 * Build the A-to-Z master lead sheet from the Google Places crawl (leads-google.csv).
 * Classifies each business by blue-collar staff-hiring potential for Switch,
 * drops non-targets (apartments, ATMs, EV chargers, etc.), sorts A->Z.
 *
 * Outputs:
 *   master-leads.csv     - every relevant business, A->Z (HIGH/MED/LOW)
 *   master-callable.csv  - relevant + has a phone, prioritized HIGH->MED->LOW
 *   switch-targets.csv    - the outreach sheet: HIGH/MED potential WITH a phone
 *
 * Usage: node build-master-google.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs'

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

// --- staff-hiring potential classifier (matches Google place types) ---
const HIGH = /\b(restaurant|cafe|coffee_shop|bar|pub|night_club|bakery|fast_food|meal_takeaway|meal_delivery|food_court|ice_cream|hotel|motel|resort_hotel|guest_house|inn|lodging|hostel|hospital|clinic|spa|wellness_center|gym|fitness_center|beauty_salon|hair_salon|hair_care|nail_salon|barber|supermarket|grocery_store|shopping_mall|department_store|banquet_hall|wedding_venue|catering|cafeteria)\b/
const MED  = /\b(store|clothing_store|electronics_store|shoe_store|jewelry_store|furniture_store|home_goods_store|book_store|pet_store|hardware_store|convenience_store|liquor_store|pharmacy|drugstore|dentist|doctor|physiotherapist|veterinary_care|bank|finance|school|university|child_care|car_repair|car_wash|car_dealer|car_rental|laundry|corporate_office|coworking|real_estate_agency|travel_agency|gas_station|movie_theater|amusement|tourist_attraction)\b/
// hard excludes — never a staffing target
const SKIP = /\b(apartment_building|housing|residential|electric_vehicle_charging_station|parking|atm|bus_stop|train_station|subway_station|transit_station|airport|place_of_worship|hindu_temple|mosque|church|cemetery|park|natural_feature|administrative_area|locality|political|postal_code|gas_station_)\b/

function rate(primary, all) {
  const t = `${primary} ${all}`.toLowerCase().replace(/\|/g, ' ')
  if (HIGH.test(t)) return 'HIGH'
  if (MED.test(t)) return 'MED'
  // pure point_of_interest/establishment with nothing useful, or a skip type
  if (SKIP.test(t)) return 'SKIP'
  return 'LOW'
}

const list = []
for (const r of rows) {
  const name = get(r, 'name')
  if (!name) continue
  const pot = rate(get(r, 'primary_type'), get(r, 'all_types'))
  if (pot === 'SKIP') continue
  list.push({
    name,
    category: get(r, 'primary_type'),
    staff_potential: pot,
    phone: get(r, 'phone'),
    website: get(r, 'website'),
    rating: get(r, 'rating'),
    reviews: get(r, 'reviews'),
    address: get(r, 'address'),
    maps_url: get(r, 'maps_url'),
  })
}

const cols = ['name','category','staff_potential','phone','website','rating','reviews','address','maps_url']
const toCSV = (rs) => [cols.join(','), ...rs.map(r => cols.map(c => cell(r[c])).join(','))].join('\n') + '\n'

const azName = (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase())
const POT = { HIGH: 0, MED: 1, LOW: 2 }

const master = [...list].sort(azName)
writeFileSync('master-leads.csv', toCSV(master))

const callable = list.filter(r => r.phone)
  .sort((a, b) => (POT[a.staff_potential] - POT[b.staff_potential]) || azName(a, b))
writeFileSync('master-callable.csv', toCSV(callable))

const targets = list.filter(r => r.phone && r.staff_potential !== 'LOW')
  .sort((a, b) => (POT[a.staff_potential] - POT[b.staff_potential]) || azName(a, b))
writeFileSync('switch-targets.csv', toCSV(targets))

const c = (arr, p) => arr.filter(r => r.staff_potential === p).length
console.log(`master-leads.csv     ${master.length} relevant businesses (A->Z)`)
console.log(`   HIGH ${c(master,'HIGH')} · MED ${c(master,'MED')} · LOW ${c(master,'LOW')}`)
console.log(`master-callable.csv  ${callable.length} with a phone`)
console.log(`switch-targets.csv    ${targets.length} OUTREACH LEADS (HIGH+MED, has phone)`)
console.log(`   HIGH w/ phone ${c(targets,'HIGH')} · MED w/ phone ${c(targets,'MED')}`)
