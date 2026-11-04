import { Suspense, useEffect, useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'

import './styles/switch.css'

import Header from './components/chrome/Header.jsx'
import Footer from './components/chrome/Footer.jsx'
import HashScroll from './components/HashScroll.jsx'
import ScrollReveal from './components/ScrollReveal.jsx'
import HomeHero from './components/home/HomeHero.jsx'
import useToast from './components/fx/useToast.jsx'
import Icon from './components/ui/Icon.jsx'
import { BrandBand, CtaFeature, Faq, Ticker, TrialTickets } from './components/ui/Blocks.jsx'
import {
  AppBlock,
  Coverage,
  How,
  Industries,
  PayrollBanner,
  Pricing,
  RequestForm,
  RoleTiles,
  Services,
  Trust,
} from './components/home/HomeSections.jsx'

import {
  AboutPage,
  AppPage,
  BlogIndex,
  BlogPost,
  IndustryPage,
  LegalPage,
  PartnerPage,
  SeoPage,
  StaffingPage,
  VerifyPage,
} from './routes.jsx'

import { INDUSTRY_LINKS, SERVICE_LIST } from './data/siteIndex.js'
import { FAQS, PAYROLL_PLANS, REVIEW_VIDEOS } from './data/homeContent.js'
import { PHONE, WHATSAPP_URL, waLink } from './data/site.js'

/* ─── SEO HEAD ────────────────────────────────────── */
function HomeHead() {
  const allServices = [
    'Housekeeping','Maid','House Cleaning','Cook','Cleaning Staff',
    'Security Guard','Bouncer','Bartender','Waiter','Kitchen Helper','Promoter',
    'Factory Helper','General Helper','Caretaker','Nanny','Delivery Switch Player',
  ]
  const localBusiness = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    '@id': 'https://switchlocally.com/#business',
    name: 'Switch',
    alternateName: ['Switch Locally', 'Switch App'],
    description: 'Switch is Gurgaon\'s business staffing platform. Hire Aadhaar-verified, background-checked store and general helpers, security guards, factory and warehouse Switch Players, waiters, bartenders, bouncers, promoters, cooks, kitchen helpers and housekeeping for shops, restaurants, warehouses, offices and events across all major areas and pincodes of Gurgaon. Bulk hiring, weekly teams, replacement guaranteed.',
    url: 'https://switchlocally.com',
    email: 'hello@switchlocally.com',
    image: 'https://switchlocally.com/hero-workers.jpg',
    logo: 'https://switchlocally.com/hero-workers.jpg',
    priceRange: '₹119-₹599 per hour',
    address: {
      '@type': 'PostalAddress',
      addressLocality: 'Gurgaon',
      addressRegion: 'Haryana',
      addressCountry: 'IN',
    },
    geo: { '@type': 'GeoCoordinates', latitude: 28.4595, longitude: 77.0266 },
    areaServed: [
      { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
      { '@type': 'City', name: 'Gurugram' },
      ...['DLF Phase 1','DLF Phase 3','DLF Phase 4','DLF Queens Enclave','Sushant Lok Phase 1','Sushant Lok Phase 2','Sushant Lok Phase 3','Palam Vihar','Udyog Vihar','Sohna Road','Cyber City','MG Road','Galleria Market','Sector 14','Sector 17','Sector 23','Sector 31','Sector 40','Sector 47','Sector 49','Chakkarpur','Sikanderpur','Nathupur','Greenwood City','Malibu Towne','Sun City'].map(n => ({ '@type': 'Place', name: `${n}, Gurgaon` })),
      ...['122001','122002','122006','122009','122010','122017','122018','122022'].map(p => ({ '@type': 'PostalAddress', postalCode: p, addressLocality: 'Gurgaon', addressRegion: 'Haryana', addressCountry: 'IN' })),
    ],
    telephone: PHONE,
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
    sameAs: ['https://www.linkedin.com/company/switchlocal', 'https://www.instagram.com/switchlocally/', 'https://www.facebook.com/switchlocally'],
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
      contactType: 'customer service',
      areaServed: 'IN',
      availableLanguage: ['en', 'hi'],
    },
    sameAs: ['https://www.linkedin.com/company/switchlocal', 'https://www.instagram.com/switchlocally/', 'https://www.facebook.com/switchlocally'],
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
  const videoSchema = REVIEW_VIDEOS.map((v) => {
    const [m, sec] = v.len.split(':').map(Number)
    return {
      '@context': 'https://schema.org',
      '@type': 'VideoObject',
      name: `${v.who} reviews Switch staffing`,
      description: `${v.who}, ${v.where}: ${v.line}`,
      thumbnailUrl: `https://switchlocally.com${v.poster}`,
      contentUrl: `https://switchlocally.com${v.src}`,
      uploadDate: '2026-09-26',
      duration: `PT${m}M${sec}S`,
      publisher: { '@type': 'Organization', name: 'Switch', url: 'https://switchlocally.com' },
    }
  })
  return (
    <Helmet>
      <title>Hire Verified Staff for Business in Gurgaon | Switch</title>
      <meta name="description" content="Hire Aadhaar-verified staff for your Gurgaon business — helpers, guards, cooks, waiters &amp; more. Bulk &amp; weekly teams, replacement guaranteed, transparent rates." />
      <meta name="keywords" content="staffing agency Gurgaon, manpower supply Gurgaon, hire staff for business Gurgaon, bulk hiring Gurgaon, contract staff Gurgaon, restaurant staff Gurgaon, warehouse Switch Players Gurgaon, factory helper Gurgaon, store helper Gurgaon, retail staff Gurgaon, security guard Gurgaon, waiter for events Gurgaon, bartender hire Gurgaon, bouncer Gurgaon, housekeeping staff Gurgaon, office boy Gurgaon, on-demand blue-collar staffing Gurgaon, hire Switch Players Udyog Vihar, Cyber City staffing, DLF business staff, Sohna Road staffing, switchlocally.com, Switch App, same-day Switch Player hiring Gurgaon, replacement guarantee staffing Gurgaon, transparent staffing rates Gurgaon, weekly staff hire Gurgaon" />
      <link rel="canonical" href="https://switchlocally.com/" />
      <meta property="og:title" content="Staffing for Business in Gurgaon — Hire Verified Switch Players | Switch" />
      <meta property="og:description" content="Hire Aadhaar-verified staff for shops, restaurants, warehouses, offices &amp; events in Gurgaon — store helpers, guards, waiters, cooks, housekeeping. Bulk &amp; weekly teams, replacement guaranteed, transparent rates." />
      <meta property="og:url" content="https://switchlocally.com/" />
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="Switch" />
      <meta property="og:image" content="https://switchlocally.com/hero-workers.jpg" />
      <meta property="og:locale" content="en_IN" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content="Staffing for Business in Gurgaon — Hire Verified Switch Players | Switch" />
      <meta name="twitter:description" content="Hire verified staff for shops, restaurants, warehouses, offices &amp; events in Gurgaon. Store helpers, guards, waiters, cooks, housekeeping. Bulk &amp; weekly teams." />
      <meta name="twitter:image" content="https://switchlocally.com/hero-workers.jpg" />
      <script type="application/ld+json">{JSON.stringify(localBusiness)}</script>
      <script type="application/ld+json">{JSON.stringify(websiteSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(orgSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
      {videoSchema.map((v) => (
        <script key={v.contentUrl} type="application/ld+json">
          {JSON.stringify(v)}
        </script>
      ))}
    </Helmet>
  )
}

/* ─── SERVICES DIRECTORY ──────────────────────────── */
/* Every generated service page, linked from the homepage (internal linking
   for the ~190 SEO pages). */
function AllServicesDirectory() {
  return (
    <section className="sw-sec" id="svc-dir">
      <div className="sw-head">
        <p className="sw-eyebrow">Browse by service</p>
        <h2 className="sw-h2">
          Every role, <em>every guide.</em>
        </h2>
        <p className="sw-lead">Pricing, hiring guides and verified professionals for every role in Gurgaon.</p>
      </div>
      <div className="sw-grid sw-g4 sw-swipe">
        {SERVICE_LIST.map((svc) => (
          <div className="sw-card" key={svc.id} style={{ padding: 16, display: 'grid', gap: 10, alignContent: 'start' }}>
            <Link to={`/${svc.slug}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 800 }}>
              {svc.name}
              <span className="sw-go" style={{ width: 30, height: 30 }}>
                <Icon name="arrow" />
              </span>
            </Link>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {svc.pages.slice(1).map((p) => (
                <Link key={p.slug} to={`/${p.slug}`} className="sw-tag" style={{ height: 'auto', padding: '4px 9px' }}>
                  {p.label}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ─── OFFER POPUP ─────────────────────────────────── */
function OfferPopup() {
  const [open, setOpen] = useState(false)
  const close = () => {
    setOpen(false)
    try {
      sessionStorage.setItem('switch_payroll_dismissed', '1')
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      if (sessionStorage.getItem('switch_payroll_dismissed')) return
    } catch {
      /* ignore */
    }
    /* First thing a visitor sees, once the page has had a moment to paint. */
    const t = setTimeout(() => setOpen(true), 900)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])

  if (!open) return null

  const [day1] = PAYROLL_PLANS
  return (
    <div className="sw-pop-bg" onClick={close}>
      <div
        className="sw-pop sw-pop-pay sw-feature"
        role="dialog"
        aria-modal="true"
        aria-label="Hire staff on your payroll"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="sw-vm-x" onClick={close} aria-label="Close offer">
          ✕
        </button>
        <div className="sw-pop-ph">
          <img src="/hero-workers.jpg" alt="" />
          <p>
            Your staff.
            <br />
            Your salary.
          </p>
        </div>
        <div className="sw-pop-body">
          <span className="sw-pill">New · Hire on your payroll</span>
          <h2>
            Staff on your payroll from <em>₹2,000/month.</em>
          </h2>
          <p>Monthly retention fee for the same worker.</p>
          <div className="sw-pop-fees">
            {PAYROLL_PLANS.map((p) => (
              <div className={p.featured ? 'on' : ''} key={p.name}>
                <span>{p.name}</span>
                <b>{p.price}</b>
                <small>per worker / month</small>
              </div>
            ))}
          </div>
          <ul className="sw-pop-inc">
            {day1.items.map((it) => (
              <li key={it}>
                <Icon name="check" />
                {it}
              </li>
            ))}
          </ul>
          <a className="sw-btn white" href={waLink(day1.msg)} target="_blank" rel="noreferrer" onClick={close}>
            {day1.cta} <Icon name="arrow" />
          </a>
          <a className="sw-pop-alt" href="#trial" onClick={close}>
            Or try a verified worker for ₹429
          </a>
        </div>
      </div>
    </div>
  )
}

/* ─── OFFER BANNER ────────────────────────────────── */
/* Site-wide strip above the sticky header. Scrolls away with the page rather
   than eating viewport height on every screen; the sticky header takes over. */
function OfferBanner() {
  return (
    <aside className="sw-strip">
      <a href="/#trial">
        <span>
          <b>New</b> · 4-hour trial at <b>₹429</b> · 50% off your first booking · Monthly staff from <b>₹20,800</b>
        </span>
        <u>See offers</u>
      </a>
    </aside>
  )
}

/* ─── MOBILE / BOTTOM CTA BAR ─────────────────────── */
function MobileCTABar() {
  /* Shows once the hero is scrolled past, and steps aside for the request
     form and the footer so it never covers them. Hidden in the server HTML. */
  const [show, setShow] = useState(false)
  useEffect(() => {
    let blocked = false
    const update = () => setShow(window.scrollY > 560 && !blocked)
    const io =
      'IntersectionObserver' in window
        ? new IntersectionObserver((entries) => {
            blocked = entries.some((e) => e.isIntersecting)
            update()
          })
        : null
    document.querySelectorAll('#request, footer').forEach((el) => io?.observe(el))
    update()
    window.addEventListener('scroll', update, { passive: true })
    return () => {
      io?.disconnect()
      window.removeEventListener('scroll', update)
    }
  }, [])
  return (
    <div className={`sw-bar${show ? '' : ' is-hidden'}`} aria-label="Quick actions">
      <a href={WHATSAPP_URL} target="_blank" rel="noreferrer" tabIndex={show ? undefined : -1}>
        <span>
          <b>Hire verified staff</b>
          <small>4-hour trial at ₹429 · Staff in a day</small>
        </span>
        <span className="gob">
          WhatsApp <Icon name="arrow" />
        </span>
      </a>
    </div>
  )
}

/* ─── HOME ────────────────────────────────────────── */
function HomePage() {
  const [toast, showToast] = useToast()

  return (
    <>
      <HomeHead />
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <OfferPopup />
      <main id="page-main" className="sw-wrap">
        <HomeHero />
        <PayrollBanner />
        <RoleTiles />
        <Ticker />
        <BrandBand />
        <TrialTickets />
        <Services />
        <Industries />
        <How />
        <Pricing />
        <Trust />
        <Coverage />
        <AppBlock />
        <RequestForm onToast={showToast} />
        <section className="sw-sec" id="faq" style={{ paddingTop: 0 }}>
          <div className="sw-head">
            <p className="sw-eyebrow">Questions, answered</p>
            <h2 className="sw-h2">
              Before you <em>book.</em>
            </h2>
          </div>
          <Faq items={FAQS} two />
        </section>
        <CtaFeature
          title={
            <>
              Staff who show up. <em>Book your first shift.</em>
            </>
          }
          sub="Aadhaar-verified people across Gurgaon, a replacement within 24 hours, and a clear invoice. Try one for 4 hours at ₹429."
          photos={['/sw-maid.jpg', '/sw-kitchen-helper.jpg']}
        />
        <AllServicesDirectory />
      </main>
      <Footer />
      <MobileCTABar />
      {toast}
    </>
  )
}

/* ─── ROUTES ──────────────────────────────────────── */
export default function App() {
  return (
    <>
      <HashScroll />
      <ScrollReveal />
      <OfferBanner />
      <Suspense fallback={null}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/partner" element={<PartnerPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/blog" element={<BlogIndex />} />
          <Route path="/blog/:slug" element={<BlogPost />} />
          <Route path="/app" element={<AppPage />} />
          <Route path="/terms" element={<LegalPage policy="terms" />} />
          <Route path="/privacy" element={<LegalPage policy="privacy" />} />
          <Route path="/cancellation" element={<LegalPage policy="cancellation" />} />
          <Route path="/staffing-gurgaon" element={<StaffingPage />} />
          {INDUSTRY_LINKS.map((p) => (
            <Route key={p.slug} path={`/${p.slug}`} element={<IndustryPage slug={p.slug} />} />
          ))}
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/:slug" element={<SeoPage />} />
        </Routes>
      </Suspense>
    </>
  )
}
