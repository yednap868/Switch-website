/* ─── ISSUED CERTIFICATE REGISTRY ─────────────────────
   Source of truth for /verify. Keyed by the certificate ID
   in hyphenated form (as used in the QR / verify URL, e.g.
   ?id=SWITCH-INT-2026-0007). Add one entry per certificate
   issued. The QR printed on each certificate points to:
   https://switchlocally.com/verify?id=<KEY>
*/
export const CERTIFICATES = {
  'SWITCH-INT-2026-0006': {
    displayId: 'SWITCH/INT/2026/0006',
    name: 'Saksham Batra',
    type: 'Internship',
    role: 'Operations Intern',
    duration: 'Seven (7) days',
    start: '30 July 2026',
    end: '05 August 2026',
    issued: '06 August 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0007': {
    displayId: 'SWITCH/INT/2026/0007',
    name: 'Ankul Kumar',
    type: 'Internship',
    role: 'Python Software Engineer Intern',
    duration: 'One (1) month',
    start: '20 June 2026',
    end: '20 July 2026',
    issued: '21 July 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0008': {
    displayId: 'SWITCH/INT/2026/0008',
    name: 'Sanskriti Gupta',
    type: 'Internship',
    role: 'Frontend Developer Intern',
    duration: 'Two (2) months',
    start: '20 June 2026',
    end: '20 August 2026',
    issued: '21 August 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0009': {
    displayId: 'SWITCH/INT/2026/0009',
    name: 'Suhani Singh',
    type: 'Internship',
    role: 'Frontend Developer Intern',
    duration: 'Two (2) months',
    start: '20 June 2026',
    end: '20 August 2026',
    issued: '21 August 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0010': {
    displayId: 'SWITCH/INT/2026/0010',
    name: 'Saba Faij',
    type: 'Internship',
    role: 'Backend Developer Intern',
    duration: 'One (1) month',
    start: '20 June 2026',
    end: '20 July 2026',
    issued: '21 July 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0011': {
    displayId: 'SWITCH/INT/2026/0011',
    name: 'Shourya Pandey',
    type: 'Internship',
    role: 'Founder’s Office – Product & Growth Intern',
    duration: 'Two (2) months',
    start: '20 June 2026',
    end: '20 August 2026',
    issued: '21 August 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0012': {
    displayId: 'SWITCH/INT/2026/0012',
    name: 'Sanya Priya',
    type: 'Internship',
    role: 'Graphic Designer Intern',
    duration: 'One (1) month',
    start: '20 July 2026',
    end: '20 August 2026',
    issued: '21 August 2026',
    location: 'Gurugram',
  },
  'SWITCH-INT-2026-0013': {
    displayId: 'SWITCH/INT/2026/0013',
    name: 'Ayush Kukrety',
    type: 'Internship',
    role: 'Backend Developer Intern',
    duration: 'Two (2) months',
    start: '20 June 2026',
    end: '20 August 2026',
    issued: '21 August 2026',
    location: 'Gurugram',
  },
}

/* Normalise any user/QR-supplied id to the registry key:
   trims, uppercases, and converts slashes/spaces to hyphens. */
export function lookupCertificate(rawId) {
  if (!rawId) return null
  const key = String(rawId).trim().toUpperCase().replace(/[\s/]+/g, '-')
  return CERTIFICATES[key] ? { key, ...CERTIFICATES[key] } : null
}
