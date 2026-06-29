import { useState, useEffect } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import './App.css'
import SeoPage from './pages/SeoPage.jsx'
import PartnerPage from './pages/PartnerPage.jsx'
import AboutPage from './pages/AboutPage.jsx'
import BlogIndex from './pages/BlogIndex.jsx'
import BlogPost from './pages/BlogPost.jsx'
import AppPage from './pages/AppPage.jsx'
import { SERVICE_LIST } from './data/seoData.js'

/* ─── CONTACT ─────────────────────────────────────── */
const APP_URL = 'https://app.switchlocally.com'
const PLAY_URL = 'https://play.google.com/store/apps/details?id=com.switchlocally.employer'
const PHONE = '+918368828660'
const WA_MSG = encodeURIComponent("Hi Switch — I'd like to hire staff for my business in Gurgaon.")
const WHATSAPP_URL = `https://wa.me/${PHONE.replace('+','')}?text=${WA_MSG}`
const CALL_URL = `tel:${PHONE}`

/* ─── DATA ────────────────────────────────────────── */
const ALL_ROLES_MARQUEE = [
  'Store Helper','Security Guard','Picker / Packer','Driver','Delivery Rider','Cook / Chef',
  'Housekeeping','Caretaker','Painter','Electrician','Plumber','Carpenter',
]

// Branded "switch" service photos (sw-*.jpg) — the same set the Switch app
// displays on its service cards.
const ROLES = [
  { img: '/sw-general-helper.jpg', name: 'General / Store Helper', slug: 'store-helper-gurgaon',     desc: 'Billing support, stocking, loading & shop-floor help', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/sw-security-guard.jpg', name: 'Security Guard',         slug: 'security-guard-gurgaon',   desc: 'Gate duty, premises security & night patrol', tags: ['12 hrs','2 days','7 days'] },
  { img: '/sw-factory-helper.jpg', name: 'Picker / Packer',        slug: 'factory-warehouse-gurgaon', desc: 'Warehouse picking, packing, sorting & dispatch', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/sw-driver.jpg',         name: 'Driver',                 slug: 'driver-gurgaon',           desc: 'Commercial runs, deliveries & staff transport', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/delivery-rider.jpg',  name: 'Delivery Rider',         slug: 'delivery-worker-gurgaon',  desc: 'Last-mile delivery, loading & movers', tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/sw-cook.jpg',           name: 'Cook / Chef',            slug: 'cook-gurgaon',             desc: 'Kitchen production for cafés, messes & catering', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/sw-maid.jpg',           name: 'Housekeeping',           slug: 'home-cleaning-gurgaon',    desc: 'Daily upkeep for offices, shops & premises', tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/sw-caretaker.jpg',      name: 'Caretaker / Elder Care', slug: 'nanny-gurgaon',            desc: 'Baby care, elder care & home assistance', tags: ['4 hrs','8 hrs','2 days'] },
]

const INDUSTRIES = [
  { ico: '🛍️', name: 'Retail & Shops',         roles: 'Store helpers · Billing support · Security · Loaders' },
  { ico: '🍽️', name: 'Restaurants & Cafés',    roles: 'Waiters · Kitchen helpers · Cooks · Dishwashers' },
  { ico: '📦', name: 'Warehouses & Factories', roles: 'Packers · Loaders · Line workers · Helpers' },
  { ico: '🎉', name: 'Events & Banquets',      roles: 'Waiters · Bartenders · Bouncers · Promoters' },
  { ico: '🏢', name: 'Offices & Co-working',   roles: 'Housekeeping · Security · Pantry · Office boys' },
  { ico: '💈', name: 'Salons & Clinics',       roles: 'Front desk · Housekeeping · Helpers · Attendants' },
]

const REVIEWS = [
  { name: 'Pradnyesh', loc: 'Warehouse · Udyog Vihar', text: 'Needed 4 warehouse workers urgently. Got verified staff same-day. Absolute lifesaver for our dispatch team.' },
  { name: 'Sameer K.',  loc: 'Retail Store · DLF Phase 5', text: 'Our store needed extra hands during Diwali. Switch sent 3 experienced helpers within just a few hours.' },
  { name: 'Rohit M.',   loc: 'Restaurant · Sector 29',   text: 'We staff weekend banquets through Switch — waiters and a bartender, every time on time. Replacement was instant when one fell sick.' },
  { name: 'Neha P.',    loc: 'Logistics · Sector 52',     text: 'Booked drivers for 7 days straight. Always professional, always on time. Now our default for staffing.' },
  { name: 'Aman G.',    loc: 'Café · Golf Course Road',   text: 'Two kitchen helpers for a full week during our launch. Verified, skilled, and no agency drama.' },
  { name: 'Ritika M.',  loc: 'Event · Sector 23',         text: 'Hired waiters for a corporate event. Booked at 9 PM, reported 8 AM sharp. Incredible reliability.' },
  { name: 'Vivek S.',   loc: 'Office · Cyber City',       text: 'Daily housekeeping and a security guard for our office floor. Set up in a day, billing was clean.' },
  { name: 'Kirti S.',   loc: 'Home · DLF Phase 2',        text: 'Also used them for a home cook — punctual, skilled, excellent food every single day.' },
]

const FAQS = [
  { q: 'What kind of staff can I hire for my business?', a: 'Store and general helpers, security guards, factory and warehouse workers, waiters, bartenders, bouncers, promoters, drivers, cooks, kitchen helpers and housekeeping — for shops, restaurants, warehouses, offices, events and more.' },
  { q: 'Can I hire multiple workers or a full team?', a: 'Yes. Bulk hiring is one of our most common requests — 3, 5 or more workers, including full teams for 7-day blocks. WhatsApp us your requirement for a custom quote and a dedicated point of contact.' },
  { q: 'What if a worker doesn’t show up?', a: 'We back every booking with a replacement guarantee. If a worker is a no-show or not the right fit, we dispatch a replacement fast — usually within 24 hours — so your business stays covered.' },
  { q: 'How does pricing work for longer bookings?', a: 'You can hire by the hour (1–4 hrs), by the full day, or in 2-day and 7-day blocks. The longer the booking, the lower the per-worker rate. Talk to us on WhatsApp for exact rates for your business.' },
  { q: 'Are all workers verified?', a: 'Yes. Every worker is Aadhaar-verified, background-checked and skill-assessed before they’re approved on the platform. On arrival, OTP verification confirms the right person reached your site.' },
  { q: 'Do you provide GST invoices and how is payment handled?', a: 'No advance — you pay on arrival. Pay via UPI, cards or bank transfer, and we can provide proper invoices for your business records. Ask our team to set up a business account.' },
  { q: 'Can I try a worker before committing to a longer booking?', a: 'Yes. Start with a trial shift to see the quality before you scale to a full day, a 7-day team or an ongoing arrangement. If the worker isn’t the right fit, we replace them — no questions asked.' },
  { q: 'Which areas of Gurgaon do you cover?', a: 'All major sectors and localities — DLF, Sushant Lok, Palam Vihar, Udyog Vihar, Cyber City, Sohna Road, MG Road and Sectors 1–49 — across pincodes 122001 to 122022. Tell us your location and we’ll confirm availability.' },
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

function IcoPin() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" width="13" height="13">
      <path d="M8 1a4.5 4.5 0 014.5 4.5c0 3-4.5 9.5-4.5 9.5S3.5 8.5 3.5 5.5A4.5 4.5 0 018 1zm0 2.5a2 2 0 100 4 2 2 0 000-4z"/>
    </svg>
  )
}

function StarRow() {
  return <div className="rev-stars">{[0,1,2,3,4].map(i=><IcoStar key={i}/>)}</div>
}

/* ─── NAV ─────────────────────────────────────────── */
export function Nav() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])
  // lock body scroll while the mobile menu is open
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])
  const close = () => setMenuOpen(false)
  return (
    <nav className={`nav${scrolled || menuOpen ? ' nav--scrolled' : ''}${menuOpen ? ' nav--open' : ''}`}>
      <div className="nav-inner">
        <a href="/" className="nav-logo">
          <div className="nav-mark">S</div>
          <span className="nav-name">Switch</span>
        </a>
        <div className="nav-links">
          <a href="/#industries" className="nav-link">Industries</a>
          <div className="nav-dd">
            <a href="/#roles" className="nav-link nav-dd-trigger">Services <span className="nav-dd-caret">▾</span></a>
            <div className="nav-dd-menu">
              {SERVICE_LIST.map(svc => (
                <Link key={svc.id} to={`/${svc.slug}`} className="nav-dd-item">{svc.name}</Link>
              ))}
              <a href="/#roles" className="nav-dd-item nav-dd-item--all">View all staff →</a>
            </div>
          </div>
          <a href="/#why" className="nav-link">Why Us</a>
          <a href="/#how-it-works" className="nav-link">How It Works</a>
          <a href="/#pricing" className="nav-link">Pricing</a>
          <Link to="/app" className="nav-link">Get App</Link>
          <Link to="/about" className="nav-link">About</Link>
        </div>
        <div className="nav-actions">
          <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="nav-partner">💬 WhatsApp</a>
          <a href={APP_URL} className="nav-cta">Hire Staff</a>
          <button
            type="button"
            className={`nav-burger${menuOpen ? ' is-open' : ''}`}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(o => !o)}
          >
            <span /><span /><span />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <div className={`nav-mobile${menuOpen ? ' is-open' : ''}`}>
        <div className="nav-mobile-links">
          <a href="/#industries" className="nav-mobile-link" onClick={close}>Industries</a>
          <a href="/#roles" className="nav-mobile-link" onClick={close}>Services</a>
          <a href="/#why" className="nav-mobile-link" onClick={close}>Why Us</a>
          <a href="/#how-it-works" className="nav-mobile-link" onClick={close}>How It Works</a>
          <a href="/#pricing" className="nav-mobile-link" onClick={close}>Pricing</a>
          <Link to="/app" className="nav-mobile-link" onClick={close}>Get the App</Link>
          <Link to="/about" className="nav-mobile-link" onClick={close}>About</Link>
        </div>
        <div className="nav-mobile-actions">
          <a href={APP_URL} className="nav-mobile-cta" onClick={close}>Hire Staff Now</a>
          <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="nav-mobile-wa" onClick={close}>💬 Chat on WhatsApp</a>
        </div>
      </div>
      <button
        type="button"
        className={`nav-scrim${menuOpen ? ' is-open' : ''}`}
        aria-hidden={!menuOpen}
        tabIndex={-1}
        onClick={close}
      />
    </nav>
  )
}

