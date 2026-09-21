import { useEffect, useRef, useState } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Analytics } from '@vercel/analytics/react'

import './styles/editorial.css'
import './styles/extras.css'

import Header from './components/chrome/Header.jsx'
import Footer from './components/chrome/Footer.jsx'
import HashScroll from './components/HashScroll.jsx'
import PixelCanvas from './components/fx/PixelCanvas.jsx'
import useScrollReveal from './components/fx/useScrollReveal.js'
import useToast from './components/fx/useToast.jsx'

import Hero from './components/home/Hero.jsx'
import ServiceEditorial from './components/home/ServiceEditorial.jsx'
import Journey from './components/home/Journey.jsx'
import TrustEditorial from './components/home/TrustEditorial.jsx'
import Coverage from './components/home/Coverage.jsx'
import AppSection from './components/home/AppSection.jsx'
import FinalCta from './components/home/FinalCta.jsx'

import SeoPage from './pages/SeoPage.jsx'
import PartnerPage from './pages/PartnerPage.jsx'
import AboutPage from './pages/AboutPage.jsx'
import BlogIndex from './pages/BlogIndex.jsx'
import BlogPost from './pages/BlogPost.jsx'
import AppPage from './pages/AppPage.jsx'
import LegalPage from './pages/LegalPage.jsx'
import StaffingPage from './pages/StaffingPage.jsx'
import VerifyPage from './pages/VerifyPage.jsx'

import { SERVICE_LIST } from './data/seoData.js'
import { FAQS } from './data/homeContent.js'
import { APP_URL, WHATSAPP_URL, waLink } from './data/site.js'

/* ─── SEO HEAD ────────────────────────────────────── */
function HomeHead() {
  const allServices = [
    'Housekeeping','Maid','House Cleaning','Cook','Driver','Cleaning Staff',
    'Security Guard','Bouncer','Bartender','Waiter','Kitchen Helper','Promoter',
    'Factory Helper','General Helper','Caretaker','Nanny','Delivery Switch Player',
  ]
  const localBusiness = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    '@id': 'https://switchlocally.com/#business',
    name: 'Switch',
    alternateName: ['Switch Locally', 'Switch App'],
    description: 'Switch is Gurgaon\'s business staffing platform. Hire Aadhaar-verified, background-checked store and general helpers, security guards, factory and warehouse Switch Players, waiters, bartenders, bouncers, promoters, drivers, cooks, kitchen helpers and housekeeping for shops, restaurants, warehouses, offices and events across all major areas and pincodes of Gurgaon. Bulk hiring, weekly teams, replacement guaranteed.',
    url: 'https://switchlocally.com',
    email: 'hello@switchlocally.com',
    telephone: '+91-9205617375',
    image: 'https://switchlocally.com/hero-workers.jpg',
    logo: 'https://switchlocally.com/hero-workers.jpg',
    priceRange: '₹99-₹199 per hour',
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
      telephone: '+91-9205617375',
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
    </Helmet>
  )
}

/* ─── SCROLL PROGRESS ─────────────────────────────── */
function ScrollProgress() {
  const ref = useRef(null)
  useEffect(() => {
    const fn = () => {
      const h = document.documentElement
      const max = h.scrollHeight - h.clientHeight || 1
      const p = Math.min(1, Math.max(0, h.scrollTop / max))
      if (ref.current) ref.current.style.transform = `scaleX(${p})`
    }
    fn()
    window.addEventListener('scroll', fn, { passive: true })
    window.addEventListener('resize', fn)
    return () => {
      window.removeEventListener('scroll', fn)
      window.removeEventListener('resize', fn)
    }
  }, [])
  return <div className="scroll-prog" ref={ref} aria-hidden="true" />
}

