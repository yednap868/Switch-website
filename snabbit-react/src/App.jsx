import { Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'

import './styles/switch.css'

import HashScroll from './components/HashScroll.jsx'
import ScrollReveal from './components/ScrollReveal.jsx'

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
import { FAQS } from './data/switchHome.js'
import SwitchHome from './components/sx/SwitchHome.jsx'
import WorkerPage from './components/sx/WorkerPage.jsx'
import NotFound from './components/sx/NotFound.jsx'
import { PHONE } from './data/site.js'

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
    description: 'Switch is one chat with Jyoti, an AI assistant: businesses and homes in Gurugram book cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers, and workers find jobs near them — in Hindi, Hinglish, English or Telugu. ₹0 to post; a ₹99 booking fee only after a worker accepts..',
    url: 'https://switchlocally.com',
    email: 'hello@switchlocally.com',
    image: 'https://switchlocally.com/hero-workers.jpg',
    logo: 'https://switchlocally.com/hero-workers.jpg',
    priceRange: '₹0 to post · ₹99 booking fee',
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
    legalName: 'Third Wave Labs Private Limited',
    url: 'https://switchlocally.com',
    logo: 'https://switchlocally.com/favicon-512.png',
    slogan: 'Staff chahiye? Bas boliye.',
    description: 'Switch is a staffing app for Gurugram: businesses and homes book cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers by chatting with Jyoti, an AI assistant, in Hindi, Hinglish, English or Telugu. ₹0 to post, ₹99 only after a worker accepts; the fare goes to the worker.',
    knowsAbout: ['Staffing in Gurgaon', 'Hiring cooks', 'Kitchen helpers', 'Housekeeping staff', 'Waiters', 'Utility staff', 'Picker and packer jobs', 'Blue-collar jobs in Gurugram'],
    areaServed: { '@type': 'City', name: 'Gurugram' },
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer service',
      areaServed: 'IN',
      availableLanguage: ['en', 'hi', 'te'],
      telephone: PHONE,
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
      <title>Book Staff in Gurugram — Just Ask Jyoti | Switch</title>
      <meta name="description" content="Staff chahiye? Bas boliye. Book cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers in Gurugram by chatting with Jyoti — Hindi, Hinglish, English or Telugu. ₹0 to post, ₹99 only when a worker says yes; the fare goes straight to the worker." />
      <meta name="keywords" content="staffing agency Gurgaon, manpower supply Gurgaon, hire staff for business Gurgaon, bulk hiring Gurgaon, contract staff Gurgaon, restaurant staff Gurgaon, warehouse Switch Players Gurgaon, factory helper Gurgaon, store helper Gurgaon, retail staff Gurgaon, security guard Gurgaon, waiter for events Gurgaon, bartender hire Gurgaon, bouncer Gurgaon, housekeeping staff Gurgaon, office boy Gurgaon, on-demand blue-collar staffing Gurgaon, hire Switch Players Udyog Vihar, Cyber City staffing, DLF business staff, Sohna Road staffing, switchlocally.com, Switch App, same-day Switch Player hiring Gurgaon, replacement guarantee staffing Gurgaon, transparent staffing rates Gurgaon, weekly staff hire Gurgaon" />
      <link rel="canonical" href="https://switchlocally.com/" />
      <meta property="og:title" content="Book Staff in Gurugram — Just Ask Jyoti | Switch" />
      <meta property="og:description" content="Staff chahiye? Bas boliye. Book cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers in Gurugram by chatting with Jyoti — Hindi, Hinglish, English or Telugu. ₹0 to post, ₹99 only when a worker says yes; the fare goes straight to the worker." />
      <meta property="og:url" content="https://switchlocally.com/" />
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="Switch" />
      <meta property="og:image" content="https://switchlocally.com/og-switch.png" />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:image:alt" content="Switch — Staff chahiye? Bas boliye. One chat with Jyoti." />
      <meta property="og:locale" content="en_IN" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content="Book Staff in Gurugram — Just Ask Jyoti | Switch" />
      <meta name="twitter:description" content="Staff chahiye? Bas boliye. Book cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers in Gurugram by chatting with Jyoti — Hindi, Hinglish, English or Telugu. ₹0 to post, ₹99 only when a worker says yes; the fare goes straight to the worker." />
      <meta name="twitter:image" content="https://switchlocally.com/og-switch.png" />
      <script type="application/ld+json">{JSON.stringify(localBusiness)}</script>
      <script type="application/ld+json">{JSON.stringify(websiteSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(orgSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
    </Helmet>
  )
}

/* ─── SERVICES DIRECTORY ──────────────────────────── */
/* Every generated service page, linked from the homepage (internal linking
   for the ~190 SEO pages). */
/* ─── OFFER BANNER ────────────────────────────────── */
/* ─── HOME ────────────────────────────────────────── */
function HomePage() {
  return (
    <>
      <HomeHead />
      <SwitchHome />
    </>
  )
}

/* ─── ROUTES ──────────────────────────────────────── */
export default function App() {
  return (
    <>
      <HashScroll />
      <ScrollReveal />
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
          <Route path="/work" element={<WorkerPage />} />
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="/:slug" element={<SeoPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </>
  )
}
