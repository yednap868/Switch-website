import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs, CtaFeature, HeroArt, ReviewVideos, StatsRow } from '../components/ui/Blocks.jsx'
import './AboutPage.css'

const PHONE = '+918796894500'
const WA_MSG = encodeURIComponent("Hi Switch — I'd like to hire staff for my business in Gurgaon.")
const WHATSAPP_URL = `https://wa.me/${PHONE.replace('+','')}?text=${WA_MSG}`

const WHAT_WE_DO = [
  {
    ico: 'building',
    title: 'Business Staffing',
    desc: 'Store helpers, security guards, factory & warehouse Switch Players, waiters, bartenders, bouncers, cooks and housekeeping — for shops, restaurants, warehouses, offices and events of every size.',
  },
  {
    ico: 'cal',
    title: 'Bulk & Weekly Teams',
    desc: 'Need 3, 5 or a full team for 7 days straight? We deploy verified Switch Players at scale, with a dedicated point of contact and priority coverage.',
  },
  {
    ico: 'check',
    title: 'Replacement Guarantee',
    desc: 'A no-show shouldn’t stop your business. If a Switch Player doesn’t turn up or isn’t the right fit, we dispatch a replacement fast — usually within 24 hours.',
  },
  {
    ico: 'shield',
    title: 'Verified at Every Step',
    desc: 'Every Switch Player on Switch is Aadhaar-verified, document-checked and personally interviewed before being assigned to your site.',
  },
  {
    ico: 'wallet',
    title: 'Simple & Transparent',
    desc: 'Hire in minutes on WhatsApp, switchlocally.com or the Switch App. Transparent rates, with proper invoices for your records.',
  },
  {
    ico: 'heart',
    title: 'Home Services Too',
    desc: 'Beyond business, we also place trusted cooks, maids, caretakers and nannies for your home — the same verification, the same reliability.',
  },
]

const WHY_SWITCH = [
  {
    ico: 'sparkles',
    title: 'One Platform, Every Service',
    desc: 'From domestic help to business staffing — we do it all. No need to call five different agencies.',
  },
  {
    ico: 'shield',
    title: 'Aadhaar-Verified Switch Players',
    desc: 'Every Switch Player on our platform is Aadhaar-verified and background-checked. Your safety is not negotiable.',
  },
  {
    ico: 'phone',
    title: 'Switch Players at a Click',
    desc: 'No long waits, no endless back-and-forth. Book a verified Switch Player in minutes on switchlocally.com or the Switch App.',
  },
  {
    ico: 'wallet',
    title: 'Transparent, Honest Billing',
    desc: 'One clear rate agreed up front — no hidden charges, no agency commissions, no surprises on the invoice.',
  },
  {
    ico: 'check',
    title: 'Replacement Guarantee',
    desc: 'Not happy with the assigned Switch Player? We will replace them — fast, no questions asked.',
  },
  {
    ico: 'msg',
    title: '24/7 Support',
    desc: 'Our team is always available to help you find the right person and resolve any concerns along the way.',
  },
]

const AREAS = [
  'DLF Phase 1','DLF Phase 3','DLF Phase 4','DLF Queens Enclave',
  'Sushant Lok Phase 1','Sushant Lok Phase 2','Sushant Lok Phase 3',
  'Palam Vihar','Palam Vihar Extension','Udyog Vihar','Sohna Road',
  'Cyber City','MG Road','Galleria Market','Railway Road','Basai',
  'Chakkarpur','Sikanderpur','Nathupur',
  'Greenwood City','Malibu Towne','Sun City',
  'Sector 14','Sector 15','Sector 17','Sector 17B','Sector 23',
  'Sector 23A','Sector 24','Sector 25','Sector 26','Sector 27',
  'Sector 28','Sector 31','Sector 40','Sector 47','Sector 48','Sector 49',
]

const PINCODES = ['122001','122002','122006','122009','122010','122017','122018','122022']

const TINTS = ['t-lav', 't-peach', 't-sky', 't-mint', 't-pink', 't-grey']

const STATS = [
  { num: '20,000+', lbl: 'Verified Partners' },
  { num: '1,500+', lbl: 'Bookings Served' },
  { num: '12+', lbl: 'Service Categories' },
  { num: '4.8 ★', lbl: 'Average Rating' },
]