/* ─── SERVICES DIRECTORY ──────────────────────────── */
/* Every generated service page, linked from the homepage. */
function AllServicesDirectory() {
  return (
    <section className="svc-dir">
      <div className="shell">
        <div className="svc-dir-head">
          <div>
            <span className="eyebrow">BROWSE BY SERVICE</span>
            <h2>Every role, every guide.</h2>
          </div>
          <p>
            Pricing, hiring guides and verified professionals for every Switch Player type in
            Gurgaon.
          </p>
        </div>
        <div className="svc-dir-grid">
          {SERVICE_LIST.map((svc) => (
            <div className="svc-dir-card" key={svc.id}>
              <Link to={`/${svc.slug}`} className="svc-dir-card-head">
                <span>{svc.name}</span>
                <b>↗</b>
              </Link>
              <div className="svc-dir-chips">
                {svc.pages.slice(1).map((p) => (
                  <Link key={p.slug} to={`/${p.slug}`} className="svc-dir-chip">
                    {p.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
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
      sessionStorage.setItem('switch_offer_dismissed', '1')
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      if (sessionStorage.getItem('switch_offer_dismissed')) return
    } catch {
      /* ignore */
    }
    const t = setTimeout(() => setOpen(true), 1200)
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

  return (
    <div className="offer-pop-overlay" onClick={close}>
      <div
        className="offer-pop"
        role="dialog"
        aria-modal="true"
        aria-label="Special staffing offer"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="offer-pop-close" onClick={close} aria-label="Close offer">
          ✕
        </button>
        <span className="offer-pop-badge">LIMITED-TIME OFFER</span>
        <h3 className="offer-pop-title">
          Hire verified staff at just <span>₹999/mo</span>
        </h3>
        <p className="offer-pop-sub">
          Full-time, Aadhaar-verified Switch Players — a simple monthly plan, paid in advance, with
          replacement guaranteed.
        </p>
        <ul className="offer-pop-list">
          <li>
            <b>✓</b> Housekeeping, helpers, guards, pickers &amp; more
          </li>
          <li>
            <b>✓</b> Replacement guarantee
          </li>
          <li>
            <b>✓</b> Cancel anytime · GST extra · T&amp;C apply
          </li>
        </ul>
        <div className="offer-pop-cta">
          <a
            href={waLink(
              'Hi Switch — I want to hire staff on the ₹999/mo subscription. Please share the details.',
            )}
            target="_blank"
            rel="noreferrer"
            className="btn primary"
            onClick={close}
          >
            Hire now on WhatsApp ↗
          </a>
          <a href="#subscription" className="btn ghost" onClick={close}>
            View plans
          </a>
        </div>
      </div>
    </div>
  )
}

/* ─── ₹999 OFFER BANNER ───────────────────────────── */
/* Site-wide strip above the sticky header. Scrolls away with the page rather
   than eating viewport height on every screen; the sticky header takes over. */
function OfferBanner() {
  return (
    <aside className="offer-banner">
      <a
        className="offer-banner-inner"
        href={waLink('Hi Switch — I want to hire staff at ₹999 for a month. Please share the details.')}
        target="_blank"
        rel="noreferrer"
      >
        <span className="offer-banner-tag">OFFER</span>
        <strong>
          Hire staff at just <em>₹999</em> for a month
        </strong>
        <span className="offer-banner-tc">T&amp;C apply</span>
        <b className="offer-banner-cta">Hire now ↗</b>
      </a>
    </aside>
  )
}

/* ─── MOBILE STICKY CTA BAR ───────────────────────── */
function MobileCTABar() {
  return (
    <div className="mcta" aria-label="Quick actions">
      <a href={WHATSAPP_URL} target="_blank" rel="noreferrer">
        WhatsApp
      </a>
      <a href={APP_URL} className="mcta-hire">
        Hire staff ↗
      </a>
    </div>
  )
}

/* ─── HOME ────────────────────────────────────────── */
function HomePage() {
  const [toast, showToast] = useToast()
  useScrollReveal()

  return (
    <>
      <HomeHead />
      <ScrollProgress />
      <PixelCanvas />
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <OfferPopup />
      <main id="page-main">
        <Hero />
        <ServiceEditorial />
        <Journey />
        <TrustEditorial />
        <Coverage />
        <AppSection />
        <FinalCta onToast={showToast} />
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
      <OfferBanner />
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
        <Route path="/verify" element={<VerifyPage />} />
        <Route path="/:slug" element={<SeoPage />} />
      </Routes>
      <Analytics />
    </>
  )
}
