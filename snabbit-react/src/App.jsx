import { useState, useEffect } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import './App.css'
import SeoPage from './pages/SeoPage.jsx'
import PartnerPage from './pages/PartnerPage.jsx'
import { SERVICE_LIST } from './data/seoData.js'

/* ─── DATA ────────────────────────────────────────── */
const ALL_ROLES_MARQUEE = [
  'Cook','Cleaning Staff','Driver','Security Guard','Factory Helper',
  'General Helper','Caretaker','Kitchen Helper','Promoter','Bouncer','Bartender','Waiter',
]

const ROLES = [
  { img: '/cook-new.jpg',           name: 'Cook',           slug: 'cook-gurgaon',           desc: 'Daily meals, tiffin prep, or catering support',     tags: ['4 hrs','8 hrs','2 days'] },
  { img: '/cleaning-staff.jpg',     name: 'Cleaning Staff', slug: 'home-cleaning-gurgaon',  desc: 'Sweep, mop, dust — full home or specific rooms',    tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/driver-new.jpg',         name: 'Driver',         slug: 'driver-gurgaon',         desc: 'Daily commute, outstation, or airport runs',        tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/security-guard-new.jpg', name: 'Security Guard', slug: 'security-guard-gurgaon', desc: 'Gate duty, premises security, night patrol',        tags: ['12 hrs','2 days','7 days'] },
  { img: '/factory-helper.jpg',     name: 'Factory Helper', slug: 'factory-warehouse-gurgaon', desc: 'Sorting, packing, assembly line support',         tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/general-helper.jpg',     name: 'General Helper', slug: 'store-helper-gurgaon',   desc: 'Picking, packing, loading and organizing',          tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/caretaker.jpg',          name: 'Caretaker',      slug: 'nanny-gurgaon',          desc: 'Childcare, elderly care, complete peace of mind',   tags: ['4 hrs','8 hrs','2 days'] },
  { img: '/kitchen-helper.jpg',     name: 'Kitchen Helper', external: 'https://app.switchlocally.com/employer', desc: 'Kitchen prep, chopping, cleaning support', tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/promoter.jpg',           name: 'Promoter',       external: 'https://app.switchlocally.com/employer', desc: 'Engage customers and boost brand sales',   tags: ['4 hrs','8 hrs','2 days'] },
  { img: '/bouncer.jpg',            name: 'Bouncer',        external: 'https://app.switchlocally.com/employer', desc: 'Entry management and secure environments', tags: ['8 hrs','12 hrs','7 days'] },
  { img: '/bartender.jpg',          name: 'Bartender',      external: 'https://app.switchlocally.com/employer', desc: 'Crafting drinks for events and venues',    tags: ['4 hrs','8 hrs','12 hrs'] },
  { img: '/waiter.jpg',             name: 'Waiter',         external: 'https://app.switchlocally.com/employer', desc: 'Table service for parties, dine-in, events', tags: ['4 hrs','8 hrs','12 hrs'] },
]

const REVIEWS = [
  { name: 'Kirti S.',   loc: 'DLF Phase 2',     text: 'Found a reliable cook in minutes. Punctual, skilled, and the food was excellent every single day.' },
  { name: 'Neha P.',    loc: 'Sector 52',        text: 'Booked a driver for 7 days straight. Always professional, always on time. Will definitely rebook.' },
  { name: 'Pradnyesh', loc: 'Udyog Vihar',      text: 'Needed 4 warehouse workers urgently. Got verified staff same-day. Absolute lifesaver for our business.' },
  { name: 'Ridhi S.',   loc: 'Golf Course Road', text: 'Hired a painter for 2 days. Clean work, no mess, finished ahead of schedule. Effortless experience.' },
  { name: 'Ritika M.',  loc: 'Sector 23',        text: 'Cook prepared amazing meals for our family event. Booked at 9 PM, arrived 8 AM sharp. Incredible service.' },
  { name: 'Sameer K.',  loc: 'DLF Phase 5',      text: 'Our store needed part-time help during Diwali. Switch sent 3 experienced hands within just a few hours.' },
  { name: 'Karishma',  loc: 'Sikanderpur',      text: 'Switch is our weekly go-to for home cleaning. Always trained, always polite, always thorough. Love it.' },
  { name: 'Rabia A.',   loc: 'Sector 45',        text: 'Got a nanny for 2 weeks. She was wonderful with my kids — completely reliable and trusted.' },
]

const FAQS = [
  { q: 'What types of workers can I book?',       a: 'Switch covers multiple blue-collar categories — cooks, drivers, cleaners, security guards, factory workers, store helpers, nannies, painters, delivery workers, and more.' },
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
function Nav() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])
  return (
    <nav className={`nav${scrolled ? ' nav--scrolled' : ''}`}>
      <div className="nav-inner">
        <a href="/" className="nav-logo">
          <div className="nav-mark">S</div>
          <span className="nav-name">Switch</span>
        </a>
        <div className="nav-links">
          <a href="#roles" className="nav-link">Services</a>
          <a href="#how-it-works" className="nav-link">How it works</a>
          <a href="#pricing" className="nav-link">Pricing</a>
          <a href="#reviews" className="nav-link">Reviews</a>
          <a href="#faq" className="nav-link">FAQ</a>
        </div>
        <div className="nav-actions">
          <Link to="/partner" className="nav-partner">Become Switch Partner</Link>
          <a href="https://app.switchlocally.com/employer" className="nav-cta">Book Now</a>
        </div>
      </div>
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
            <a href="https://app.switchlocally.com/employer" className="btn-book">
              <IcoBolt />
              <span>
                <span className="btn-main">Book Instant</span>
                <span className="btn-sub">Help in under 60 mins</span>
              </span>
            </a>
            <a href="https://app.switchlocally.com/employer" className="btn-schedule">
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
        <img
          src="/hero-workers.jpg"
          alt="Switch verified blue-collar professionals — cooks, drivers, cleaners, security guards in Gurgaon"
          width="1000"
          height="650"
          fetchpriority="high"
          decoding="async"
        />
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

/* ─── ROLES ───────────────────────────────────────── */
function Roles() {
  return (
    <section className="sec sec-alt sec-border-t" id="roles">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">All categories</span>
          <h2 className="h2">Every blue-collar role,<br />one platform.</h2>
          <p className="lead">From a 4-hour cook to a 7-day warehouse team — book the right skill for exactly as long as you need it.</p>
        </div>
        <div className="roles-grid">
          {ROLES.map((r, i) => {
            const inner = (
              <>
                <img
                  src={r.img}
                  alt={`Hire verified ${r.name.toLowerCase()} in Gurgaon — ${r.desc}`}
                  className="role-img"
                  width="720"
                  height="720"
                  loading="lazy"
                  decoding="async"
                />
                <div className="role-body">
                  <div className="r-name">{r.name}</div>
                  <div className="r-desc">{r.desc}</div>
                  <div className="r-tags">
                    {r.tags.map(t => <span className="r-tag" key={t}>{t}</span>)}
                  </div>
                </div>
              </>
            )
            const style = {'--delay':`${(i%4)*65}ms`}
            return r.external ? (
              <a href={r.external} className="role" key={i} data-anim style={style}>{inner}</a>
            ) : (
              <Link to={`/${r.slug}`} className="role" key={i} data-anim style={style}>{inner}</Link>
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
    { n:'01', title:'Choose the service',           desc:'Easily book through our user-friendly platform. Pick from 12+ verified blue-collar services — done in seconds.', Ill: IllChoose },
    { n:'02', title:'Choose the no. of hours',      desc:'Select the perfect slot — 4 hrs, 8 hrs, or up to 7 days — and let our expert take care of the rest.', Ill: IllHours },
    { n:'03', title:'Verify expert at your doorstep', desc:'A fast face scan and OTP verification ensure you receive trusted service every single time.', Ill: IllVerify },
    { n:'04', title:'Enjoy your space',             desc:'Now just rest and enjoy a smooth, hassle-free service experience from start to finish.', Ill: IllRelax },
  ]
  return (
    <section className="sec" id="how-it-works">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">Easy process</span>
          <h2 className="h2">How to use<br />our service?</h2>
          <p className="lead">A simple guide to help you use our service effortlessly.</p>
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
          <span className="tag">Get the app</span>
          <h2 className="cta-h2">Book any worker,<br />anytime, anywhere.</h2>
          <p className="cta-p">12 job categories. Flexible slots from 4 hours to 7 days. Aadhaar-verified workers, guaranteed results.</p>
          <a href="mailto:hello@switchlocally.com" className="cta-mail">✉ hello@switchlocally.com</a>
          <div className="cta-btns">
            <a href="https://app.switchlocally.com/employer" className="btn-book">
              <IcoApple />
              <span>
                <span className="btn-sub" style={{opacity:0.55}}>Download on the</span>
                <span className="btn-main">App Store</span>
              </span>
            </a>
            <a href="https://app.switchlocally.com/employer" className="btn-book">
              <IcoPlay />
              <span>
                <span className="btn-sub" style={{opacity:0.55}}>Get it on</span>
                <span className="btn-main">Google Play</span>
              </span>
            </a>
          </div>
        </div>
        <div className="phones" data-anim style={{'--delay':'180ms'}}>
          <img src="/screen-2.png" alt="" className="ph ph-s" width="280" height="580" loading="lazy" decoding="async" />
          <img src="/screen-home.png" alt="Switch app — book verified workers in Gurgaon" className="ph ph-c" width="320" height="640" loading="lazy" decoding="async" />
          <img src="/screen-3.png" alt="" className="ph ph-s" width="280" height="580" loading="lazy" decoding="async" />
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
    alternateName: 'Switch Locally',
    description: 'Hire verified housekeeping staff, maids, cooks, drivers, cleaners, helpers, security guards, bouncers, bartenders and waiters in Gurgaon. All workers are Aadhaar-verified and background-checked.',
    url: 'https://switchlocally.com',
    email: 'hello@switchlocally.com',
    telephone: '+91-8368828660',
    image: 'https://switchlocally.com/hero-workers.jpg',
    logo: 'https://switchlocally.com/hero-workers.jpg',
    priceRange: '₹200-₹250 per hour',
    address: {
      '@type': 'PostalAddress',
      streetAddress: '5th Floor, WeWork, Cyber Hub',
      addressLocality: 'Gurgaon',
      addressRegion: 'Haryana',
      postalCode: '122002',
      addressCountry: 'IN',
    },
    geo: { '@type': 'GeoCoordinates', latitude: 28.4595, longitude: 77.0266 },
    areaServed: { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.8', bestRating: '5', reviewCount: '1000' },
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
    sameAs: [],
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
      <title>Hire Housekeeping, Maid &amp; Verified Workers in Gurgaon | Switch</title>
      <meta name="description" content="Hire verified housekeeping staff, maids, cooks, drivers, cleaning staff, helpers, security guards, bouncers, bartenders and waiters in Gurgaon. Background-checked, Aadhaar-verified workers — book in 2 minutes. Pay only after work is done." />
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

/* ─── FOOTER ──────────────────────────────────────── */
/* ─── PRICING ─────────────────────────────────────── */
function Pricing() {
  return (
    <section className="sec sec-alt sec-border-t" id="pricing">
      <div className="w">
        <div className="sec-hd" data-anim>
          <span className="tag">Pricing · Transparent</span>
          <h2 className="h2">Simple, honest pricing.</h2>
          <p className="lead">No hidden fees. Pay only for the hours you need — with an early-bird deal for your first bookings.</p>
        </div>

        <div className="pricing-grid" data-anim style={{'--delay':'80ms'}}>

          <div className="price-card price-card--featured">
            <div className="price-badge">First 5 Bookings</div>
            <div className="price-tag-wrap">
              <span className="price-currency">₹</span>
              <span className="price-amount">200</span>
              <span className="price-per">/hr</span>
            </div>
            <div className="price-name">Early Bird Rate</div>
            <p className="price-desc">Lock in our launch price for your first 5 bookings. All worker categories included.</p>
            <ul className="price-perks">
              <li><IcoCheck />Aadhaar-verified workers</li>
              <li><IcoCheck />Same-day availability</li>
              <li><IcoCheck />Free cancellation (2 hrs notice)</li>
              <li><IcoCheck />All durations: 4 hrs – 7 days</li>
            </ul>
            <a href="https://app.switchlocally.com/employer" className="price-cta price-cta--primary">
              <IcoBolt />Claim Early Bird Rate
            </a>
            <p className="price-note">Limited to first 5 bookings per account</p>
          </div>

          <div className="price-card">
            <div className="price-tag-wrap">
              <span className="price-currency">₹</span>
              <span className="price-amount">250</span>
              <span className="price-per">/hr</span>
            </div>
            <div className="price-name">Standard Rate</div>
            <p className="price-desc">Our regular rate after the early-bird period. Still the most competitive rate in the market.</p>
            <ul className="price-perks">
              <li><IcoCheck />Aadhaar-verified workers</li>
              <li><IcoCheck />Same-day availability</li>
              <li><IcoCheck />Free cancellation (2 hrs notice)</li>
              <li><IcoCheck />All durations: 4 hrs – 7 days</li>
            </ul>
            <a href="https://app.switchlocally.com/employer" className="price-cta price-cta--secondary">
              Book a Worker
            </a>
          </div>

        </div>

        <div className="pricing-note" data-anim style={{'--delay':'180ms'}}>
          All prices are per worker per hour. Multi-day bookings billed at hourly rate × hours worked. No platform fee.
        </div>
      </div>
    </section>
  )
}

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
            <a href="#" title="LinkedIn">in</a>
            <a href="#" title="X.com">𝕏</a>
            <a href="#" title="Instagram">ig</a>
          </div>
        </div>
        <div className="ft-col">
          <h3 className="ft-col-title">Support</h3>
          <ul>
            <li><a href="#">Contact Us</a></li>
            <li><a href="#">Help Centre</a></li>
            <li><a href="#">Delete Account</a></li>
          </ul>
        </div>
        <div className="ft-col">
          <h3 className="ft-col-title">Company</h3>
          <ul>
            <li><a href="mailto:careers@switchlocally.com">Careers</a></li>
            <li><a href="#">About Us</a></li>
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
        <Roles />
        <HowItWorks />
        <Pricing />
        <Reviews />
        <FAQ />
        <CTA />
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
      <Route path="/:slug" element={<SeoPage />} />
    </Routes>
  )
}