export default function AboutPage() {
  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0)
  }, [])

  const aboutSchema = {
    '@context': 'https://schema.org',
    '@type': 'AboutPage',
    name: 'About Switch — Gurgaon\'s Trusted Home & Business Staffing Platform',
    url: 'https://switchlocally.com/about',
    description: 'Switch is Gurgaon\'s most trusted home and business staffing platform. Founded in 2026, we connect families and businesses across Gurgaon with Aadhaar-verified, background-checked domestic Switch Players and business staff.',
    publisher: {
      '@type': 'Organization',
      name: 'Switch',
      url: 'https://switchlocally.com',
    },
  }

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://switchlocally.com/' },
      { '@type': 'ListItem', position: 2, name: 'About Us', item: 'https://switchlocally.com/about' },
    ],
  }

  return (
    <>
      <Helmet>
        <title>About Switch — Gurgaon's Business Staffing Platform</title>
        <meta name="description" content="Switch is Gurgaon's business staffing platform. Founded in 2026, we connect 20,000+ Aadhaar-verified Switch Players with shops, restaurants, warehouses, offices and events across DLF, Udyog Vihar, Cyber City, Sohna Road and all pincodes 122001–122022. Hire store helpers, guards, waiters, cooks, housekeeping — bulk and weekly teams, replacement guaranteed." />
        <meta name="keywords" content="about Switch, staffing agency Gurgaon, manpower supply Gurgaon, verified Switch Players Gurgaon, hire staff for business Gurgaon, bulk hiring Gurgaon, contract staff Gurgaon, restaurant staff Gurgaon, warehouse Switch Players Gurgaon, store helper Gurgaon, on-demand staffing Gurgaon, switchlocally.com, Switch App" />
        <link rel="canonical" href="https://switchlocally.com/about" />
        <meta property="og:title" content="About Switch — Gurgaon's Business Staffing Platform" />
        <meta property="og:description" content="Founded in 2026. 20,000+ verified Switch Players. Staffing shops, restaurants, warehouses, offices and events across Gurgaon — store helpers, guards, waiters, cooks, housekeeping. Bulk & weekly teams." />
        <meta property="og:url" content="https://switchlocally.com/about" />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <script type="application/ld+json">{JSON.stringify(aboutSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
      </Helmet>
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="sw-wrap">
        <Crumbs items={[['About Us']]} />

        {/* Hero */}
        <section className="sw-hero ab-hero">
          <div>
            <p className="sw-eyebrow">About Switch</p>
            <h1 className="sw-h1">
              Gurgaon&apos;s staffing partner for <em>shops, restaurants &amp; offices.</em>
            </h1>
            <p className="sw-lead">
              Born in 2026 with one simple idea — staffing your business should never be hard.
              Whether you run a shop, a kitchen, a warehouse or an event, Switch puts verified,
              reliable Switch Players on your floor — for a shift, a day, or a full week.
            </p>
            <div className="sw-btns">
              <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="sw-btn">
                Hire staff for your business <Icon name="arrow" />
              </a>
              <Link to="/partner" className="sw-btn line">
                Become a Partner
              </Link>
            </div>
          </div>
          <HeroArt
            img="/sw-security-guard.jpg"
            alt="A verified Switch Player in uniform"
            badge={{ icon: 'shield', title: 'Aadhaar verified', sub: 'Every Switch Player' }}
          />
        </section>

        <StatsRow items={STATS.map((s) => ({ value: s.num, label: s.lbl }))} />

        {/* Who We Are */}
        <section className="sw-sec">
          <div className="ab-split">
            <div className="sw-head">
              <p className="sw-eyebrow">Who we are</p>
              <h2 className="sw-h2">
                Built for Gurgaon. <em>Trusted by thousands.</em>
              </h2>
            </div>
            <div className="ab-prose">
              <p>
                We are <strong>Switch</strong> — Gurgaon&apos;s business staffing platform.
                Born in 2026, we set out to fix one of the most frustrating problems any business owner faces:
                <em> finding reliable Switch Players who actually show up, without the agency runaround.</em>
              </p>
              <p>
                Whether you need store helpers for a shop in DLF, packers for a warehouse in Udyog Vihar,
                waiters and a bartender for an event in Cyber City, or a 7-day team during a sale —
                Switch has verified Switch Players ready for you. With <strong>20,000+ verified Switch Players</strong> on our platform
                and a fast-growing base of businesses across Gurgaon, Switch is becoming the go-to name
                for dependable staffing across the city.
              </p>
            </div>
          </div>
        </section>

        {/* What We Do */}
        <section className="sw-sec" style={{ paddingTop: 0 }}>
          <div className="sw-head">
            <p className="sw-eyebrow">What we do</p>
            <h2 className="sw-h2">
              Every Switch Player. <em>One platform.</em>
            </h2>
            <p className="sw-lead">
              Running a home or a business is not easy — and finding the right people makes all the difference. At Switch, we bring everything under one roof.
            </p>
          </div>
          <div className="sw-grid sw-g3">
            {WHAT_WE_DO.map((w, i) => (
              <div className="sw-card ab-card" key={w.title}>
                <span className={`sw-sq ${TINTS[i % TINTS.length]}`}>
                  <Icon name={w.ico} />
                </span>
                <h3 className="sw-h3">{w.title}</h3>
                <p>{w.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Mission */}
        <section className="sw-sec" style={{ paddingTop: 0 }}>
          <div className="sw-feature ab-mission">
            <p className="sw-eyebrow">Our mission</p>
            <h2>
              Good staff shouldn&apos;t be <em>hard to find.</em>
            </h2>
            <p>
              Our mission is simple — to make sure every business in Gurgaon can staff up at the right time,
              without the hassle. We have built a platform where verified store helpers, security guards,
              factory and warehouse Switch Players, waiters, bartenders, bouncers, cooks and housekeeping
              are available at the click of a button —
              <strong> background-checked, Aadhaar-verified, and ready to work.</strong>
            </p>
          </div>
        </section>

        {/* Why Switch */}
        <section className="sw-sec" style={{ paddingTop: 0 }}>
          <div className="sw-head">
            <p className="sw-eyebrow">Why Switch</p>
            <h2 className="sw-h2">
              Six reasons businesses <em>trust Switch.</em>
            </h2>
            <p className="sw-lead">
              There are plenty of options out there — here&apos;s why shops, restaurants, warehouses and offices across Gurgaon choose us.
            </p>
          </div>
          <div className="sw-grid sw-g3">
            {WHY_SWITCH.map((w, i) => (
              <div className="sw-card ab-card" key={w.title}>
                <span className={`sw-sq ${TINTS[(i + 3) % TINTS.length]}`}>
                  <Icon name={w.ico} />
                </span>
                <h3 className="sw-h3">{w.title}</h3>
                <p>{w.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Reviews */}
        <section className="sw-sec" style={{ paddingTop: 0 }} id="reviews">
          <div className="sw-head">
            <p className="sw-eyebrow">In their words</p>
            <h2 className="sw-h2">
              Employers on <em>working with Switch.</em>
            </h2>
            <p className="sw-lead">Business owners across Gurgaon on the staff we send and how it works.</p>
          </div>
          <ReviewVideos />
        </section>

        {/* Where We Serve */}
        <section className="sw-sec" style={{ paddingTop: 0 }}>
          <div className="sw-head">
            <p className="sw-eyebrow">Where we serve</p>
            <h2 className="sw-h2">
              Across every corner <em>of Gurgaon.</em>
            </h2>
            <p className="sw-lead">From DLF Cyber City to Sohna Road — Switch is already right around the corner.</p>
          </div>
          <div className="ab-areas">
            {AREAS.map((a) => (
              <span className="ab-area" key={a}>
                <Icon name="pin" />
                {a}
              </span>
            ))}
          </div>
          <div className="sw-card ab-pins">
            <b>All pincodes:</b>
            {PINCODES.map((p) => (
              <span key={p}>{p}</span>
            ))}
          </div>
        </section>

        {/* Story */}
        <section className="sw-sec" style={{ paddingTop: 0 }}>
          <div className="sw-card ab-story ab-split">
            <div className="sw-head">
              <p className="sw-eyebrow">Our story</p>
              <h2 className="sw-h2">
                From a real problem <em>to a real platform.</em>
              </h2>
            </div>
            <div className="ab-prose">
              <p>
                Switch was founded in 2026 with a very real problem in mind — finding verified, trustworthy
                domestic and business staff in Gurgaon was unnecessarily complicated. Too many middlemen,
                too many delays, too little trust.
              </p>
              <p>
                We decided to change that. We built a simple, transparent platform where Switch Players are verified
                before they ever reach your door, where booking takes minutes not days, and where you only pay
                after the work is done.
              </p>
              <p>
                Today, with 20,000+ verified partners and a fast-growing customer base across Gurgaon —
                <strong> we are just getting started.</strong> Gurgaon is our home, and we are here to make yours run better.
              </p>
            </div>
          </div>
        </section>

        {/* CTA */}
        <CtaFeature
          title={
            <>
              Let&apos;s Switch — <em>to staff that shows up.</em>
            </>
          }
          sub="Whether you run a shop in DLF needing extra hands, a restaurant in Udyog Vihar needing waiters, or a warehouse needing a 7-day team — Switch has verified Switch Players ready for you."
          photos={['/sw-cook.jpg', '/sw-general-helper.jpg']}
        />
        <p className="ab-fine">
          <span>Verified staff. Transparent rates. Just Switch.</span>
          <Link to="/blog" className="sw-link">
            Read our guides <Icon name="arrow" />
          </Link>
        </p>
      </main>
      <Footer />
    </>
  )
}
