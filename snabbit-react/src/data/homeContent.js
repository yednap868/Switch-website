/* Homepage content. Lifted out of App.jsx so the section components in
   src/components/home stay presentational. Copy is the live site's. */

export const ALL_ROLES_MARQUEE = [
  'Store Helper','Security Guard','Picker / Packer','Driver','Delivery Rider','Cook / Chef',
  'Housekeeping','Caretaker',
]

export const ROLES = [
  { img: '/sw-general-helper.jpg', name: 'General / Store Helper', slug: 'store-helper-gurgaon',     desc: 'Billing support, stocking, loading & shop-floor help', focus: '46% 3%', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/sw-security-guard.jpg', name: 'Security Guard',         slug: 'security-guard-gurgaon',   desc: 'Gate duty, premises security & night patrol', focus: '50% 8%', tags: ['12 hrs','2 days','7 days'] },
  { img: '/sw-factory-helper.jpg', name: 'Picker / Packer',        slug: 'factory-warehouse-gurgaon', desc: 'Warehouse picking, packing, sorting & dispatch', focus: '51% 0%', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/sw-driver.jpg',         name: 'Driver',                 slug: 'driver-gurgaon',           desc: 'Commercial runs, deliveries & staff transport', focus: '42% 14%', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/delivery-rider.jpg',  name: 'Delivery Rider',         slug: 'delivery-worker-gurgaon',  desc: 'Last-mile delivery, loading & movers', focus: '45% 10%', tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/sw-cook.jpg',           name: 'Cook / Chef',            slug: 'cook-gurgaon',             desc: 'Kitchen production for cafés, messes & catering', focus: '51% 4%', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/sw-maid.jpg',           name: 'Housekeeping',           slug: 'home-cleaning-gurgaon',    desc: 'Daily upkeep for offices, shops & premises', focus: '54% 6%', tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/sw-caretaker.jpg',      name: 'Caretaker / Elder Care', slug: 'nanny-gurgaon',            desc: 'Baby care, elder care & home assistance', focus: '49% 6%', tags: ['4 hrs','8 hrs','2 days'] },
]

/* Nine sectors — business premises only; domestic and institutional work came
   out. Nine is what the grid is built around: a 3x3 block beside a feature
   column on desktop, three rows of three on tablet, and at two columns the
   last card spans the pair so the odd count does not leave a hole.
   `ico` is carried for the interior pages; the homepage cards are numbered
   rather than illustrated. */
export const INDUSTRIES = [
  { ico: '🛍️', name: 'Retail & Shops', slug: 'retail-staffing-gurgaon',          roles: 'Store helpers · Billing support · Loaders · Security' },
  { ico: '🍽️', name: 'Restaurants & Cafés', slug: 'restaurant-staffing-gurgaon',     roles: 'Waiters · Kitchen helpers · Cooks · Dishwashers' },
  { ico: '📦', name: 'Warehouses & Logistics', slug: 'warehouse-staffing-gurgaon',  roles: 'Pickers · Packers · Loaders · Dispatch help' },
  { ico: '🏭', name: 'Factories & Production',  roles: 'Factory helpers · Loaders · Packers · Shift hands' },
  { ico: '🏢', name: 'Offices & Co-working', slug: 'office-staffing-gurgaon',    roles: 'Office boys · Housekeeping · Pantry · Front desk' },
  { ico: '🎉', name: 'Events & Banquets', slug: 'event-staffing-gurgaon',       roles: 'Waiters · Bartenders · Bouncers · Promoters' },
  { ico: '🏨', name: 'Hotels & Guest Houses',   roles: 'Housekeeping · Stewards · Kitchen helpers · Security' },
  { ico: '🛒', name: 'Grocery & Q-Commerce',   roles: 'Pickers · Packers · Delivery riders · Store helpers' },
  { ico: '💈', name: 'Salons, Gyms & Clinics',  roles: 'Front desk · Housekeeping · Attendants · Helpers' },
]

/* Client logo wall. `logo` is a file in public/logos/. `h` is its display
   height in px: these marks range from a 3:1 wordmark to a taller-than-wide
   crest, so a single height makes the wide ones shout and the tall ones vanish.
   Each h is set to give every logo roughly the same optical area
   (h ~= sqrt(1600 / aspect)), which is what makes a logo wall look even.
   A brand with no logo file falls back to a styled wordmark, so the row stays
   complete — drop a file in public/logos/ and add `logo` + `h` to swap it. */
export const BRANDS = [
  { name: 'Ivory Stayz',        logo: '/logos/ivory-stayz.svg', h: 24 },
  { name: 'Dr Diet Restaurant', logo: '/logos/dr-diet.png',     h: 42 },
  { name: 'Foressta Cafe',      logo: '/logos/foressta.png',    h: 22 },
  { name: 'Crax',               logo: '/logos/crax.png',        h: 38 },
  { name: 'ValueShoppe',        logo: '/logos/valueshoppe.png', h: 42 },
  { name: 'BentoBox'                                                  },
  { name: 'Fairdeal'                                                  },
  { name: 'Inamo',              logo: '/logos/inamo.png',       h: 24 },
]

export const REVIEWS = [
  { name: 'Pradnyesh', loc: 'Warehouse · Udyog Vihar', text: 'Needed 4 warehouse Switch Players urgently. Got verified staff same-day. Absolute lifesaver for our dispatch team.' },
  { name: 'Sameer K.',  loc: 'Retail Store · DLF Phase 5', text: 'Our store needed extra hands during Diwali. Switch sent 3 experienced helpers within just a few hours.' },
  { name: 'Rohit M.',   loc: 'Restaurant · Sector 29',   text: 'We staff weekend banquets through Switch — waiters and a bartender, every time on time. Replacement was instant when one fell sick.' },
  { name: 'Neha P.',    loc: 'Logistics · Sector 52',     text: 'Booked drivers for 7 days straight. Always professional, always on time. Now our default for staffing.' },
  { name: 'Aman G.',    loc: 'Café · Golf Course Road',   text: 'Two kitchen helpers for a full week during our launch. Verified, skilled, and no agency drama.' },
  { name: 'Ritika M.',  loc: 'Event · Sector 23',         text: 'Hired waiters for a corporate event. Booked at 9 PM, reported 8 AM sharp. Incredible reliability.' },
  { name: 'Vivek S.',   loc: 'Office · Cyber City',       text: 'Daily housekeeping and a security guard for our office floor. Set up in a day, billing was clean.' },
  { name: 'Kirti S.',   loc: 'Home · DLF Phase 2',        text: 'Also used them for a home cook — punctual, skilled, excellent food every single day.' },
]

export const FAQS = [
  { q: 'What kind of staff can I hire for my business?', a: 'Store and general helpers, security guards, factory and warehouse Switch Players, waiters, bartenders, bouncers, promoters, drivers, cooks, kitchen helpers and housekeeping — for shops, restaurants, warehouses, offices, events and more.' },
  { q: 'Can I hire multiple Switch Players or a full team?', a: 'Yes. Bulk hiring is one of our most common requests — 3, 5 or more Switch Players, including full teams for 7-day blocks. WhatsApp us your requirement for a custom quote and a dedicated point of contact.' },
  { q: 'What if a Switch Player doesn’t show up?', a: 'We back every booking with a replacement guarantee. If a Switch Player is a no-show or not the right fit, we dispatch a replacement fast — usually within 24 hours — so your business stays covered.' },
  { q: 'How does pricing work for longer bookings?', a: 'You can hire by the hour (1–4 hrs), by the full day, or in 2-day and 7-day blocks. The longer the booking, the lower the rate per Switch Player. Talk to us on WhatsApp for exact rates for your business.' },
  { q: 'Are all Switch Players verified?', a: 'Yes. Every Switch Player is Aadhaar-verified, background-checked and skill-assessed before they’re approved on the platform. On arrival, OTP verification confirms the right person reached your site.' },
  { q: 'Do you provide GST invoices and how is payment handled?', a: 'Monthly plans are billed in advance; hourly and daily bookings are invoiced against the hours worked. Pay via UPI, cards or bank transfer, and we provide proper invoices for your business records. Ask our team to set up a business account.' },
  { q: 'Can I try a Switch Player before committing to a longer booking?', a: 'Yes. Start with a trial shift to see the quality before you scale to a full day, a 7-day team or an ongoing arrangement. If the Switch Player isn’t the right fit, we replace them — no questions asked.' },
  { q: 'Which areas of Gurgaon do you cover?', a: 'All major sectors and localities — DLF, Sushant Lok, Palam Vihar, Udyog Vihar, Cyber City, Sohna Road, MG Road and Sectors 1–49 — across pincodes 122001 to 122022. Tell us your location and we’ll confirm availability.' },
]

export const WHY_US = [
  { title: 'Replacement Guarantee', desc: 'A no-show won’t stop your business. We dispatch a replacement fast — usually within 24 hours.' },
  { title: 'Aadhaar-Verified Staff', desc: 'Every Switch Player is Aadhaar-verified, document-checked and interviewed before they reach your site.' },
  { title: 'Staff in a Day', desc: 'No agency runaround. Tell us your need and get matched with the right Switch Players within hours.' },
  { title: 'Bulk & Weekly Teams', desc: 'Need 3, 5 or a full team for 7 days? We deploy at scale with a dedicated point of contact.' },
  { title: 'Simple, Transparent Billing', desc: 'One clear rate, no agency commissions or hidden charges. Clean invoices for your business records.' },
  { title: '24/7 Support', desc: 'Our team is always available to find the right person and sort out any issue, fast.' },
]

export const FORM_ROLES = [
  'Store / General Helper','Waiter','Kitchen Helper','Cook / Chef','Dishwasher',
  'Housekeeping','Security Guard','Picker / Packer','Loader','Driver','Delivery Rider',
  'Receptionist / Front Desk','Bartender','Bouncer','Promoter','Other / Multiple',
]

export const HOW_SHOTS = ['/screen-2.png', '/screen-home.png', '/screen-3.png']

/* The eight service tiles of the editorial grid. The grid spans tiles via
   :nth-child, so do not reorder. `focus` is the object-position for the photo.
   These are square/portrait shots with the subject's head near the top edge, so
   a plain `center` crop decapitates them in a wide two-column tile. The X is the
   subject's centre; the Y is set from the headroom above the hair, not the face,
   so the head survives the shallowest crop. Re-measure if an image changes. */
export const SERVICE_TILES = [
  { slug: 'home-cleaning-gurgaon',    name: 'Housekeeping',            img: '/sw-maid.jpg',            desc: 'Daily upkeep for offices, shops & premises.', focus: '54% 6%' },
  { slug: 'cook-gurgaon',             name: 'Cook / Chef',             img: '/sw-cook.jpg',            desc: 'Kitchen production for cafés, messes & catering.', focus: '51% 4%' },
  { slug: 'driver-gurgaon',           name: 'Driver',                  img: '/sw-driver.jpg',          desc: 'Commercial runs, deliveries & staff transport.', focus: '42% 14%' },
  { slug: 'delivery-worker-gurgaon',  name: 'Delivery Rider',          img: '/delivery-rider.jpg',     desc: 'Last-mile delivery, loading & movers.', focus: '45% 10%' },
  { slug: 'nanny-gurgaon',            name: 'Caretaker / Elder Care',  img: '/sw-caretaker.jpg',       desc: 'Baby care, elder care & home assistance.', focus: '49% 6%' },
  { slug: 'security-guard-gurgaon',   name: 'Security Guard',          img: '/sw-security-guard.jpg',  desc: 'Gate duty, premises security & night patrol.', focus: '50% 8%' },
  { slug: 'store-helper-gurgaon',     name: 'General / Store Helper',  img: '/sw-general-helper.jpg',  desc: 'Billing support, stocking, loading & shop-floor help.', focus: '46% 3%' },
  { slug: 'factory-warehouse-gurgaon',name: 'Picker / Packer',         img: '/sw-factory-helper.jpg',  desc: 'Warehouse picking, packing, sorting & dispatch.', focus: '51% 0%' },
]