/* ─── HERO ────────────────────────────────────────── */
function Hero() {
  const doubled = [...ALL_ROLES_MARQUEE, ...ALL_ROLES_MARQUEE]
  return (
    <section className="hero">
      <div className="hero-bg" aria-hidden="true">
        <div className="hero-grid" />
        <div className="hero-glow" />
      </div>
      {/* LEFT */}
      <div className="hero-l">
        <div className="hero-l-wrap">

          <div className="hero-live">
            <span className="hero-dot" />
            <span>Staffing Gurgaon businesses · Now live</span>
          </div>

          <h1 className="hero-h1">
            Staff your<br />
            business with<br />
            workers who<br />
            <em>show up.</em>
          </h1>

          <p className="hero-lead">
            Verified cooks, helpers, guards, waiters &amp; more for shops, restaurants, warehouses and offices across Gurgaon. Replacement guaranteed — no agency, no hassle.
          </p>

          <div className="hero-marquee-wrap">
            <div className="hero-marquee">
              {doubled.map((name, i) => (
                <span className="hero-marquee-pill" key={i}>{name}</span>
              ))}
            </div>
          </div>

          <div className="hero-ctas">
            <a href={APP_URL} className="btn-book">
              <IcoBolt />
              <span>
                <span className="btn-main">Hire Staff Now</span>
                <span className="btn-sub">Workers in as little as a day</span>
              </span>
            </a>
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="btn-schedule">
              <IcoCal />
              <span>
                <span className="btn-main">Talk to our team</span>
                <span className="btn-sub">WhatsApp for a quote</span>
              </span>
            </a>
          </div>

          <div className="hero-trust">
            <div className="trust-item"><IcoShield />Aadhaar Verified</div>
            <span className="trust-sep" />
            <div className="trust-item"><IcoCheck />Replacement Guarantee</div>
            <span className="trust-sep" />
            <div className="trust-item"><IcoStar />4.8 ★ Rating</div>
          </div>

        </div>
      </div>

      {/* RIGHT */}
      <div className="hero-r">
        <img
          src="/hero-workers.jpg"
          alt="Switch verified blue-collar professionals — cooks, drivers, cleaners, security guards in Gurgaon"
          width="1000"
          height="789"
          fetchpriority="high"
          decoding="async"
        />
        <div className="hero-r-fade" />
        <div className="hero-booking-card">
          <div className="hbc-head">
            <span className="hbc-dot" />
            <span className="hbc-status">Just Confirmed</span>
          </div>
          <div className="hbc-role">2 Store Helpers · 7 days</div>
          <div className="hbc-info">Reporting to shop tomorrow at 9:00 AM</div>
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
          { num: '500+', lbl: 'Verified Workers' },
          { num: '200+',   lbl: 'Businesses Served' },
          { num: '24h',  lbl: 'Replacement Time' },
        ].map((s, i) => (
          <div className="s-cell" key={i} data-anim style={{'--delay':`${i*90}ms`}}>
            <div className="s-num">{s.num}</div>
            <div className="s-lbl">{s.lbl}</div>
          </div>
        ))}
        <div className="s-cell s-cell--city" data-anim style={{'--delay':'270ms'}}>
          <div className="s-city-icon">
            <svg viewBox="0 0 40 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="1" y="14" width="12" height="21" rx="1.5" fill="url(#cg1)" opacity="0.9"/>
              <rect x="3" y="17" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="7" y="17" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="3" y="21" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="7" y="21" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="3" y="25" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="7" y="25" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="14" y="6" width="14" height="29" rx="1.5" fill="url(#cg2)"/>
              <rect x="17" y="10" width="2.5" height="2.5" rx="0.4" fill="white" opacity="0.55"/>
              <rect x="22" y="10" width="2.5" height="2.5" rx="0.4" fill="white" opacity="0.55"/>
              <rect x="17" y="15" width="2.5" height="2.5" rx="0.4" fill="white" opacity="0.55"/>
              <rect x="22" y="15" width="2.5" height="2.5" rx="0.4" fill="white" opacity="0.55"/>
              <rect x="17" y="20" width="2.5" height="2.5" rx="0.4" fill="white" opacity="0.55"/>
              <rect x="22" y="20" width="2.5" height="2.5" rx="0.4" fill="white" opacity="0.55"/>
              <rect x="19" y="26" width="4" height="9" rx="0.5" fill="white" opacity="0.2"/>
              <rect x="29" y="18" width="10" height="17" rx="1.5" fill="url(#cg1)" opacity="0.85"/>
              <rect x="31" y="21" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="35" y="21" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="31" y="25" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <rect x="35" y="25" width="2" height="2" rx="0.4" fill="white" opacity="0.5"/>
              <line x1="0" y1="35.5" x2="40" y2="35.5" stroke="white" strokeOpacity="0.15" strokeWidth="1"/>
              <defs>
                <linearGradient id="cg1" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
                  <stop offset="0%" stopColor="rgba(139,92,246,0.7)"/>
                  <stop offset="100%" stopColor="rgba(99,102,241,0.5)"/>
                </linearGradient>
                <linearGradient id="cg2" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
                  <stop offset="0%" stopColor="rgba(160,110,255,0.9)"/>
                  <stop offset="100%" stopColor="rgba(99,102,241,0.7)"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="s-city-name">Gurgaon</div>
          <div className="s-lbl">Live · Exclusively</div>
        </div>
      </div>
    </div>
  )
}

