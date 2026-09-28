import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import {
  BrandBand,
  Crumbs,
  CtaFeature,
  Faq,
  HeroArt,
  StatsRow,
  TrialTickets,
} from '../components/ui/Blocks.jsx'
import { SERVICE_LIST } from '../data/seoData'
import './AboutPage.css'
import './StaffingPage.css'

const BASE_URL = 'https://switchlocally.com'
const CANONICAL = `${BASE_URL}/staffing-gurgaon`
const APP_URL = 'https://app.switchlocally.com/'
const PHONE = '+918796894500'
const WA_MSG = encodeURIComponent("Hi Switch — I need staffing for my business in Gurgaon.")
const WHATSAPP_URL = `https://wa.me/${PHONE.replace('+', '')}?text=${WA_MSG}`

const TITLE = 'Staffing Agency in Gurgaon | Hire Verified Staff — Switch'
const DESCRIPTION = 'Switch is a staffing agency in Gurgaon for shops, restaurants, warehouses, offices & events. Hire Aadhaar-verified store helpers, guards, waiters, cooks, housekeeping & factory workers — bulk & weekly teams, replacement guaranteed, transparent rates. Same-day staffing across Gurgaon.'

const INDUSTRIES = [
  { ico: 'store', title: 'Retail & Shops', slug: 'retail-staffing-gurgaon', desc: 'Store helpers, sales staff and stock hands for shops, showrooms and malls across DLF, MG Road and Galleria.' },
  { ico: 'utensils', title: 'Restaurants & Cafés', slug: 'restaurant-staffing-gurgaon', desc: 'Waiters, kitchen helpers, cooks, dishwashers and bartenders — for daily service, weekends and rush hours.' },
  { ico: 'warehouse', title: 'Warehouses & Factories', slug: 'warehouse-staffing-gurgaon', desc: 'Loaders, packers, pickers and factory helpers for Udyog Vihar, IMT Manesar and industrial units.' },
  { ico: 'building', title: 'Offices & Corporates', slug: 'office-staffing-gurgaon', desc: 'Office boys, housekeeping, pantry staff and front-desk support for offices in Cyber City and Sohna Road.' },
  { ico: 'party', title: 'Events & Banquets', slug: 'event-staffing-gurgaon', desc: 'Waiters, bartenders, bouncers and helpers for weddings, parties, exhibitions and corporate events.' },
  { ico: 'shield', title: 'Security & Facility', desc: 'Trained security guards, bouncers and facility staff for buildings, sites, gated societies and events.' },
]

const STEPS = [
  { title: 'Tell us what you need', desc: 'Message us on WhatsApp — share the role, headcount, location and dates. Takes two minutes.' },
  { title: 'We match verified staff', desc: 'We assign Aadhaar-verified, background-checked Switch Players suited to your role and shift timings.' },
  { title: 'Staff show up on site', desc: 'Your team reports on time at your location — for a single shift, a full day, or a 7-day stretch.' },
  { title: 'Transparent billing', desc: 'One clear rate with a proper invoice, and a fast replacement if anyone falls short.' },
]

const WHY = [
  { ico: 'shield', title: 'Every Worker Verified', desc: 'Aadhaar-verified, document-checked and interviewed before they ever reach your site — no strangers on your floor.' },
  { ico: 'timer', title: 'Same-Day & Fast', desc: 'Need staff today? We deploy quickly across Gurgaon — often within hours for common roles.' },
  { ico: 'cal', title: 'Bulk & Weekly Teams', desc: 'One worker or a full team for 7 days straight — we scale to your peak demand with a single point of contact.' },
  { ico: 'check', title: 'Replacement Guarantee', desc: 'A no-show shouldn’t stop your business. If someone doesn’t turn up or fit, we dispatch a replacement fast.' },
  { ico: 'wallet', title: 'Transparent Billing', desc: 'No hidden agency commissions. Clear rates and proper invoices for your records.' },
  { ico: 'msg', title: 'Dedicated Support', desc: 'A real team on WhatsApp to help you staff up, handle changes and resolve issues — any day of the week.' },
]

const AREAS = [
  'DLF Phase 1', 'DLF Phase 3', 'DLF Phase 4', 'Cyber City', 'Udyog Vihar',
  'Sohna Road', 'MG Road', 'Galleria Market', 'Sushant Lok', 'Palam Vihar',
  'Golf Course Road', 'Golf Course Ext Road', 'Sector 14', 'Sector 29',
  'Sector 44', 'Sector 47', 'Sector 49', 'Sector 56', 'IMT Manesar', 'New Gurgaon',
]

/* Area anchors — the homepage coverage map links to /staffing-gurgaon#<id>. */
const areaId = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')

