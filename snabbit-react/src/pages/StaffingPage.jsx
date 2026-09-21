import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Nav from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import { SERVICE_LIST } from '../data/seoData'
import './AboutPage.css'
import './StaffingPage.css'

const BASE_URL = 'https://switchlocally.com'
const CANONICAL = `${BASE_URL}/staffing-gurgaon`
const APP_URL = 'https://app.switchlocally.com/'
const PHONE = '+919205617375'
const WA_MSG = encodeURIComponent("Hi Switch — I need staffing for my business in Gurgaon.")
const WHATSAPP_URL = `https://wa.me/${PHONE.replace('+', '')}?text=${WA_MSG}`

const TITLE = 'Staffing Agency in Gurgaon | Hire Verified Staff — Switch'
const DESCRIPTION = 'Switch is a staffing agency in Gurgaon for shops, restaurants, warehouses, offices & events. Hire Aadhaar-verified store helpers, guards, waiters, cooks, housekeeping & factory workers — bulk & weekly teams, replacement guaranteed, transparent rates. Same-day staffing across Gurgaon.'

const INDUSTRIES = [
  { ico: '🛍️', title: 'Retail & Shops', desc: 'Store helpers, sales staff and stock hands for shops, showrooms and malls across DLF, MG Road and Galleria.' },
  { ico: '🍽️', title: 'Restaurants & Cafés', desc: 'Waiters, kitchen helpers, cooks, dishwashers and bartenders — for daily service, weekends and rush hours.' },
  { ico: '🏭', title: 'Warehouses & Factories', desc: 'Loaders, packers, pickers and factory helpers for Udyog Vihar, IMT Manesar and industrial units.' },
  { ico: '🏢', title: 'Offices & Corporates', desc: 'Office boys, housekeeping, pantry staff and front-desk support for offices in Cyber City and Sohna Road.' },
  { ico: '🎉', title: 'Events & Banquets', desc: 'Waiters, bartenders, bouncers and helpers for weddings, parties, exhibitions and corporate events.' },
  { ico: '🛡️', title: 'Security & Facility', desc: 'Trained security guards, bouncers and facility staff for buildings, sites, gated societies and events.' },
]

const STEPS = [
  { title: 'Tell us what you need', desc: 'Message us on WhatsApp or call — share the role, headcount, location and dates. Takes two minutes.' },
  { title: 'We match verified staff', desc: 'We assign Aadhaar-verified, background-checked Switch Players suited to your role and shift timings.' },
  { title: 'Staff show up on site', desc: 'Your team reports on time at your location — for a single shift, a full day, or a 7-day stretch.' },
  { title: 'Transparent billing', desc: 'One clear rate with a proper invoice, and a fast replacement if anyone falls short.' },
]

const WHY = [
  { ico: '🆔', title: 'Every Worker Verified', desc: 'Aadhaar-verified, document-checked and interviewed before they ever reach your site — no strangers on your floor.' },
  { ico: '⚡', title: 'Same-Day & Fast', desc: 'Need staff today? We deploy quickly across Gurgaon — often within hours for common roles.' },
  { ico: '👥', title: 'Bulk & Weekly Teams', desc: 'One worker or a full team for 7 days straight — we scale to your peak demand with a single point of contact.' },
  { ico: '🔁', title: 'Replacement Guarantee', desc: 'A no-show shouldn’t stop your business. If someone doesn’t turn up or fit, we dispatch a replacement fast.' },
  { ico: '💳', title: 'Transparent Billing', desc: 'No hidden agency commissions. Clear rates and proper invoices for your records.' },
  { ico: '📞', title: 'Dedicated Support', desc: 'A real team on WhatsApp to help you staff up, handle changes and resolve issues — any day of the week.' },
]

const AREAS = [
  'DLF Phase 1', 'DLF Phase 3', 'DLF Phase 4', 'Cyber City', 'Udyog Vihar',
  'Sohna Road', 'MG Road', 'Galleria Market', 'Sushant Lok', 'Palam Vihar',
  'Golf Course Road', 'Golf Course Ext Road', 'Sector 14', 'Sector 29',
  'Sector 44', 'Sector 47', 'Sector 49', 'Sector 56', 'IMT Manesar', 'New Gurgaon',
]

/* Area anchors — the homepage coverage map links to /staffing-gurgaon#<id>. */
const areaId = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')

