import { useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import './App.css'
import SeoPage from './pages/SeoPage.jsx'
import { SERVICE_LIST } from './data/seoData.js'

/* ─── DATA ────────────────────────────────────────── */
const ALL_ROLES_MARQUEE = [
  'Home Cleaning','Cook','Driver','Store Helper','Painter',
  'Carpenter','Electrician','Plumber','Delivery Worker','Factory / Warehouse','Nanny / Babysitter','Security Guard',
]

const ROLES = [
  { img: '/house-cleaner.jpg',   name: 'Home Cleaning',      slug: 'home-cleaning-gurgaon',      desc: 'Sweep, mop, dust — full home or specific rooms',       tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/cook-chef.jpg',       name: 'Cook',               slug: 'cook-gurgaon',               desc: 'Daily meals, tiffin prep, or catering support',        tags: ['4 hrs','8 hrs','2 days'] },
  { img: '/driver.jpg',          name: 'Driver',             slug: 'driver-gurgaon',             desc: 'Daily commute, outstation, or airport runs',           tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/store-helper.jpg',    name: 'Store Helper',       slug: 'store-helper-gurgaon',       desc: 'Stacking, billing, customer floor support',            tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/painter.jpg',         name: 'Painter',            slug: 'painter-gurgaon',            desc: 'Interior, exterior painting and touch-ups',            tags: ['8 hrs','2 days','7 days'] },
  { img: '/carpenter.jpg',       name: 'Carpenter',          slug: 'carpenter-gurgaon',          desc: 'Furniture assembly, repairs, custom woodwork',         tags: ['4 hrs','8 hrs','2 days'] },
  { img: '/electrician.jpg',     name: 'Electrician',        slug: 'electrician-gurgaon',        desc: 'Wiring, fixtures, fuse boxes, appliance installation', tags: ['4 hrs','8 hrs'] },
  { img: '/plumber.jpg',         name: 'Plumber',            slug: 'plumber-gurgaon',            desc: 'Pipe repairs, leaks, bathroom and kitchen fitting',    tags: ['4 hrs','8 hrs'] },
  { img: '/delivery-rider.jpg',  name: 'Delivery Worker',    slug: 'delivery-worker-gurgaon',    desc: 'Last-mile delivery, loading and unloading',            tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/warehouse-staff.jpg', name: 'Factory / Warehouse',slug: 'factory-warehouse-gurgaon',  desc: 'Sorting, packing, assembly line support',              tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/baby-care.jpg',       name: 'Nanny / Babysitter', slug: 'nanny-gurgaon',              desc: 'Childcare, school pickup, homework help',              tags: ['4 hrs','8 hrs','2 days'] },
  { img: '/security-guard.jpg',  name: 'Security Guard',     slug: 'security-guard-gurgaon',     desc: 'Gate duty, premises security, night patrol',           tags: ['12 hrs','2 days','7 days'] },
]

const REVIEWS = [
  { name: 'Kirti S.',   loc: 'Mumbai',     text: 'Found a reliable cook in minutes. Punctual, skilled, and the food was excellent every single day.' },
  { name: 'Neha P.',    loc: 'Pune',       text: 'Booked a driver for 7 days straight. Always professional, always on time. Will definitely rebook.' },
  { name: 'Pradnyesh', loc: 'Bangalore',  text: 'Needed 4 warehouse workers urgently. Got verified staff same-day. Absolute lifesaver for our business.' },
  { name: 'Ridhi S.',   loc: 'Delhi',      text: 'Hired a painter for 2 days. Clean work, no mess, finished ahead of schedule. Effortless experience.' },
  { name: 'Ritika M.',  loc: 'Hyderabad',  text: 'Plumber fixed our pipe leak in under 2 hours. Booked at 9 PM, arrived 8 AM sharp. Incredible service.' },
  { name: 'Sameer K.',  loc: 'Chennai',    text: 'Our store needed part-time help during Diwali. Switch sent 3 experienced hands within just a few hours.' },
  { name: 'Karishma',  loc: 'Ahmedabad',  text: 'Switch is our weekly go-to for home cleaning. Always trained, always polite, always thorough. Love it.' },
  { name: 'Rabia A.',   loc: 'Surat',      text: 'Got a nanny for 2 weeks. She was wonderful with my kids — completely reliable and trusted.' },
]

const FAQS = [
  { q: 'What types of workers can I book?',       a: 'Switch covers 12+ blue-collar categories — cooks, drivers, cleaners, electricians, plumbers, carpenters, security guards, factory workers, store helpers, nannies, painters, delivery workers, and more.' },
  { q: 'What booking durations are available?',   a: 'Book for 4 hours, 8 hours, 12 hours, 2 days, or up to 7 days. Mix and match based on your exact requirement.' },
  { q: 'Are all workers background verified?',    a: 'Yes. Every worker is Aadhaar-verified, background-checked, and skills-assessed before they are approved to take bookings on the platform.' },
  { q: 'How quickly can I get someone?',          a: 'Most bookings are confirmed within 6 hours. For urgent needs, same-day availability is shown in real time within the app.' },
  { q: 'Can I reschedule or cancel?',             a: 'Yes — cancel or reschedule at no charge up to 2 hours before the booking start time, directly from the app.' },
  { q: 'How does payment work?',                  a: 'Pay securely via UPI, cards, or wallets. You are only charged after the work is completed and confirmed by you.' },
]

/* ─── ICONS ───────────────────────────────────────── */
function IcoBolt() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor">
      <path d="M9 2L4 9h5l-2 5 7-7H9l2-5z"/>
    </svg>
  )
}
function IcoCal() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="12" height="11" rx="2"/>
      <line x1="5" y1="1.5" x2="5" y2="4.5"/>
      <line x1="11" y1="1.5" x2="11" y2="4.5"/>
      <line x1="2" y1="7" x2="14" y2="7"/>
    </svg>
  )
}
function IcoApple() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
    </svg>
  )
}
function IcoPlay() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
      <path d="M3.18 23.2c.3.17.64.26.99.26.52 0 1.03-.2 1.41-.58l14.02-8.1c.78-.45 1.25-1.27 1.25-2.17 0-.9-.47-1.72-1.25-2.17L5.58 2.34C5.2 1.96 4.69 1.76 4.17 1.76c-.35 0-.69.09-.99.26C2.47 2.47 2 3.25 2 4.17v15.66c0 .92.47 1.7 1.18 2.11z"/>
    </svg>
  )
}
function IcoStar() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14">
      <path fill="#f59e0b" d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
    </svg>
  )
}
function IcoCheck() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <polyline points="3 8.5 6.5 12 13 5"/>
    </svg>
  )
}
function IcoShield() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" width="15" height="15">
      <path d="M8 2L3 4v4c0 3 2.5 5.5 5 6.5C11 13.5 13 11 13 8V4L8 2z"/>
      <polyline points="5.5 8 7 9.5 10.5 6"/>
    </svg>
  )
}

