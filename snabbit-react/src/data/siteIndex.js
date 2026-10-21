/* Lightweight link index for the header, footer and home page. Kept apart from
   seoData.js / industryPages.js so the home bundle doesn't ship every page's
   full content just to render a list of links. */

const SERVICES = [
  { id: 'home-cleaning', name: 'Home Cleaning' },
  { id: 'cook', name: 'Cook' },
  { id: 'delivery-worker', name: 'Delivery Switch Player' },
  { id: 'nanny', name: 'Nanny' },
  { id: 'security-guard', name: 'Security Guard' },
  { id: 'store-helper', name: 'Store Helper' },
  { id: 'factory-warehouse', name: 'Factory / Warehouse' },
]

export const SERVICE_LIST = SERVICES.map(s => ({
  id: s.id,
  name: s.name,
  slug: `${s.id}-gurgaon`,
  pages: [
    { label: `${s.name} in Gurgaon`, slug: `${s.id}-gurgaon` },
    { label: 'Pricing & Rates', slug: `${s.id}-cost-gurgaon` },
    { label: 'How to Hire', slug: `hire-${s.id}-gurgaon` },
    { label: 'Near Me', slug: `${s.id}-near-me-gurgaon` },
    { label: 'Same Day', slug: `same-day-${s.id}-gurgaon` },
  ],
}))

export const INDUSTRY_LINKS = [
  { slug: 'warehouse-staffing-gurgaon', name: 'Warehouse Staffing' },
  { slug: 'event-staffing-gurgaon', name: 'Event & Banquet Staffing' },
  { slug: 'restaurant-staffing-gurgaon', name: 'Restaurant Staffing' },
  { slug: 'office-staffing-gurgaon', name: 'Office & Co-working Staffing' },
  { slug: 'retail-staffing-gurgaon', name: 'Retail & Store Staffing' },
]
