import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import './AboutPage.css'

const APP_URL = 'https://app.switchlocally.com/'
const PHONE = '+918368828660'
const WA_MSG = encodeURIComponent("Hi Switch — I'd like to hire staff for my business in Gurgaon.")
const WHATSAPP_URL = `https://wa.me/${PHONE.replace('+','')}?text=${WA_MSG}`

const WHAT_WE_DO = [
  {
    ico: '💼',
    title: 'Business Staffing',
    desc: 'Store helpers, security guards, factory & warehouse workers, waiters, bartenders, bouncers, cooks and housekeeping — for shops, restaurants, warehouses, offices and events of every size.',
  },
  {
    ico: '👥',
    title: 'Bulk & Weekly Teams',
    desc: 'Need 3, 5 or a full team for 7 days straight? We deploy verified workers at scale, with a dedicated point of contact and priority coverage.',
  },
  {
    ico: '🔁',
    title: 'Replacement Guarantee',
    desc: 'A no-show shouldn’t stop your business. If a worker doesn’t turn up or isn’t the right fit, we dispatch a replacement fast — usually within 24 hours.',
  },
  {
    ico: '🛡️',
    title: 'Verified at Every Step',
    desc: 'Every worker on Switch is Aadhaar-verified, document-checked and personally interviewed before being assigned to your site.',
  },
  {
    ico: '💳',
    title: 'Simple & Transparent',
    desc: 'Hire in minutes on WhatsApp, switchlocally.com or the Switch App. No advance — you pay on arrival, with proper invoices for your records.',
  },
  {
    ico: '🏠',
    title: 'Home Services Too',
    desc: 'Beyond business, we also place trusted cooks, maids, caretakers and nannies for your home — the same verification, the same reliability.',
  },
]

