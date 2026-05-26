import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import './AboutPage.css'

const APP_URL = 'https://app.switchlocally.com/'

const WHAT_WE_DO = [
  {
    ico: '🏠',
    title: 'Home Services',
    desc: 'Verified home cooks, kitchen helpers, maids, caretakers and nannies — everything inside your home, handled by people you can trust.',
  },
  {
    ico: '💼',
    title: 'Business Services',
    desc: 'Trained security guards, drivers, bouncers, bartenders, waiters, promoters and general helpers for offices, events, restaurants and businesses of all sizes.',
  },
  {
    ico: '📍',
    title: 'All of Gurgaon',
    desc: 'Serving every major sector and locality across pincodes 122001, 122002, 122006, 122009, 122010, 122017, 122018 and 122022.',
  },
  {
    ico: '🛡️',
    title: 'Verified at Every Step',
    desc: 'Every worker on Switch is Aadhaar-verified, document-checked and personally interviewed before being assigned to you.',
  },
  {
    ico: '💳',
    title: 'Simple & Transparent',
    desc: 'Book in minutes on switchlocally.com or the Switch App. No advance payment — you only pay after the work is done.',
  },
  {
    ico: '⚡',
    title: 'On-Demand, Same-Day',
    desc: 'Most bookings are confirmed within hours. Get verified workers at your door the same day, across Gurgaon and Gurugram.',
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
        <title>About Switch — Gurgaon's Trusted Home & Business Staffing Platform</title>
        <meta name="description" content="Switch is Gurgaon's most trusted home and business staffing platform. Founded in 2026, we connect 500+ Aadhaar-verified workers with families and businesses across DLF, Sushant Lok, Palam Vihar, Udyog Vihar, Sohna Road and all pincodes 122001–122022. Book maids, cooks, caretakers, drivers, security guards, bouncers, bartenders and waiters in minutes." />
        <meta name="keywords" content="about Switch, trusted home staffing agency Gurgaon, verified manpower agency Gurgaon, verified domestic workers Gurgaon, Aadhaar-verified workers Gurgaon, hire domestic help Gurgaon, professional home staffing Gurgaon, on-demand home staff Gurgaon, switchlocally.com, Switch App" />
        <link rel="canonical" href="https://switchlocally.com/about" />
        <meta property="og:title" content="About Switch — Gurgaon's Trusted Home & Business Staffing Platform" />
        <meta property="og:description" content="Founded in 2026. 500+ verified partners. 1000+ bookings served. Verified maids, cooks, caretakers, drivers, security guards, bouncers and bartenders across Gurgaon." />
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
                Gurgaon's most trusted<br />
                <em>home &amp; business staffing</em><br />
                platform.
              </h1>
              <p className="ab-lead">
                Born in 2026 with one simple idea — finding the right worker should never be hard.
                Whether you need someone to cook your meals, clean your home, care for your loved ones,
                or manage security at your business, we are just one click away.
              </p>
              <div className="ab-hero-ctas">
                <a href={APP_URL} className="ab-cta-primary">Book a verified worker →</a>
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
                We are <strong>Switch</strong> — Gurgaon's most trusted and friendly home and business staffing platform.
                Born in 2026, we set out to fix one of the most frustrating problems in any household or business:
                <em> finding the right worker, when you need them, without the hassle.</em>
              </p>
              <p>
                Whether you need a verified maid in DLF Phase 3, a cook in Sushant Lok, an elderly caretaker
                in Palam Vihar, a security guard in Udyog Vihar, or a bartender for an event in Cyber City —
                Switch has someone ready for you. With <strong>500+ verified partners</strong> on our platform
                and a fast-growing community of happy customers across Gurgaon, Switch is fast becoming the go-to name
                for reliable domestic and business staffing across the city.
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
              <h2 className="ab-h2">Good help shouldn't be hard to find.</h2>
              <p className="ab-mission-text">
                Our mission is simple — to make sure every home and every business in Gurgaon has access to
                the right help, at the right time, without any hassle. We have built a platform where verified
                maids, cooks, kitchen helpers, caretakers, security guards, drivers, helpers, promoters, bouncers,
                bartenders and waiters are available to you at the click of a button —
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
              <h2 className="ab-h2">Six reasons families &amp; businesses<br />trust Switch.</h2>
              <p className="ab-sub">There are plenty of options out there — here's why thousands of homes and businesses in Gurgaon choose us.</p>
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
              <h2 className="ab-cta-h">Let's Switch — to better help.</h2>
              <p className="ab-cta-p">
                Whether you're a busy family in DLF Phase 3 looking for a reliable maid, a restaurant in Udyog Vihar
                needing a bartender, or a startup in Cyber City needing a security guard — Switch has someone ready for you.
              </p>
              <div className="ab-cta-btns">
                <a href={APP_URL} className="ab-cta-primary">Book a verified worker →</a>
                <Link to="/blog" className="ab-cta-secondary">Read our guides</Link>
              </div>
              <p className="ab-cta-fine">No advance. No hassle. Just Switch.</p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
