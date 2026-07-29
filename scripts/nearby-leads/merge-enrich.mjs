#!/usr/bin/env node
/**
 * Merge web-search-verified phone numbers (enrich-web.json) into b2b-leads.csv.
 * Adds two columns: `phone_source` (osm | web | none) and `enrich_note`.
 * Re-runnable: add entries to enrich-web.json and run again.
 *
 * Usage: node merge-enrich.mjs   ->  rewrites b2b-leads.csv + writes ready-to-call.csv
 */
import { readFileSync, writeFileSync } from 'node:fs'

// --- tiny CSV parser (handles quoted fields with commas) ---
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

const enrich = JSON.parse(readFileSync('enrich-web.json', 'utf8'))
const rows = parseCSV(readFileSync('b2b-leads.csv', 'utf8')).filter(r => r.length > 1)
const head = rows.shift()
const idx = Object.fromEntries(head.map((h, i) => [h, i]))

let webCount = 0
const out = rows.map(r => {
  const name = r[idx.name]
  const hasOsmPhone = !!(r[idx.phone] && r[idx.phone].trim())
  let source = hasOsmPhone ? 'osm' : 'none'
  let note = ''
  if (enrich[name]) {
    r[idx.phone] = enrich[name].phone
    source = 'web'
    note = enrich[name].note || ''
    webCount++
  }
  return [...r, source, note]
})

const newHead = [...head, 'phone_source', 'enrich_note']
writeFileSync('b2b-leads.csv',
  [newHead, ...out].map(r => r.map(cell).join(',')).join('\n'))

// ready-to-call.csv: only rows WITH a phone, HIGH first, web-verified flagged
const pIdx = newHead.length - 2
const withPhone = out.filter(r => r[idx.phone] && r[idx.phone].trim())
const rank = { HIGH: 0, MED: 1, LOW: 2 }
withPhone.sort((a, b) =>
  rank[a[idx.staff_potential]] - rank[b[idx.staff_potential]] ||
  a[idx.area].localeCompare(b[idx.area]))
writeFileSync('ready-to-call.csv',
  [newHead, ...withPhone].map(r => r.map(cell).join(',')).join('\n'))

console.log(`Merged ${webCount} web-verified numbers.`)
console.log(`Total rows: ${out.length}`)
console.log(`Rows with a phone (any source): ${withPhone.length}`)
console.log(`  web-verified: ${withPhone.filter(r => r[pIdx] === 'web').length}`)
console.log(`  osm-listed  : ${withPhone.filter(r => r[pIdx] === 'osm').length}`)
console.log(`HIGH potential + phone: ${withPhone.filter(r => r[idx.staff_potential] === 'HIGH').length}`)
console.log('\nWrote -> b2b-leads.csv (now with source columns)')
console.log('Wrote -> ready-to-call.csv (prioritized call sheet)')