const TINTS = ['t-lav', 't-peach', 't-sky', 't-mint', 't-pink', 't-grey']

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
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="sw-wrap">
        <Crumbs items={[['Staffing in Gurgaon']]} />

        {/* Hero */}
        <section className="sw-hero ab-hero">
          <div>
            <p className="sw-eyebrow">Staffing in Gurgaon</p>
            <h1 className="sw-h1">
              Staffing agency in Gurgaon —<br />
              <em>verified staff, on demand.</em>
            </h1>
            <p className="sw-lead">
              Switch is Gurgaon&apos;s on-demand staffing agency for shops, restaurants, warehouses,
              offices and events. Hire Aadhaar-verified store helpers, guards, waiters, cooks,
              housekeeping and factory workers — for a shift, a day, or a full week. Bulk teams,
              replacement guaranteed, and you pay against a clear invoice.
            </p>
            <div className="sw-btns">
              <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="sw-btn">
                Get staff for your business <Icon name="arrow" />
              </a>
              <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="sw-btn line">
                Open the Switch App
              </a>
            </div>
            <div className="sw-checks">
              {['Aadhaar verified', 'Same-day staffing', 'Replacement guarantee', 'Clear invoices'].map((x) => (
                <span className="sw-pill sw-live" key={x}>
                  {x}
                </span>
              ))}
            </div>
          </div>
          <HeroArt
            img="/hero-workers.jpg"
            alt="Switch staff in uniform ready for work in Gurgaon"
            badge={{ title: 'Staff confirmed', sub: 'Same-day across Gurgaon' }}
          />
        </section>

        <StatsRow
          items={[
            { value: '20,000+', label: 'Verified Workers' },
            { value: 'Same-day', label: 'Deployment' },
            { value: '12+', label: 'Staff Categories' },
            { value: '4.8 ★', label: 'Average Rating' },
          ]}
        />

        <BrandBand />

        {/* Intro copy */}
        <section className="sw-sec">
          <div className="ab-split">
            <div className="sw-head">
              <p className="sw-eyebrow">Staffing, made simple</p>
              <h2 className="sw-h2">
                Reliable staffing in Gurgaon, <em>without the agency runaround.</em>
              </h2>
            </div>
            <div className="ab-prose">
              <p>
                Finding dependable staff in Gurgaon is hard — middlemen, delays, no-shows and no
                accountability. <strong>Switch fixes that.</strong> We&apos;re a modern staffing agency that puts
                verified, background-checked workers on your floor exactly when you need them, whether that&apos;s
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

        <TrialTickets />

        {/* Roles we staff */}
        <section className="sw-sec" id="roles">
          <div className="sw-head">
            <p className="sw-eyebrow">Roles we staff</p>
            <h2 className="sw-h2">
              Every role. <em>One platform.</em>
            </h2>
            <p className="sw-lead">
              Hire any of these in minutes — explore rates, availability and how it works for each role.
            </p>
          </div>
          <div className="st-svc-grid">
            {SERVICE_LIST.map((s) => (
              <Link className="sw-card sw-press st-svc" to={`/${s.slug}`} key={s.id}>
                <span className="st-svc-name">{s.name} in Gurgaon</span>
                <span className="st-svc-cta">View rates &amp; hire →</span>
              </Link>
            ))}
          </div>
        </section>

        {/* Industries */}
        <section className="sw-sec" id="industries">
          <div className="sw-head">
            <p className="sw-eyebrow">Industries we serve</p>
            <h2 className="sw-h2">
              Staffing for every <em>business in Gurgaon.</em>
            </h2>
          </div>
          <div className="sw-grid sw-g3">
            {INDUSTRIES.map((w, i) => (
              <div className="sw-card ab-card" key={w.title}>
                <span className={`sw-sq ${TINTS[i % TINTS.length]}`}>
                  <Icon name={w.ico} />
                </span>
                <h3 className="sw-h3">{w.title}</h3>
                <p>{w.desc}</p>
                {w.slug && (
                  <Link className="sw-link" to={`/${w.slug}`}>
                    {w.title} staffing <Icon name="arrow" />
                  </Link>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section className="sw-sec" id="how">
          <div className="sw-head">
            <p className="sw-eyebrow">How it works</p>
            <h2 className="sw-h2">
              Staffed up in <em>four steps.</em>
            </h2>
          </div>
          <div className="sw-grid sw-g4">
            {STEPS.map((s, i) => (
              <div className="sw-card sw-step" key={s.title}>
                <span className="n">STEP {i + 1}</span>
                <h3 className="sw-h3">{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Why Switch */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Why Switch</p>
            <h2 className="sw-h2">
              Why businesses choose Switch <em>for staffing in Gurgaon.</em>
            </h2>
          </div>
          <div className="sw-grid sw-g3">
            {WHY.map((w, i) => (
              <div className="sw-card ab-card" key={w.title}>
                <span className={`sw-sq ${TINTS[(i + 2) % TINTS.length]}`}>
                  <Icon name={w.ico} />
                </span>
                <h3 className="sw-h3">{w.title}</h3>
                <p>{w.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Areas */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Where we serve</p>
            <h2 className="sw-h2">
              Staffing across <em>all of Gurgaon.</em>
            </h2>
            <p className="sw-lead">From Cyber City to IMT Manesar — verified staff, right around the corner.</p>
          </div>
          <div className="ab-areas" id="areas">
            {AREAS.map((a) => (
              <span className="ab-area" id={areaId(a)} key={a}>
                <Icon name="pin" />
                {a}
              </span>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="sw-sec" id="faq">
          <div className="sw-head">
            <p className="sw-eyebrow">FAQs</p>
            <h2 className="sw-h2">
              Staffing in Gurgaon — <em>your questions answered.</em>
            </h2>
          </div>
          <Faq items={FAQS} />
        </section>

        {/* CTA */}
        <CtaFeature
          title={
            <>
              Need staff in Gurgaon? <em>Let&apos;s Switch.</em>
            </>
          }
          sub="Tell us the role, headcount and dates — we'll put verified, reliable staff on your site fast. Bulk teams, weekly staffing and same-day deployment across Gurgaon."
          msg="Hi Switch — I need staffing for my business in Gurgaon."
          photos={['/sw-waiter.jpg', '/sw-factory-helper.jpg']}
        />
        <p className="ab-fine">Transparent rates. Clean invoices. Replacement guaranteed.</p>
      </main>
      <Footer />
    </>
  )
}