function StarRow() {
  return <div className="rev-stars">{[0,1,2,3,4].map(i=><IcoStar key={i}/>)}</div>
}

/* ─── NAV ─────────────────────────────────────────── */
function Nav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <a href="/" className="nav-logo">
          <div className="nav-mark">S</div>
          <span className="nav-name">Switch</span>
        </a>
        <div className="nav-links">
          <a href="#roles" className="nav-link">Services</a>
          <a href="#how-it-works" className="nav-link">How it works</a>
          <a href="#reviews" className="nav-link">Reviews</a>
          <a href="#faq" className="nav-link">FAQ</a>
        </div>
        <a href="https://app.switchlocally.com/hire" className="nav-cta">Book Now</a>
      </div>
    </nav>
  )
}

/* ─── HERO ────────────────────────────────────────── */
function Hero() {
  const doubled = [...ALL_ROLES_MARQUEE, ...ALL_ROLES_MARQUEE]
  return (
    <section className="hero">
      {/* LEFT */}
      <div className="hero-l">
        <div className="hero-l-wrap">

          <div className="hero-live">
            <span className="hero-dot" />
            <span>Now live · Gurgaon</span>
          </div>

          <h1 className="hero-h1">
            The right<br />
            worker,<br />
            right when<br />
            <em>you need.</em>
          </h1>

          <p className="hero-lead">
            Hire verified blue-collar professionals in minutes. No agencies, no calls — just book and get it done.
          </p>

          <div className="hero-marquee-wrap">
            <div className="hero-marquee">
              {doubled.map((name, i) => (
                <span className="hero-marquee-pill" key={i}>{name}</span>
              ))}
            </div>
          </div>

          <div className="hero-ctas">
            <a href="https://app.switchlocally.com/hire" className="btn-book">
              <IcoBolt />
              <span>
                <span className="btn-main">Book Instant</span>
                <span className="btn-sub">Help in under 60 mins</span>
              </span>
            </a>
            <a href="https://app.switchlocally.com/hire" className="btn-schedule">
              <IcoCal />
              <span>
                <span className="btn-main">Schedule Later</span>
                <span className="btn-sub">Pick your date &amp; time</span>
              </span>
            </a>
          </div>

          <div className="hero-trust">
            <div className="trust-item"><IcoShield />Aadhaar Verified</div>
            <span className="trust-sep" />
            <div className="trust-item"><IcoStar />4.8 ★ Rating</div>
            <span className="trust-sep" />
            <div className="trust-item"><IcoCheck />On-time Guarantee</div>
          </div>

        </div>
      </div>

      {/* RIGHT */}
      <div className="hero-r">
        <img src="/hero-workers.png" alt="Switch verified professionals" />
        <div className="hero-r-fade" />
        <div className="hero-booking-card">
          <div className="hbc-head">
            <span className="hbc-dot" />
            <span className="hbc-status">Just Confirmed</span>
          </div>
          <div className="hbc-role">Home Cleaning · 8 hrs</div>
          <div className="hbc-info">Worker arriving tomorrow at 9:00 AM</div>
        </div>
      </div>

    </section>
  )
}