const FAQS = [
  { q: 'Which is the best staffing agency in Gurgaon?', a: 'Switch is a leading staffing agency in Gurgaon, trusted by shops, restaurants, warehouses, offices and event organisers. Every worker is Aadhaar-verified and background-checked, you get a replacement guarantee, and every booking is invoiced clearly — transparent rates.' },
  { q: 'What types of staff can I hire in Gurgaon through Switch?', a: 'You can hire store helpers, security guards, waiters, bartenders, cooks, kitchen helpers, housekeeping staff, office boys, factory and warehouse workers, drivers and more — for a single shift, a full day, or weekly teams.' },
  { q: 'How much does staffing cost in Gurgaon?', a: 'Rates depend on the role, skill level and duration. Pricing is transparent and fixed upfront with no hidden agency commission, and you pay against a clear invoice. Message us with your requirement for a quick quote.' },
  { q: 'Can I get staff on the same day?', a: 'Yes. For common roles we can deploy verified staff across Gurgaon on the same day — often within a few hours. For large or specialised teams we recommend a day’s notice.' },
  { q: 'Are the workers verified and background-checked?', a: 'Yes. Every Switch Player is Aadhaar-verified, document-checked and personally screened before being assigned to your site, so you never have strangers on your floor.' },
  { q: 'Can I hire staff in bulk or for a full week?', a: 'Absolutely. Switch specialises in bulk and weekly staffing — deploy a full team for 7 days straight during sales, events or peak season, with a dedicated point of contact.' },
  { q: 'Which areas of Gurgaon do you cover?', a: 'We staff businesses across all of Gurgaon — DLF, Cyber City, Udyog Vihar, Sohna Road, MG Road, Golf Course Road, Sushant Lok, Palam Vihar, IMT Manesar, New Gurgaon and every sector and pincode from 122001 to 122022.' },
  { q: 'How does payment work?', a: 'Monthly plans are billed in advance for the plan period. Hourly, daily and weekly bookings are invoiced against the hours worked. Either way you receive a proper invoice for your records.' },
  { q: 'What happens if a worker doesn’t show up?', a: 'Switch offers a replacement guarantee. If a worker doesn’t turn up or isn’t the right fit, we dispatch a replacement fast — usually within 24 hours — so your business keeps running.' },
]