const WHY_SWITCH = [
  {
    ico: '🧩',
    title: 'One Platform, Every Service',
    desc: 'From domestic help to business staffing — we do it all. No need to call five different agencies.',
  },
  {
    ico: '🆔',
    title: 'Aadhaar-Verified Workers',
    desc: 'Every worker on our platform is Aadhaar-verified and background-checked. Your safety is not negotiable.',
  },
  {
    ico: '⚡',
    title: 'Workers at a Click',
    desc: 'No long waits, no endless back-and-forth. Book a verified worker in minutes on switchlocally.com or the Switch App.',
  },
  {
    ico: '💸',
    title: 'Pay After Work is Done',
    desc: 'We never ask for advance payments. You pay only after you are satisfied with the service.',
  },
  {
    ico: '🔁',
    title: 'Replacement Guarantee',
    desc: 'Not happy with the assigned worker? We will replace them — fast, no questions asked.',
  },
  {
    ico: '📞',
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

const STATS = [
  { num: '500+', lbl: 'Verified Partners' },
  { num: '1000+', lbl: 'Bookings Served' },
  { num: '12+', lbl: 'Service Categories' },
  { num: '4.8 ★', lbl: 'Average Rating' },
]

export default function AboutPage() {
  useEffect(() => {
    window.scrollTo(0, 0)
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('anim-in'); obs.unobserve(e.target) }
      }),
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    )
    document.querySelectorAll('[data-anim]').forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  const aboutSchema = {
    '@context': 'https://schema.org',
    '@type': 'AboutPage',
    name: 'About Switch — Gurgaon\'s Trusted Home & Business Staffing Platform',
    url: 'https://switchlocally.com/about',
    description: 'Switch is Gurgaon\'s most trusted home and business staffing platform. Founded in 2026, we connect families and businesses across Gurgaon with Aadhaar-verified, background-checked domestic workers and business staff.',
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
        <meta name="description" content="Switch is Gurgaon's business staffing platform. Founded in 2026, we connect 500+ Aadhaar-verified workers with shops, restaurants, warehouses, offices and events across DLF, Udyog Vihar, Cyber City, Sohna Road and all pincodes 122001–122022. Hire store helpers, guards, waiters, cooks, housekeeping — bulk and weekly teams, replacement guaranteed." />
        <meta name="keywords" content="about Switch, staffing agency Gurgaon, manpower supply Gurgaon, verified workers Gurgaon, hire staff for business Gurgaon, bulk hiring Gurgaon, contract staff Gurgaon, restaurant staff Gurgaon, warehouse workers Gurgaon, store helper Gurgaon, on-demand staffing Gurgaon, switchlocally.com, Switch App" />
        <link rel="canonical" href="https://switchlocally.com/about" />
        <meta property="og:title" content="About Switch — Gurgaon's Business Staffing Platform" />
        <meta property="og:description" content="Founded in 2026. 500+ verified workers. Staffing shops, restaurants, warehouses, offices and events across Gurgaon — store helpers, guards, waiters, cooks, housekeeping. Bulk & weekly teams." />
        <meta property="og:url" content="https://switchlocally.com/about" />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <script type="application/ld+json">{JSON.stringify(aboutSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
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
              <span className="ab-tag">About Switch</span>
              <h1 className="ab-h1">
                Gurgaon's staffing<br />
                partner for <em>shops,<br />
                restaurants &amp; offices.</em>
              </h1>
              <p className="ab-lead">
                Born in 2026 with one simple idea — staffing your business should never be hard.
                Whether you run a shop, a kitchen, a warehouse or an event, Switch puts verified,
                reliable workers on your floor — for a shift, a day, or a full week.
              </p>
              <div className="ab-hero-ctas">
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ab-cta-primary">Hire staff for your business →</a>
                <Link to="/partner" className="ab-cta-secondary">Become a Partner</Link>
              </div>
              <div className="ab-stats">
                {STATS.map((s, i) => (
                  <div className="ab-stat" key={i}>
                    <div className="ab-stat-num">{s.num}</div>
                    <div className="ab-stat-lbl">{s.lbl}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Who We Are */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Who we are</span>
              <h2 className="ab-h2">Built for Gurgaon.<br />Trusted by thousands.</h2>
            </div>
            <div className="ab-text" data-anim style={{'--delay':'80ms'}}>
              <p>
                We are <strong>Switch</strong> — Gurgaon's business staffing platform.
                Born in 2026, we set out to fix one of the most frustrating problems any business owner faces:
                <em> finding reliable workers who actually show up, without the agency runaround.</em>
              </p>
              <p>
                Whether you need store helpers for a shop in DLF, packers for a warehouse in Udyog Vihar,
                waiters and a bartender for an event in Cyber City, or a 7-day team during a sale —
                Switch has verified workers ready for you. With <strong>500+ verified workers</strong> on our platform
                and a fast-growing base of businesses across Gurgaon, Switch is becoming the go-to name
                for dependable staffing across the city.
              </p>
            </div>
          </div>
        </section>

        {/* What We Do */}
        <section className="ab-sec ab-sec-alt">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">What we do</span>
              <h2 className="ab-h2">Every worker. One platform.</h2>
              <p className="ab-sub">Running a home or a business is not easy — and finding the right people makes all the difference. At Switch, we bring everything under one roof.</p>
            </div>
            <div className="ab-grid">
              {WHAT_WE_DO.map((w, i) => (
                <div className="ab-card" key={i} data-anim style={{'--delay':`${(i%3)*80}ms`}}>
                  <div className="ab-card-ico">{w.ico}</div>
                  <h3 className="ab-card-title">{w.title}</h3>
                  <p className="ab-card-desc">{w.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Mission */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-mission" data-anim>
              <span className="ab-tag">Our mission</span>
              <h2 className="ab-h2">Good staff shouldn't be hard to find.</h2>
              <p className="ab-mission-text">
                Our mission is simple — to make sure every business in Gurgaon can staff up at the right time,
                without the hassle. We have built a platform where verified store helpers, security guards,
                factory and warehouse workers, waiters, bartenders, bouncers, cooks, drivers and housekeeping
                are available at the click of a button —
                <strong> background-checked, Aadhaar-verified, and ready to work.</strong>
              </p>
            </div>
          </div>
        </section>

        {/* Why Switch */}
        <section className="ab-sec ab-sec-alt">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Why Switch</span>
              <h2 className="ab-h2">Six reasons businesses<br />trust Switch.</h2>
              <p className="ab-sub">There are plenty of options out there — here's why shops, restaurants, warehouses and offices across Gurgaon choose us.</p>
            </div>
            <div className="ab-grid">
              {WHY_SWITCH.map((w, i) => (
                <div className="ab-card ab-card--why" key={i} data-anim style={{'--delay':`${(i%3)*80}ms`}}>
                  <div className="ab-card-ico">{w.ico}</div>
                  <h3 className="ab-card-title">{w.title}</h3>
                  <p className="ab-card-desc">{w.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Where We Serve */}
        <section className="ab-sec">
          <div className="ab-w">
            <div className="ab-sec-hd" data-anim>
              <span className="ab-tag">Where we serve</span>
              <h2 className="ab-h2">Across every corner of Gurgaon.</h2>
              <p className="ab-sub">From DLF Cyber City to Sohna Road — Switch is already right around the corner.</p>
            </div>
            <div className="ab-areas" data-anim style={{'--delay':'80ms'}}>
              {AREAS.map(a => <span className="ab-area-pill" key={a}>{a}</span>)}
            </div>
            <div className="ab-pin-block" data-anim style={{'--delay':'160ms'}}>
              <div className="ab-pin-label">All pincodes:</div>
              <div className="ab-pins">
                {PINCODES.map(p => <span className="ab-pin" key={p}>{p}</span>)}
              </div>
            </div>
          </div>
        </section>

        {/* Story */}
        <section className="ab-sec ab-sec-alt">
          <div className="ab-w">
            <div className="ab-story" data-anim>
              <span className="ab-tag">Our story</span>
              <h2 className="ab-h2">From a real problem to a real platform.</h2>
              <p>
                Switch was founded in 2026 with a very real problem in mind — finding verified, trustworthy
                domestic and business staff in Gurgaon was unnecessarily complicated. Too many middlemen,
                too many delays, too little trust.
              </p>
              <p>
                We decided to change that. We built a simple, transparent platform where workers are verified
                before they ever reach your door, where booking takes minutes not days, and where you only pay
                after the work is done.
              </p>
              <p>
                Today, with 500+ verified partners and a fast-growing customer base across Gurgaon —
                <strong> we are just getting started.</strong> Gurgaon is our home, and we are here to make yours run better.
              </p>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="ab-cta-sec">
          <div className="ab-w">
            <div className="ab-cta" data-anim>
              <h2 className="ab-cta-h">Let's Switch — to staff that shows up.</h2>
              <p className="ab-cta-p">
                Whether you run a shop in DLF needing extra hands, a restaurant in Udyog Vihar needing waiters,
                or a warehouse needing a 7-day team — Switch has verified workers ready for you.
              </p>
              <div className="ab-cta-btns">
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ab-cta-primary">Hire staff for your business →</a>
                <Link to="/blog" className="ab-cta-secondary">Read our guides</Link>
              </div>
              <p className="ab-cta-fine">No advance. Pay on arrival. Just Switch.</p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
