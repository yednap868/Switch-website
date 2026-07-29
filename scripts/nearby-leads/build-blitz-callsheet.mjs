#!/usr/bin/env node
// Build a prioritized 2-day outreach call sheet from master-callable.csv.
// Keeps only HIGH-potential leads that have a phone, maps each category to the
// staff roles worth pitching, sorts by churn-tier, and adds tracking columns.
//
//   node build-blitz-callsheet.mjs            # top 100 -> 2-day-blitz-callsheet.csv
//   node build-blitz-callsheet.mjs --limit 60 # smaller list
//
// Re-run any time the lead lists are refreshed.

import { readFileSync, writeFileSync } from 'node:fs';

const SRC = 'master-callable.csv';
const OUT = '2-day-blitz-callsheet.csv';
const limitArg = process.argv.indexOf('--limit');
const LIMIT = limitArg !== -1 ? Number(process.argv[limitArg + 1]) : 100;

// --- tiny CSV parser (handles quoted fields with commas) ---------------------
function parseCSV(text) {
  const rows = [];
  let row = [], field = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') inQ = false;
      else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else if (c === '\r') { /* skip */ }
    else field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

const csv = (s) => {
  s = s == null ? '' : String(s);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

// --- category -> (priority tier, roles to pitch) -----------------------------
// Lower tier number = call first (highest staff churn / fastest yes).
function classify(category) {
  const c = (category || '').toLowerCase();
  const has = (...words) => words.some((w) => c.includes(w));

  if (has('restaurant', 'food_court', 'fast_food', 'cafe', 'bakery', 'dhaba', 'eatery', 'food'))
    return { tier: 1, roles: 'Kitchen helper, dishwasher, waiter, delivery boy' };
  if (has('hotel', 'lodging', 'guest', 'resort', 'banquet'))
    return { tier: 1, roles: 'Housekeeping, room boy, security guard, helper' };
  if (has('wedding', 'event', 'venue'))
    return { tier: 1, roles: 'Banquet staff, helpers, security, housekeeping' };
  if (has('grocery', 'supermarket', 'store', 'mart', 'retail', 'shop'))
    return { tier: 2, roles: 'Store helper, packer, loader, delivery' };
  if (has('salon', 'spa', 'beauty', 'wellness', 'parlour', 'parlor'))
    return { tier: 2, roles: 'Receptionist, helper, housekeeping' };
  if (has('fitness', 'gym'))
    return { tier: 2, roles: 'Front desk, housekeeping, trainer assistant' };
  if (has('clinic', 'medical', 'health', 'hospital', 'dental'))
    return { tier: 2, roles: 'Receptionist, attendant, housekeeping, guard' };
  if (has('warehouse', 'logistics', 'distribution'))
    return { tier: 1, roles: 'Loader, packer, picker, delivery' };
  return { tier: 3, roles: 'Helper, housekeeping, security guard' };
}

// --- run ---------------------------------------------------------------------
const rows = parseCSV(readFileSync(SRC, 'utf8'));
const header = rows[0];
const idx = (name) => header.indexOf(name);
const iName = idx('name'), iCat = idx('category'), iPot = idx('staff_potential'),
      iPhone = idx('phone'), iAddr = idx('address'), iMaps = idx('maps_url');

const hasPhone = (p) => /[0-9]{6}/.test(p || '');

const leads = rows.slice(1)
  .filter((r) => r.length > iPhone)
  .filter((r) => (r[iPot] || '').toUpperCase() === 'HIGH' && hasPhone(r[iPhone]))
  .map((r) => {
    const { tier, roles } = classify(r[iCat]);
    return {
      tier,
      roles,
      name: r[iName],
      category: r[iCat],
      phone: (r[iPhone] || '').trim(),
      address: r[iAddr] || '',
      maps: r[iMaps] || '',
    };
  });

// dedupe by phone, then by name
const seen = new Set();
const deduped = leads.filter((l) => {
  const key = l.phone.replace(/\D/g, '') || l.name.toLowerCase();
  if (seen.has(key)) return false;
  seen.add(key);
  return true;
});

deduped.sort((a, b) => a.tier - b.tier || a.category.localeCompare(b.category) || a.name.localeCompare(b.name));
const top = deduped.slice(0, LIMIT);

const outHeader = ['Priority', 'Business Name', 'Category', 'Suggested Roles to Pitch',
  'Phone', 'Address', 'Maps', 'Status', 'Owner', 'Last Contact', 'Next Action', 'Notes'];
const lines = [outHeader.join(',')];
for (const l of top) {
  lines.push([
    `P${l.tier}`, l.name, l.category, l.roles, l.phone, l.address, l.maps,
    'Not contacted', '', '', '', '',
  ].map(csv).join(','));
}
writeFileSync(OUT, lines.join('\n') + '\n');

const byTier = top.reduce((m, l) => ((m[l.tier] = (m[l.tier] || 0) + 1), m), {});
console.log(`Wrote ${top.length} leads -> ${OUT}`);
console.log(`  P1 (call first): ${byTier[1] || 0}   P2: ${byTier[2] || 0}   P3: ${byTier[3] || 0}`);
console.log(`  (from ${deduped.length} unique HIGH callable leads)`);