export default function StaffingPage() {
  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0)
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('anim-in'); obs.unobserve(e.target) }
      }),
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    )
    document.querySelectorAll('[data-anim]').forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${BASE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Staffing in Gurgaon', item: CANONICAL },
    ],
  }

  const serviceSchema = {
    '@context': 'https://schema.org',
    '@type': 'Service',
    serviceType: 'Staffing Agency',
    name: 'Staffing in Gurgaon',
    description: DESCRIPTION,
    url: CANONICAL,
    areaServed: { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
    provider: {
      '@type': 'LocalBusiness',
      name: 'Switch',
      url: BASE_URL,
      email: 'hello@switchlocally.com',
      telephone: PHONE,
      areaServed: { '@type': 'City', name: 'Gurgaon' },
    },
  }

  const faqSchema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQS.map(f => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  }

  return (
    <>
      <Helmet>
        <title>{TITLE}</title>
        <meta name="description" content={DESCRIPTION} />
        <meta name="keywords" content="staffing in Gurgaon, staffing agency Gurgaon, staffing services Gurgaon, manpower supply Gurgaon, hire staff Gurgaon, contract staff Gurgaon, bulk hiring Gurgaon, temporary staffing Gurgaon, restaurant staff Gurgaon, warehouse workers Gurgaon, security guard agency Gurgaon, event staff Gurgaon, housekeeping staff Gurgaon, office boy Gurgaon, on-demand staffing Gurgaon" />
        <meta name="robots" content="index, follow" />
        <meta name="geo.region" content="IN-HR" />
        <meta name="geo.placename" content="Gurgaon" />
        <meta name="geo.position" content="28.4595;77.0266" />
        <meta name="ICBM" content="28.4595, 77.0266" />
        <link rel="canonical" href={CANONICAL} />
        <meta property="og:title" content={TITLE} />
        <meta property="og:description" content={DESCRIPTION} />
        <meta property="og:url" content={CANONICAL} />
        <meta property="og:type" content="website" />
        <meta property="og:site_name" content="Switch" />
        <meta property="og:image" content={`${BASE_URL}/hero-workers.jpg`} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={TITLE} />
        <meta name="twitter:description" content={DESCRIPTION} />
        <meta name="twitter:image" content={`${BASE_URL}/hero-workers.jpg`} />
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
        <script type="application/ld+json">{JSON.stringify(serviceSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
      </Helmet>
      <Nav />
      <main className="ab-root">
        {/* Hero */}
        <section className="ab-hero">
          <div className="ab-hero-bg" aria-hidden="true">
            <div className="ab-hero-grid" />
            <div className="ab-hero-glow" />
          </div>
          <div className="ab-w">
            <div className="ab-hero-inner" data-anim>
              <span className="ab-tag">Staffing in Gurgaon</span>
              <h1 className="ab-h1">
                Staffing agency in Gurgaon —<br />
                <em>verified staff, on demand.</em>
              </h1>
              <p className="ab-lead">
                Switch is Gurgaon's on-demand staffing agency for shops, restaurants, warehouses,
                offices and events. Hire Aadhaar-verified store helpers, guards, waiters, cooks,
                housekeeping and factory workers — for a shift, a day, or a full week. Bulk teams,
                replacement guaranteed, and you pay against a clear invoice.
              </p>
              <div className="ab-hero-ctas">
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ab-cta-primary">Get staff for your business →</a>
                <a href={`tel:${PHONE}`} className="ab-cta-secondary">Call +91 92056 17375</a>
              </div>
              <div className="ab-stats">
                <div className="ab-stat"><div className="ab-stat-num">500+</div><div className="ab-stat-lbl">Verified Workers</div></div>
                <div className="ab-stat"><div className="ab-stat-num">Same-day</div><div className="ab-stat-lbl">Deployment</div></div>
                <div className="ab-stat"><div className="ab-stat-num">12+</div><div className="ab-stat-lbl">Staff Categories</div></div>
                <div className="ab-stat"><div className="ab-stat-num">4.8 ★</div><div className="ab-stat-lbl">Average Rating</div></div>
              </div>
            </div>
          </div>
        </section>

        {/* Intro copy */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Staffing, made simple</span>
              <h2 className="ab-h2">Reliable staffing in Gurgaon,<br />without the agency runaround.</h2>
            </div>
            <div className="ab-text" data-anim style={{ '--delay': '80ms' }}>
              <p>
                Finding dependable staff in Gurgaon is hard — middlemen, delays, no-shows and no
                accountability. <strong>Switch fixes that.</strong> We're a modern staffing agency that puts
                verified, background-checked workers on your floor exactly when you need them, whether that's
                one waiter for tonight or a 20-person warehouse team for a week.
              </p>
              <p>
                From <strong>staffing in Gurgaon</strong> for a single busy weekend to ongoing weekly teams,
                every worker is Aadhaar-verified, you get a replacement guarantee, and rates are transparent —
                you pay against a clear invoice.
              </p>
            </div>
          </div>
        </section>

        {/* Roles we staff */}
        <section className="ab-sec ab-sec-alt">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Roles we staff</span>
              <h2 className="ab-h2">Every role. One platform.</h2>
              <p className="ab-sub">Hire any of these in minutes — explore rates, availability and how it works for each role.</p>
            </div>
            <div className="st-svc-grid" data-anim style={{ '--delay': '80ms' }}>
              {SERVICE_LIST.map(s => (
                <Link className="st-svc" to={`/${s.slug}`} key={s.id}>
                  <span className="st-svc-name">{s.name} in Gurgaon</span>
                  <span className="st-svc-cta">View rates & hire →</span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Industries */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Industries we serve</span>
              <h2 className="ab-h2">Staffing for every business in Gurgaon.</h2>
            </div>
            <div className="ab-grid">
              {INDUSTRIES.map((w, i) => (
                <div className="ab-card" key={i} data-anim style={{ '--delay': `${(i % 3) * 80}ms` }}>
                  <div className="ab-card-ico">{w.ico}</div>
                  <h3 className="ab-card-title">{w.title}</h3>
                  <p className="ab-card-desc">{w.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="ab-sec ab-sec-alt">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">How it works</span>
              <h2 className="ab-h2">Staffed up in four steps.</h2>
            </div>
            <div className="st-steps" data-anim style={{ '--delay': '80ms' }}>
              {STEPS.map((s, i) => (
                <div className="st-step" key={i}>
                  <div className="st-step-num">STEP {i + 1}</div>
                  <h3 className="st-step-title">{s.title}</h3>
                  <p className="st-step-desc">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Why Switch */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Why Switch</span>
              <h2 className="ab-h2">Why businesses choose Switch<br />for staffing in Gurgaon.</h2>
            </div>
            <div className="ab-grid">
              {WHY.map((w, i) => (
                <div className="ab-card ab-card--why" key={i} data-anim style={{ '--delay': `${(i % 3) * 80}ms` }}>
                  <div className="ab-card-ico">{w.ico}</div>
                  <h3 className="ab-card-title">{w.title}</h3>
                  <p className="ab-card-desc">{w.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Areas */}
        <section className="ab-sec ab-sec-alt">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Where we serve</span>
              <h2 className="ab-h2">Staffing across all of Gurgaon.</h2>
              <p className="ab-sub">From Cyber City to IMT Manesar — verified staff, right around the corner.</p>
            </div>
            <div className="ab-areas" id="areas" data-anim style={{ '--delay': '80ms' }}>
              {AREAS.map(a => (
                <span className="ab-area-pill" id={areaId(a)} key={a}>{a}</span>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">FAQs</span>
              <h2 className="ab-h2">Staffing in Gurgaon — your questions answered.</h2>
            </div>
            <div className="st-faqs" data-anim style={{ '--delay': '80ms' }}>
              {FAQS.map((f, i) => (
                <details className="st-faq" key={i}>
                  <summary>{f.q}</summary>
                  <p className="st-faq-a">{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="ab-cta-sec">
          <div className="ab-w">
            <div className="ab-cta" data-anim>
              <h2 className="ab-cta-h">Need staff in Gurgaon? Let's Switch.</h2>
              <p className="ab-cta-p">
                Tell us the role, headcount and dates — we'll put verified, reliable staff on your
                site fast. Bulk teams, weekly staffing and same-day deployment across Gurgaon.
              </p>
              <div className="ab-cta-btns">
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ab-cta-primary">Get staff for your business →</a>
                <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="ab-cta-secondary">Open the Switch App</a>
              </div>
              <p className="ab-cta-fine">Transparent rates. Clean invoices. Replacement guaranteed.</p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