/* ─── STATS ───────────────────────────────────────── */
function Stats() {
  return (
    <div className="stats">
      <div className="stats-row">
        {[
          { num: '1,000+', lbl: 'Verified Users' },
          { num: '200+',   lbl: 'Jobs Completed' },
          { num: '4.8 ★',  lbl: 'Average Rating' },
          { num: '🏙',     lbl: 'Gurgaon' },
        ].map((s, i) => (
          <div className="s-cell" key={i}>
            <div className="s-num">{s.num}</div>
            <div className="s-lbl">{s.lbl}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── ROLES ───────────────────────────────────────── */
function Roles() {
  return (
    <section className="sec sec-alt sec-border-t" id="roles">
      <div className="w">
        <div className="sec-hd">
          <span className="tag">All categories</span>
          <h2 className="h2">Every blue-collar role,<br />one platform.</h2>
          <p className="lead">From a 4-hour cook to a 7-day warehouse team — book the right skill for exactly as long as you need it.</p>
        </div>
        <div className="roles-grid">
          {ROLES.map((r, i) => (
            <Link to={`/${r.slug}`} className="role" key={i}>
              <img src={r.img} alt={r.name} className="role-img" />
              <div className="role-body">
                <div className="r-name">{r.name}</div>
                <div className="r-desc">{r.desc}</div>
                <div className="r-tags">
                  {r.tags.map(t => <span className="r-tag" key={t}>{t}</span>)}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── HOW IT WORKS ────────────────────────────────── */
function HowItWorks() {
  const items = [
    { n:'1', title:'Choose the service',         desc:'Pick from 12+ verified blue-collar services — from home cleaning to security guards. Done in seconds.' },
    { n:'2', title:'Add details & select time',  desc:'Tell us what you need and pick a time that works for you. Done in under 2 minutes, no calls needed.' },
    { n:'3', title:'Confirm & relax',            desc:'We\'ll match you with a verified, nearby worker. Sit back and relax — they\'ll handle the rest.' },
  ]
  return (
    <section className="sec" id="how-it-works">
      <div className="w">
        <div className="sec-hd">
          <span className="tag">How it works</span>
          <h2 className="h2">Simple steps to get<br />the right worker.</h2>
          <p className="lead">Quick. Easy. Reliable. Get help in just a few taps.</p>
        </div>
        <img src="/how-it-works.png" alt="How Switch works" className="hiw-img" />
        <div className="steps">
          {items.map((s, i) => (
            <div className="step" key={i}>
              <div className="step-n">Step {s.n}</div>
              <div className="step-num">{s.n}</div>
              <div className="step-title">{s.title}</div>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── REVIEWS ─────────────────────────────────────── */
function Reviews() {
  const doubled = [...REVIEWS, ...REVIEWS]
  return (
    <section className="sec sec-alt sec-border-t" id="reviews">
      <div className="w">
        <div className="sec-hd">
          <span className="tag">Customer reviews</span>
          <h2 className="h2">Trusted by thousands<br />across India.</h2>
          <p className="lead">Real bookings, real workers, real results — every single day.</p>
        </div>
      </div>
      <div className="rev-outer">
        <div className="rev-track">
          {doubled.map((r, i) => (
            <div className="rev-card" key={i}>
              <StarRow />
              <p className="rev-text">"{r.text}"</p>
              <div className="rev-bot">
                <div className="rev-av">{r.name[0]}</div>
                <div>
                  <div className="rev-name">{r.name}</div>
                  <div className="rev-loc">{r.loc}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── FAQ ─────────────────────────────────────────── */
function FAQ() {
  const [open, setOpen] = useState(null)
  return (
    <section className="sec" id="faq">
      <div className="w">
        <div className="sec-hd">
          <span className="tag">FAQ</span>
          <h2 className="h2">Questions?<br />We have answers.</h2>
          <p className="lead">Everything you need to know before your first booking.</p>
        </div>
        <div className="faq-grid">
          {FAQS.map((f, i) => (
            <div className={`faq-item${open === i ? ' open' : ''}`} key={i}>
              <button className="faq-btn" onClick={() => setOpen(o => o === i ? null : i)}>
                <span className="faq-q">{f.q}</span>
                <span className="faq-tog">
                  <svg viewBox="0 0 12 12"><line x1="6" y1="1" x2="6" y2="11"/><line x1="1" y1="6" x2="11" y2="6"/></svg>
                </span>
              </button>
              <div className="faq-body">{f.a}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── CTA ─────────────────────────────────────────── */
function CTA() {
  return (
    <section className="cta-sec" id="download">
      <div className="cta-inner">
        <div>
          <span className="tag">Get the app</span>
          <h2 className="cta-h2">Book any worker,<br />anytime, anywhere.</h2>
          <p className="cta-p">12 job categories. Flexible slots from 4 hours to 7 days. Aadhaar-verified workers, guaranteed results.</p>
          <a href="mailto:hello@switchlocally.com" className="cta-mail">✉ hello@switchlocally.com</a>
          <div className="cta-btns">
            <a href="https://app.switchlocally.com/hire" className="btn-book">
              <IcoApple />
              <span>
                <span className="btn-sub" style={{opacity:0.55}}>Download on the</span>
                <span className="btn-main">App Store</span>
              </span>
            </a>
            <a href="https://app.switchlocally.com/hire" className="btn-book">
              <IcoPlay />
              <span>
                <span className="btn-sub" style={{opacity:0.55}}>Get it on</span>
                <span className="btn-main">Google Play</span>
              </span>
            </a>
          </div>
        </div>
        <div className="phones">
          <img src="/screen-2.png" alt="" className="ph ph-s" />
          <img src="/screen-home.png" alt="Switch app" className="ph ph-c" />
          <img src="/screen-3.png" alt="" className="ph ph-s" />
        </div>
      </div>
    </section>
  )
}

/* ─── HOME SEO HEAD ───────────────────────────────── */
function HomeHead() {
  const localBusiness = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    name: 'Switch',
    description: 'Book verified blue-collar workers in Gurgaon instantly. Home cleaners, cooks, drivers, electricians, plumbers, carpenters and more.',
    url: 'https://switchlocally.com',
    email: 'hello@switchlocally.com',
    areaServed: { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.8', bestRating: '5', reviewCount: '1000' },
    hasOfferCatalog: {
      '@type': 'OfferCatalog',
      name: 'Blue-Collar Services in Gurgaon',
      itemListElement: SERVICE_LIST.map(s => ({
        '@type': 'Offer',
        itemOffered: { '@type': 'Service', name: `${s.name} in Gurgaon`, url: `https://switchlocally.com/${s.slug}` },
      })),
    },
  }
  const websiteSchema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Switch',
    url: 'https://switchlocally.com',
  }
  return (
    <Helmet>
      <title>Book Verified Blue-Collar Workers in Gurgaon | Switch</title>
      <meta name="description" content="Switch is Gurgaon's fastest platform to hire verified home cleaners, cooks, drivers, electricians, plumbers, painters, carpenters and more. Aadhaar-verified workers. Book in 2 minutes. Pay only after work is done." />
      <link rel="canonical" href="https://switchlocally.com/" />
      <script type="application/ld+json">{JSON.stringify(localBusiness)}</script>
      <script type="application/ld+json">{JSON.stringify(websiteSchema)}</script>
    </Helmet>
  )
}

/* ─── ALL SERVICES DIRECTORY ──────────────────────── */
function AllServicesDirectory() {
  return (
    <section className="svc-dir">
      <div className="svc-dir-inner">
        <div className="svc-dir-hd">
          <h2 className="svc-dir-h2">Browse by service</h2>
          <p className="svc-dir-sub">Every worker type available in Gurgaon — pricing, hiring guides, and verified professionals.</p>
        </div>
        <div className="svc-dir-grid">
          {SERVICE_LIST.map(svc => (
            <div className="svc-dir-card" key={svc.id}>
              <Link to={`/${svc.slug}`} className="svc-dir-card-head">
                <span className="svc-dir-card-name">{svc.name}</span>
                <span className="svc-dir-card-arr">→</span>
              </Link>
              <div className="svc-dir-chips">
                {svc.pages.slice(1).map(p => (
                  <Link key={p.slug} to={`/${p.slug}`} className="svc-dir-chip">{p.label}</Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── FOOTER ──────────────────────────────────────── */
function Footer() {
  return (
    <footer className="footer">
      <div className="ft-grid">
        <div>
          <div className="ft-brand">
            <div className="nav-mark">S</div>
            <span className="ft-name">Switch</span>
          </div>
          <p className="ft-desc">India's trusted platform for booking verified blue-collar professionals — fast, flexible, and reliable.</p>
          <div className="ft-social">
            <a href="#" title="LinkedIn">in</a>
            <a href="#" title="X.com">𝕏</a>
            <a href="#" title="Instagram">ig</a>
          </div>
        </div>
        <div className="ft-col">
          <h5>Support</h5>
          <ul>
            <li><a href="#">Contact Us</a></li>
            <li><a href="#">Help Centre</a></li>
            <li><a href="#">Delete Account</a></li>
          </ul>
        </div>
        <div className="ft-col">
          <h5>Company</h5>
          <ul>
            <li><a href="mailto:careers@switchlocally.com">Careers</a></li>
            <li><a href="#">About Us</a></li>
            <li><a href="#">Become a Professional</a></li>
          </ul>
        </div>
        <div className="ft-col">
          <h5>Legal</h5>
          <ul>
            <li><a href="#">Terms &amp; Conditions</a></li>
            <li><a href="#">Privacy Policy</a></li>
            <li><a href="#">Cancellation Policy</a></li>
          </ul>
        </div>
      </div>
      <div className="ft-bot">
        <span className="ft-copy">© 2025 Switch. All rights reserved.</span>
        <span className="ft-copy">Made in India 🇮🇳</span>
      </div>
    </footer>
  )
}

/* ─── HOME ────────────────────────────────────────── */
function HomePage() {
  return (
    <>
      <HomeHead />
      <Nav />
      <Hero />
      <Stats />
      <Roles />
      <HowItWorks />
      <Reviews />
      <FAQ />
      <CTA />
      <AllServicesDirectory />
      <Footer />
    </>
  )
}

/* ─── APP ─────────────────────────────────────────── */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/:slug" element={<SeoPage />} />
    </Routes>
  )
}