/* ─── INDUSTRIES ──────────────────────────────────── */
function Industries() {
  return (
    <section className="sec sec-border-t" id="industries">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">Built for business</span>
          <h2 className="h2">Staffing for every<br />kind of business.</h2>
          <p className="lead">Whatever you run, we have the verified hands to keep it running — from a single shift to a full team for 7 days.</p>
        </div>
        <div className="ind-grid" data-anim style={{'--delay':'80ms'}}>
          {INDUSTRIES.map((ind, i) => (
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ind-card" key={i} style={{'--delay':`${(i%3)*70}ms`}}>
              <div className="ind-ico">{ind.ico}</div>
              <div className="ind-body">
                <div className="ind-name">{ind.name}</div>
                <div className="ind-roles">{ind.roles}</div>
              </div>
              <span className="ind-arr">→</span>
            </a>
          ))}
        </div>
        <div className="ind-cta" data-anim style={{'--delay':'160ms'}}>
          <span>Don't see your business? We staff almost anything.</span>
          <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ind-cta-btn">💬 Tell us what you need</a>
        </div>
      </div>
    </section>
  )
}

/* ─── WHY US ──────────────────────────────────────── */
const WHY_US = [
  { ico: '🔁', title: 'Replacement Guarantee', desc: 'A no-show won’t stop your business. We dispatch a replacement fast — usually within 24 hours.' },
  { ico: '🆔', title: 'Aadhaar-Verified Staff', desc: 'Every worker is Aadhaar-verified, document-checked and interviewed before they reach your site.' },
  { ico: '⚡', title: 'Staff in a Day', desc: 'No agency runaround. Tell us your need and get matched with the right workers within hours.' },
  { ico: '👥', title: 'Bulk & Weekly Teams', desc: 'Need 3, 5 or a full team for 7 days? We deploy at scale with a dedicated point of contact.' },
  { ico: '💸', title: 'No Advance — Pay on Arrival', desc: 'No upfront payment. Clean invoices for your business records, pay as the work happens.' },
  { ico: '📞', title: '24/7 Support', desc: 'Our team is always available to find the right person and sort out any issue, fast.' },
]
function WhyUs() {
  return (
    <section className="sec sec-alt sec-border-t" id="why">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">Why us</span>
          <h2 className="h2">Why businesses<br />choose Switch.</h2>
          <p className="lead">Shops, restaurants, warehouses and offices across Gurgaon rely on us to stay staffed — here’s why.</p>
        </div>
        <div className="why-grid" data-anim style={{'--delay':'80ms'}}>
          {WHY_US.map((w, i) => (
            <div className="why-card" key={i} style={{'--delay':`${(i%3)*70}ms`}}>
              <div className="why-ico">{w.ico}</div>
              <h3 className="why-title">{w.title}</h3>
              <p className="why-desc">{w.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── ROLES ───────────────────────────────────────── */
function Roles() {
  return (
    <section className="sec sec-alt sec-border-t" id="roles">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">The workers</span>
          <h2 className="h2">Every role your<br />business runs on.</h2>
          <p className="lead">From a single store helper to a 7-day warehouse team — hire the right skill for exactly as long as you need it.</p>
        </div>
        <div className="roles-grid roles-grid--app">
          {ROLES.map((r, i) => {
            const inner = (
              <img
                src={r.img}
                alt={`Hire verified ${r.name.toLowerCase()} in Gurgaon — ${r.desc}`}
                className="role-app-img"
                width="350"
                height="374"
                loading="lazy"
                decoding="async"
              />
            )
            const style = {'--delay':`${(i%4)*65}ms`}
            return r.external ? (
              <a href={r.external} className="role-app" key={i} data-anim style={style}>{inner}</a>
            ) : (
              <Link to={`/${r.slug}`} className="role-app" key={i} data-anim style={style}>{inner}</Link>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* ─── EASY PROCESS ────────────────────────────────── */
function IllChoose() {
  return (
    <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id="ipg1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="rgba(160,140,255,0.9)"/>
          <stop offset="100%" stopColor="rgba(99,102,241,0.6)"/>
        </linearGradient>
      </defs>
      <rect x="14" y="16" width="92" height="72" rx="10" fill="rgba(99,102,241,0.08)" stroke="rgba(160,140,255,0.45)" strokeWidth="1.2"/>
      <rect x="22" y="26" width="22" height="22" rx="5" fill="url(#ipg1)"/>
      <rect x="49" y="26" width="22" height="22" rx="5" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
      <rect x="76" y="26" width="22" height="22" rx="5" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
      <rect x="22" y="54" width="22" height="22" rx="5" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
      <rect x="49" y="54" width="22" height="22" rx="5" fill="url(#ipg1)" opacity="0.55"/>
      <rect x="76" y="54" width="22" height="22" rx="5" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)"/>
      <circle cx="33" cy="37" r="3.4" fill="#fff" opacity="0.95"/>
      <path d="M28 39 c0-3.4 2.4-5.2 5-5.2 s5 1.8 5 5.2" stroke="#fff" strokeWidth="1.4" opacity="0.95" fill="none"/>
    </svg>
  )
}
function IllHours() {
  return (
    <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id="ipg2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(160,140,255,0.85)"/>
          <stop offset="100%" stopColor="rgba(99,102,241,0.55)"/>
        </linearGradient>
      </defs>
      <circle cx="60" cy="50" r="34" fill="rgba(99,102,241,0.08)" stroke="rgba(160,140,255,0.5)" strokeWidth="1.3"/>
      <circle cx="60" cy="50" r="28" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1"/>
      <path d="M60 22 A28 28 0 0 1 88 50" stroke="url(#ipg2)" strokeWidth="4" strokeLinecap="round" fill="none"/>
      <line x1="60" y1="50" x2="60" y2="30" stroke="#fff" strokeWidth="2.4" strokeLinecap="round"/>
      <line x1="60" y1="50" x2="76" y2="58" stroke="#fff" strokeWidth="2.4" strokeLinecap="round"/>
      <circle cx="60" cy="50" r="2.6" fill="#fff"/>
      <text x="60" y="13" textAnchor="middle" fontSize="8" fontWeight="700" fill="rgba(255,255,255,0.6)">12</text>
      <text x="103" y="53" textAnchor="middle" fontSize="8" fontWeight="700" fill="rgba(255,255,255,0.6)">3</text>
      <text x="60" y="93" textAnchor="middle" fontSize="8" fontWeight="700" fill="rgba(255,255,255,0.6)">6</text>
      <text x="17" y="53" textAnchor="middle" fontSize="8" fontWeight="700" fill="rgba(255,255,255,0.6)">9</text>
    </svg>
  )
}
function IllVerify() {
  return (
    <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id="ipg3" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="rgba(160,140,255,0.85)"/>
          <stop offset="100%" stopColor="rgba(99,102,241,0.55)"/>
        </linearGradient>
      </defs>
      <rect x="36" y="14" width="48" height="72" rx="10" fill="rgba(99,102,241,0.08)" stroke="rgba(160,140,255,0.5)" strokeWidth="1.3"/>
      <circle cx="60" cy="44" r="13" fill="rgba(255,255,255,0.08)" stroke="url(#ipg3)" strokeWidth="1.5"/>
      <circle cx="60" cy="40" r="5" fill="#fff" opacity="0.9"/>
      <path d="M50 54 c0-6 4-9 10-9 s10 3 10 9" stroke="#fff" strokeWidth="1.6" fill="none" opacity="0.9"/>
      <line x1="44" y1="22" x2="50" y2="22" stroke="url(#ipg3)" strokeWidth="2" strokeLinecap="round"/>
      <line x1="70" y1="22" x2="76" y2="22" stroke="url(#ipg3)" strokeWidth="2" strokeLinecap="round"/>
      <line x1="44" y1="78" x2="76" y2="78" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
      <rect x="44" y="64" width="32" height="8" rx="2" fill="rgba(99,102,241,0.2)" stroke="rgba(160,140,255,0.4)"/>
      <text x="60" y="70.5" textAnchor="middle" fontSize="7" fontWeight="800" fill="#fff" letterSpacing="1.5">4 2 8 1</text>
    </svg>
  )
}
function IllRelax() {
  return (
    <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id="ipg4" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(160,140,255,0.85)"/>
          <stop offset="100%" stopColor="rgba(99,102,241,0.55)"/>
        </linearGradient>
      </defs>
      <rect x="10" y="20" width="100" height="60" rx="9" fill="rgba(99,102,241,0.06)" stroke="rgba(160,140,255,0.45)" strokeWidth="1.2"/>
      <path d="M28 64 v-10 a6 6 0 0 1 6-6 h52 a6 6 0 0 1 6 6 v10" fill="url(#ipg4)"/>
      <rect x="22" y="60" width="76" height="14" rx="3" fill="url(#ipg4)" opacity="0.85"/>
      <rect x="22" y="60" width="76" height="14" rx="3" fill="none" stroke="rgba(255,255,255,0.18)"/>
      <rect x="22" y="73" width="6" height="6" rx="1" fill="rgba(255,255,255,0.4)"/>
      <rect x="92" y="73" width="6" height="6" rx="1" fill="rgba(255,255,255,0.4)"/>
      <rect x="34" y="50" width="14" height="10" rx="3" fill="rgba(255,255,255,0.85)"/>
      <rect x="52" y="50" width="14" height="10" rx="3" fill="rgba(255,255,255,0.85)"/>
      <rect x="70" y="50" width="14" height="10" rx="3" fill="rgba(255,255,255,0.85)"/>
      <circle cx="60" cy="32" r="4" fill="#fff"/>
      <path d="M52 32 q8 -10 16 0" stroke="rgba(255,255,255,0.5)" strokeWidth="1.2" fill="none"/>
    </svg>
  )
}

function HowItWorks() {
  const items = [
    { n:'01', title:'Tell us your requirement',     desc:'Pick the role and how many workers you need — for a few hours, a full shift, or up to 7 days. Bulk needs? Just WhatsApp us.', Ill: IllChoose },
    { n:'02', title:'We match verified staff',      desc:'We assign Aadhaar-verified, skill-checked workers suited to your business — usually within hours.', Ill: IllHours },
    { n:'03', title:'They report to your site',     desc:'OTP verification on arrival confirms the right person. No-show? A replacement is dispatched fast.', Ill: IllVerify },
    { n:'04', title:'Scale up or down anytime',     desc:'Need more hands for a sale or festival? Add staff in minutes. Pay only after the work is done.', Ill: IllRelax },
  ]
  return (
    <section className="sec" id="how-it-works">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">How it works</span>
          <h2 className="h2">Staff your business<br />in four steps.</h2>
          <p className="lead">From request to reporting — built to keep your business covered without the agency runaround.</p>
        </div>
        <div className="steps steps--4">
          {items.map((s, i) => (
            <div className="step step--ill" key={i} data-anim style={{'--delay':`${i*120}ms`}}>
              <div className="step-n">Step {s.n}</div>
              <div className="step-ill"><s.Ill /></div>
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
        <div className="sec-hd" data-anim>
          <span className="tag">Customer reviews</span>
          <h2 className="h2">Trusted by businesses<br />across Gurgaon.</h2>
          <p className="lead">Shops, restaurants, warehouses and offices — staffed and running, every single day.</p>
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
        <div className="sec-hd" data-anim>
          <span className="tag">FAQ</span>
          <h2 className="h2">Questions?<br />We have answers.</h2>
          <p className="lead">Everything you need to know before your first booking.</p>
        </div>
        <div className="faq-grid" data-anim style={{'--delay':'80ms'}}>
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
        <div data-anim>
          <span className="tag">Staff your business</span>
          <h2 className="cta-h2">Tell us what you<br />need. We'll staff it.</h2>
          <p className="cta-p">From one worker to a full team — verified, reliable, replacement-guaranteed. Message us on WhatsApp and we'll get back with availability and a quote.</p>
          <a href="mailto:hello@switchlocally.com" className="cta-mail">✉ hello@switchlocally.com · ☎ +91 83688 28660</a>
          <div className="cta-btns">
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="btn-book">
              <IcoBolt />
              <span>
                <span className="btn-sub" style={{opacity:0.55}}>Fastest way to start</span>
                <span className="btn-main">Hire on WhatsApp</span>
              </span>
            </a>
            <a href={CALL_URL} className="btn-schedule">
              <IcoCal />
              <span>
                <span className="btn-sub" style={{opacity:0.55}}>Prefer to talk?</span>
                <span className="btn-main">Call our team</span>
              </span>
            </a>
          </div>
          <div className="cta-applinks">
            <span className="cta-applinks-lbl">Or hire from the app:</span>
            <a href={PLAY_URL} target="_blank" rel="noopener noreferrer" className="cta-applink"><IcoPlay /> Google Play</a>
            <span className="cta-applink cta-applink--soon"><IcoApple /> App Store · Available Soon</span>
          </div>
        </div>
        <div className="phones" data-anim style={{'--delay':'180ms'}}>
          <img src="/screen-2.png"    alt="Switch app — service categories" className="ph ph-s ph-l" width="390" height="844" loading="lazy" decoding="async" />
          <img src="/screen-home.png" alt="Switch app — book verified workers in Gurgaon" className="ph ph-c" width="390" height="844" loading="lazy" decoding="async" />
          <img src="/screen-3.png"    alt="Switch app — verified worker profiles" className="ph ph-s ph-r" width="390" height="844" loading="lazy" decoding="async" />
        </div>
      </div>
    </section>
  )
}

/* ─── REQUEST STAFF FORM (lead capture) ───────────── */
const FORM_ROLES = [
  'Store / General Helper','Waiter','Kitchen Helper','Cook / Chef','Dishwasher',
  'Housekeeping','Security Guard','Picker / Packer','Loader','Driver','Delivery Rider',
  'Receptionist / Front Desk','Bartender','Bouncer','Promoter','Other / Multiple',
]

const encodeForm = (data) =>
  Object.keys(data).map(k => encodeURIComponent(k) + '=' + encodeURIComponent(data[k])).join('&')

function RequestStaff() {
  const [form, setForm] = useState({ business: '', phone: '', role: '', count: '', area: '', message: '' })
  const [status, setStatus] = useState('idle') // idle | sending | done | error
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()
    setStatus('sending')
    fetch('/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: encodeForm({ 'form-name': 'request-staff', 'bot-field': '', ...form }),
    })
      .then(() => setStatus('done'))
      .catch(() => setStatus('error'))
  }

  return (
    <section className="reqstaff-sec sec-border-t" id="request-staff">
      <div className="reqstaff-w" data-anim>
        <div className="reqstaff-copy">
          <span className="tag">Request staff</span>
          <h2 className="h2">Prefer not to chat?<br />Send your requirement.</h2>
          <p className="lead">Fill this and our team calls you back with availability and a quote — usually within the hour. Pay only after the worker reports. Replacement guaranteed.</p>
        </div>
        {status === 'done' ? (
          <div className="reqstaff-thanks">
            <span className="reqstaff-tick">✓</span>
            <h3>Got it{form.business ? `, ${form.business}` : ''}!</h3>
            <p>Our team will call you on <strong>{form.phone || 'your number'}</strong> shortly. For anything urgent, WhatsApp us now.</p>
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="btn-book reqstaff-wa"><IcoBolt /><span><span className="btn-main">WhatsApp us now</span></span></a>
          </div>
        ) : (
          <form className="reqstaff-form" name="request-staff" method="POST" data-netlify="true" netlify-honeypot="bot-field" onSubmit={submit}>
            <input type="hidden" name="form-name" value="request-staff" />
            <p hidden><label>Don't fill this: <input name="bot-field" onChange={set('bot-field')} /></label></p>
            <div className="reqstaff-row">
              <label>Business name<input type="text" name="business" required value={form.business} onChange={set('business')} placeholder="e.g. Yum Yum Cha" /></label>
              <label>Phone / WhatsApp<input type="tel" name="phone" required value={form.phone} onChange={set('phone')} placeholder="10-digit mobile" /></label>
            </div>
            <div className="reqstaff-row">
              <label>Role needed
                <select name="role" required value={form.role} onChange={set('role')}>
                  <option value="" disabled>Select a role</option>
                  {FORM_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </label>
              <label>How many?<input type="text" name="count" value={form.count} onChange={set('count')} placeholder="e.g. 2" /></label>
            </div>
            <label>Area / locality<input type="text" name="area" value={form.area} onChange={set('area')} placeholder="e.g. DLF Phase 2, Udyog Vihar" /></label>
            <label>Anything else? <span className="reqstaff-opt">(optional)</span><textarea name="message" rows="2" value={form.message} onChange={set('message')} placeholder="Shift timing, start date, etc." /></label>
            <button type="submit" className="reqstaff-submit" disabled={status === 'sending'}>
              {status === 'sending' ? 'Sending…' : 'Request staff →'}
            </button>
            {status === 'error' && <p className="reqstaff-err">Couldn't send — please WhatsApp or call us instead.</p>}
            <p className="reqstaff-fine">No advance payment. We call you back to confirm.</p>
          </form>
        )}
      </div>
    </section>
  )
}

/* ─── WORKER POSTER (supply side) ─────────────────── */
function WorkerPoster() {
  return (
    <section className="sec poster-sec sec-border-t" id="work-with-us">
      <div className="w poster-w">
        <div className="poster-copy" data-anim>
          <span className="tag">Looking for work?</span>
          <h2 className="h2">Your next job is<br /><em>ghar ke paas.</em></h2>
          <p className="lead">Verified employers, fast placement, zero cost. Get a blue-collar job near your home across Gurgaon — apply in a few taps.</p>
          <div className="poster-ctas">
            <Link to="/partner" className="price-cta price-cta--primary poster-cta"><IcoBolt />Become a Switch Partner</Link>
            <a href={PLAY_URL} target="_blank" rel="noopener noreferrer" className="cta-applink"><IcoPlay /> Get the app</a>
          </div>
        </div>
        <div className="poster-img-wrap" data-anim style={{'--delay':'120ms'}}>
          <img src="/instagram-poster.svg" alt="Switch — find blue-collar jobs near your home in Gurgaon, fast placement, free" className="poster-img" width="1080" height="1080" loading="lazy" decoding="async" />
        </div>
      </div>
    </section>
  )
}

/* ─── HOME SEO HEAD ───────────────────────────────── */
function HomeHead() {
  const allServices = [
    'Housekeeping','Maid','House Cleaning','Cook','Driver','Cleaning Staff',
    'Security Guard','Bouncer','Bartender','Waiter','Kitchen Helper','Promoter',
    'Factory Helper','General Helper','Caretaker','Nanny','Painter','Delivery Worker',
  ]
  const localBusiness = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    '@id': 'https://switchlocally.com/#business',
    name: 'Switch',
    alternateName: ['Switch Locally', 'Switch App'],
    description: 'Switch is Gurgaon\'s business staffing platform. Hire Aadhaar-verified, background-checked store and general helpers, security guards, factory and warehouse workers, waiters, bartenders, bouncers, promoters, drivers, cooks, kitchen helpers and housekeeping for shops, restaurants, warehouses, offices and events across all major areas and pincodes of Gurgaon. Bulk hiring, weekly teams, replacement guaranteed.',
    url: 'https://switchlocally.com',
    email: 'hello@switchlocally.com',
    telephone: '+91-8368828660',
    image: 'https://switchlocally.com/hero-workers.jpg',
    logo: 'https://switchlocally.com/hero-workers.jpg',
    priceRange: '₹149-₹199 per hour',
    address: {
      '@type': 'PostalAddress',
      streetAddress: '5th Floor, WeWork, Cyber Hub',
      addressLocality: 'Gurgaon',
      addressRegion: 'Haryana',
      postalCode: '122002',
      addressCountry: 'IN',
    },
    geo: { '@type': 'GeoCoordinates', latitude: 28.4595, longitude: 77.0266 },
    areaServed: [
      { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
      { '@type': 'City', name: 'Gurugram' },
      ...['DLF Phase 1','DLF Phase 3','DLF Phase 4','DLF Queens Enclave','Sushant Lok Phase 1','Sushant Lok Phase 2','Sushant Lok Phase 3','Palam Vihar','Udyog Vihar','Sohna Road','Cyber City','MG Road','Galleria Market','Sector 14','Sector 17','Sector 23','Sector 31','Sector 40','Sector 47','Sector 49','Chakkarpur','Sikanderpur','Nathupur','Greenwood City','Malibu Towne','Sun City'].map(n => ({ '@type': 'Place', name: `${n}, Gurgaon` })),
      ...['122001','122002','122006','122009','122010','122017','122018','122022'].map(p => ({ '@type': 'PostalAddress', postalCode: p, addressLocality: 'Gurgaon', addressRegion: 'Haryana', addressCountry: 'IN' })),
    ],
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.8', bestRating: '5', reviewCount: '500' },
    hasOfferCatalog: {
      '@type': 'OfferCatalog',
      name: 'Blue-Collar &amp; Housekeeping Services in Gurgaon',
      itemListElement: [
        ...SERVICE_LIST.map(s => ({
          '@type': 'Offer',
          itemOffered: { '@type': 'Service', name: `${s.name} in Gurgaon`, url: `https://switchlocally.com/${s.slug}` },
        })),
        ...allServices.map(name => ({
          '@type': 'Offer',
          itemOffered: { '@type': 'Service', name: `${name} in Gurgaon`, areaServed: 'Gurgaon' },
        })),
      ],
    },
    sameAs: ['https://www.linkedin.com/company/switchlocal', 'https://www.instagram.com/switchlocally/'],
  }
  const websiteSchema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Switch',
    url: 'https://switchlocally.com',
    potentialAction: {
      '@type': 'SearchAction',
      target: 'https://switchlocally.com/{search_term_string}-gurgaon',
      'query-input': 'required name=search_term_string',
    },
  }
  const orgSchema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Switch',
    url: 'https://switchlocally.com',
    logo: 'https://switchlocally.com/hero-workers.jpg',
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: '+91-8368828660',
      contactType: 'customer service',
      areaServed: 'IN',
      availableLanguage: ['en', 'hi'],
    },
    sameAs: ['https://www.linkedin.com/company/switchlocal', 'https://www.instagram.com/switchlocally/'],
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
    <Helmet>
      <title>Staffing for Business in Gurgaon — Hire Verified Workers | Switch</title>
      <meta name="description" content="Hire Aadhaar-verified staff for your Gurgaon business — helpers, guards, cooks, waiters &amp; more. Bulk &amp; weekly teams, replacement guaranteed, pay after work." />
      <meta name="keywords" content="staffing agency Gurgaon, manpower supply Gurgaon, hire staff for business Gurgaon, bulk hiring Gurgaon, contract staff Gurgaon, restaurant staff Gurgaon, warehouse workers Gurgaon, factory helper Gurgaon, store helper Gurgaon, retail staff Gurgaon, security guard Gurgaon, waiter for events Gurgaon, bartender hire Gurgaon, bouncer Gurgaon, housekeeping staff Gurgaon, office boy Gurgaon, on-demand blue-collar staffing Gurgaon, hire workers Udyog Vihar, Cyber City staffing, DLF business staff, Sohna Road staffing, switchlocally.com, Switch App, same-day worker hiring Gurgaon, replacement guarantee staffing Gurgaon, pay after work done Gurgaon, weekly staff hire Gurgaon" />
      <link rel="canonical" href="https://switchlocally.com/" />
      <script type="application/ld+json">{JSON.stringify(localBusiness)}</script>
      <script type="application/ld+json">{JSON.stringify(websiteSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(orgSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
    </Helmet>
  )
}

/* ─── ALL SERVICES DIRECTORY ──────────────────────── */
function AllServicesDirectory() {
  return (
    <section className="svc-dir">
      <div className="svc-dir-inner">
        <div className="svc-dir-hd" data-anim>
          <h2 className="svc-dir-h2">Browse by service</h2>
          <p className="svc-dir-sub">Every worker type available in Gurgaon — pricing, hiring guides, and verified professionals.</p>
        </div>
        <div className="svc-dir-grid" data-anim style={{'--delay':'100ms'}}>
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

/* ─── OFFERS (B2B) ────────────────────────────────── */
function Promos() {
  return (
    <section className="sec promo-sec sec-border-t" id="offers">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag promo-tag-hd">🔥 For new businesses</span>
          <h2 className="h2">Try Switch with<br /><em className="promo-em">zero risk.</em></h2>
          <p className="lead">Onboard your business with a trial shift, then scale to a full team. No long contracts, no agency lock-in.</p>
        </div>

        <div className="promo-grid" data-anim style={{'--delay':'80ms'}}>

          {/* Card 1 — Trial shift */}
          <div className="promo-card promo-card--featured">
            <div className="promo-ribbon">MOST POPULAR</div>
            <div className="promo-icon">🤝</div>
            <div className="promo-eyebrow">FIRST-TIME BUSINESSES</div>
            <h3 className="promo-title">Trial Shift</h3>
            <div className="promo-price-row">
              <div className="promo-price-block">
                <span className="promo-price promo-price--word">Try first</span>
              </div>
              <div className="promo-strike">
                <span className="promo-strike-save">Then decide</span>
              </div>
            </div>
            <ul className="promo-perks">
              <li><IcoCheck />One verified worker for a full shift</li>
              <li><IcoCheck />See the quality before you commit</li>
              <li><IcoCheck />Replacement if they're not a fit</li>
              <li><IcoCheck />No advance — pay on arrival</li>
            </ul>
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="promo-cta">
              <IcoBolt />Start a Trial Shift
            </a>
            <p className="promo-fine">*Talk to us on WhatsApp to set up your business account.</p>
          </div>

          {/* Card 2 — Bulk / weekly teams */}
          <div className="promo-card">
            <div className="promo-ribbon promo-ribbon--alt">BEST VALUE</div>
            <div className="promo-icon">👥</div>
            <div className="promo-eyebrow">TEAMS &amp; LONG DURATION</div>
            <h3 className="promo-title">Bulk &amp; Weekly Staffing</h3>
            <div className="promo-price-row">
              <div className="promo-price-block">
                <span className="promo-price promo-price--word">Custom</span>
              </div>
              <div className="promo-strike">
                <span className="promo-strike-save">Volume pricing</span>
              </div>
            </div>
            <ul className="promo-perks">
              <li><IcoCheck />3+ workers or 7-day teams</li>
              <li><IcoCheck />Lower per-worker rates at scale</li>
              <li><IcoCheck />Dedicated point of contact</li>
              <li><IcoCheck />Priority replacement &amp; coverage</li>
            </ul>
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="promo-cta promo-cta--alt">
              <IcoBolt />Get a Bulk Quote
            </a>
            <p className="promo-fine">*Pricing scales with team size and duration. Ask us.</p>
          </div>

        </div>

        <div className="promo-trust" data-anim style={{'--delay':'180ms'}}>
          <span><IcoShield /> Aadhaar-verified workers</span>
          <span className="trust-sep" />
          <span><IcoCheck /> Replacement guarantee</span>
          <span className="trust-sep" />
          <span><IcoCheck /> Pay on arrival</span>
        </div>
      </div>
    </section>
  )
}

/* ─── FOOTER ──────────────────────────────────────── */
/* ─── PRICING ─────────────────────────────────────── */
function Pricing() {
  return (
    <section className="sec sec-alt sec-border-t" id="pricing">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">Pricing · Flexible</span>
          <h2 className="h2">Hire by the hour,<br />day, or week.</h2>
          <p className="lead">Pay only for what you use. The longer you book, the lower the per-worker rate — built for how businesses actually staff.</p>
        </div>

        <div className="pricing-grid pricing-grid--3" data-anim style={{'--delay':'80ms'}}>

          <div className="price-card">
            <div className="price-tag-wrap">
              <span className="price-name price-name--top">Hourly</span>
            </div>
            <div className="price-name">Quick &amp; short tasks</div>
            <p className="price-desc">For a few hours of extra hands — rush hours, a quick cleanup, peak footfall.</p>
            <ul className="price-perks">
              <li><IcoCheck />1, 2 &amp; 4-hour slots</li>
              <li><IcoCheck />Aadhaar-verified workers</li>
              <li><IcoCheck />Same-day availability</li>
              <li><IcoCheck />Pay after the work is done</li>
            </ul>
            <a href={APP_URL} className="price-cta price-cta--secondary">
              Book Hourly
            </a>
          </div>

          <div className="price-card price-card--featured">
            <div className="price-badge">Most businesses</div>
            <div className="price-tag-wrap">
              <span className="price-name price-name--top">Full Day</span>
            </div>
            <div className="price-name">A full shift, covered</div>
            <p className="price-desc">One worker for a complete working day — the everyday way to staff a shop, kitchen or site.</p>
            <ul className="price-perks">
              <li><IcoCheck />Full 8–12 hour shifts</li>
              <li><IcoCheck />Cheaper per hour than hourly</li>
              <li><IcoCheck />Replacement guarantee</li>
              <li><IcoCheck />Same verified worker each day</li>
            </ul>
            <a href={APP_URL} className="price-cta price-cta--primary">
              <IcoBolt />Book a Full Day
            </a>
            <p className="price-note">Best balance of cost and reliability</p>
          </div>

          <div className="price-card">
            <div className="price-tag-wrap">
              <span className="price-name price-name--top">Weekly Team</span>
            </div>
            <div className="price-name">Up to 7 days · bulk</div>
            <p className="price-desc">Continuous cover for sales, festivals, leave gaps or a steady team — at our best per-worker rate.</p>
            <ul className="price-perks">
              <li><IcoCheck />2-day &amp; 7-day blocks</li>
              <li><IcoCheck />Lowest per-worker pricing</li>
              <li><IcoCheck />Priority replacement &amp; coverage</li>
              <li><IcoCheck />Dedicated point of contact</li>
            </ul>
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="price-cta price-cta--secondary">
              Get a Weekly Quote
            </a>
          </div>

        </div>

        <div className="pricing-note" data-anim style={{'--delay':'180ms'}}>
          Per-worker rates drop as you book longer. No platform fee, no advance — pay on arrival.
          <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="pricing-note-link"> Talk to us for exact rates →</a>
        </div>
      </div>
    </section>
  )
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="ft-grid">
        <div>
          <div className="ft-brand">
            <div className="nav-mark">S</div>
            <span className="ft-name">Switch</span>
          </div>
          <p className="ft-desc">Gurgaon's staffing partner for shops, restaurants, warehouses, offices and events — verified workers, fast, flexible and replacement-guaranteed.</p>
          <div className="ft-address">
            <IcoPin />
            <div>
              <div className="ft-addr-line">5th Floor, WeWork, Cyber Hub</div>
              <div className="ft-addr-line">Gurgaon, Haryana 122002</div>
              <a
                href="https://www.google.com/maps/search/WeWork+Cyber+Hub+Gurgaon"
                target="_blank"
                rel="noopener noreferrer"
                className="ft-map-link"
              >View on Google Maps →</a>
            </div>
          </div>
          <a href="tel:+918368828660" className="ft-phone">
            <span className="ft-phone-ico">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3.5C3 3 3.4 2.5 4 2.5h2c.5 0 .9.4 1 .9l.5 2.4c.1.4-.1.8-.4 1L5.7 8a10 10 0 0 0 4.4 4.4l1.1-1.4c.2-.3.7-.4 1-.3l2.4.5c.5.1.9.5.9 1v2c0 .6-.5 1-1 1A12 12 0 0 1 3 3.5Z"/>
              </svg>
            </span>
            <span>
              <span className="ft-phone-lbl">Call us</span>
              <span className="ft-phone-num">+91 83688 28660</span>
            </span>
          </a>
          <div className="ft-social">
            <a href="https://www.linkedin.com/company/switchlocal" target="_blank" rel="noopener noreferrer" title="Switch on LinkedIn">in</a>
            <a href="https://www.instagram.com/switchlocally/" target="_blank" rel="noopener noreferrer" title="Switch on Instagram">ig</a>
          </div>
        </div>
        <div className="ft-col">
          <h3 className="ft-col-title">For Business</h3>
          <ul>
            <li><a href="/#industries">Industries</a></li>
            <li><a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer">Bulk Hiring</a></li>
            <li><a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer">Request Staff</a></li>
            <li><a href={CALL_URL}>Contact Sales</a></li>
          </ul>
        </div>
        <div className="ft-col">
          <h3 className="ft-col-title">Company</h3>
          <ul>
            <li><Link to="/about">About Us</Link></li>
            <li><Link to="/blog">Blog</Link></li>
            <li><a href="mailto:careers@switchlocally.com">Careers</a></li>
            <li><Link to="/partner">Become a Professional</Link></li>
          </ul>
        </div>
        <div className="ft-col">
          <h3 className="ft-col-title">Legal</h3>
          <ul>
            <li><a href="#">Terms &amp; Conditions</a></li>
            <li><a href="#">Privacy Policy</a></li>
            <li><a href="#">Cancellation Policy</a></li>
          </ul>
        </div>
      </div>
      <div className="ft-bot">
        <span className="ft-copy">© 2026 Switch. All rights reserved.</span>
        <span className="ft-copy">Made in India 🇮🇳</span>
      </div>
      <a
        href={APP_URL}
        className="ft-banner"
        aria-label="Switch — India's first on-demand staffing platform. Get the app."
      >
        <img
          src="/switch-banner.jpg"
          alt="Switch — India's first on-demand staffing platform. Instant staffing, verified professionals, trusted by 1000+ businesses, 4.8 rating from 10,000+ happy customers."
          loading="lazy"
          width="1600"
          height="879"
        />
      </a>
    </footer>
  )
}

/* ─── HOME ────────────────────────────────────────── */
function HomePage() {
  useEffect(() => {
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('anim-in'); obs.unobserve(e.target) }
      }),
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    )
    document.querySelectorAll('[data-anim]').forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])
  return (
    <>
      <HomeHead />
      <Nav />
      <main>
        <Hero />
        <Stats />
        <Industries />
        <Roles />
        <WhyUs />
        <HowItWorks />
        <Promos />
        <Pricing />
        <Reviews />
        <FAQ />
        <CTA />
        <RequestStaff />
        <WorkerPoster />
        <AllServicesDirectory />
      </main>
      <Footer />
    </>
  )
}

/* ─── APP ─────────────────────────────────────────── */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/partner" element={<PartnerPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/blog" element={<BlogIndex />} />
      <Route path="/blog/:slug" element={<BlogPost />} />
      <Route path="/app" element={<AppPage />} />
      <Route path="/:slug" element={<SeoPage />} />
    </Routes>
  )
}
