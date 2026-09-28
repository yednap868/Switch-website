import AppScreens from '../components/ui/AppScreens.jsx'
import { useEffect } from 'react'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs, StoreButtons } from '../components/ui/Blocks.jsx'
import { APP_URL, APPLE_URL, PLAY_URL, WHATSAPP_URL, trackWhatsApp } from '../data/site.js'
import './AppPage.css'

const TINTS = ['t-lav', 't-mint', 't-sky', 't-peach', 't-pink', 't-lav']

const FEATURES = [
  { ico: 'timer',  title: 'Hire in a day', desc: 'Post your requirement and get matched with verified Switch Players within hours — no agency runaround.' },
  { ico: 'shield', title: 'Aadhaar-verified staff', desc: 'Every Switch Player is Aadhaar-verified, background-checked and skill-assessed before they reach your site.' },
  { ico: 'check',  title: 'Replacement guarantee', desc: 'A no-show won’t stop your business. We dispatch a replacement fast — usually within 24 hours.' },
  { ico: 'cal',    title: 'Hourly, daily or weekly', desc: 'Book a few hours, a full shift, or a 7-day team. The longer you book, the lower the rate per Switch Player.' },
  { ico: 'wallet', title: 'Transparent billing', desc: 'Track your bookings, see exactly what you are charged, and get clean invoices for your records.' },
  { ico: 'phone',  title: 'Manage on the go', desc: 'Re-hire favourite Switch Players, scale your team up or down, and chat with support — all from your phone.' },
]

const STEPS = [
  { n: '01', title: 'Download & sign up', desc: 'Install the app from Google Play or the App Store and create your business account in under a minute.' },
  { n: '02', title: 'Post your requirement', desc: 'Pick the role, how many Switch Players, and how long you need them — hourly to 7 days.' },
  { n: '03', title: 'Get verified staff', desc: 'Matched Switch Players report to your site with OTP verification, and every shift is invoiced clearly.' },
]

const PERKS = ['Aadhaar-verified', 'Replacement guarantee', 'Transparent billing']

export default function AppPage() {
  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0)
  }, [])

  const appSchema = {
    '@context': 'https://schema.org',
    '@type': 'MobileApplication',
    name: 'Switch — Hire Verified Staff in Gurgaon',
    operatingSystem: 'ANDROID, IOS',
    applicationCategory: 'BusinessApplication',
    url: 'https://switchlocally.com/app',
    downloadUrl: [PLAY_URL, APPLE_URL],
    installUrl: [PLAY_URL, APPLE_URL],
    description: 'Switch is Gurgaon’s business staffing app. Hire Aadhaar-verified store helpers, security guards, warehouse Switch Players, waiters, cooks, drivers and housekeeping — by the hour, day or week. Replacement guaranteed, transparent rates.',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'INR' },
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.8', bestRating: '5', ratingCount: '500' },
    publisher: { '@type': 'Organization', name: 'Switch', url: 'https://switchlocally.com' },
  }

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://switchlocally.com/' },
      { '@type': 'ListItem', position: 2, name: 'Download App', item: 'https://switchlocally.com/app' },
    ],
  }

  return (
    <>
      <Helmet>
        <title>Download the Switch App — Hire Verified Staff in Gurgaon</title>
        <meta name="description" content="Download the Switch app to hire Aadhaar-verified staff for your Gurgaon business — helpers, guards, cooks, waiters & more. Available on Google Play and the App Store." />
        <meta name="keywords" content="Switch app download, Switch app Gurgaon, hire staff app, staffing app Gurgaon, Switch Google Play, download Switch app, business staffing app India" />
        <link rel="canonical" href="https://switchlocally.com/app" />
        <meta property="og:title" content="Download the Switch App — Hire Verified Staff in Gurgaon" />
        <meta property="og:description" content="Hire Aadhaar-verified staff for your business in a day. Available now on Google Play and the App Store." />
        <meta property="og:url" content="https://switchlocally.com/app" />
        <meta property="og:image" content="https://switchlocally.com/switch-banner.jpg" />
        <script type="application/ld+json">{JSON.stringify(appSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
      </Helmet>

      <a className="skip-link" href="#page-main">Skip to main content</a>
      <Header />

      <main id="page-main" className="sw-wrap ap">
        <Crumbs items={[['Download App']]} />

        {/* HERO */}
        <section className="sw-hero ap-hero">
          <div>
            <span className="sw-pill sw-live">Now live on Google Play &amp; the App Store · Gurgaon</span>
            <h1 className="sw-h1" style={{ marginTop: 14 }}>
              Hire verified staff <em>from your phone.</em>
            </h1>
            <p className="sw-lead">
              Get the Switch app to staff your shop, restaurant, warehouse or office with Aadhaar-verified
              Switch Players — by the hour, day or week. Replacement guaranteed, transparent rates.
            </p>
            <div className="sw-btns">
              <StoreButtons />
            </div>
            <div className="ap-trust">
              <span className="ap-stars" aria-hidden="true">★★★★★</span>
              <span><strong>4.8</strong> rating · <strong>20,000+</strong> verified Switch Players</span>
            </div>
            <p className="ap-note">
              On Android or iPhone, the Switch app is live on{' '}
              <a href={PLAY_URL} target="_blank" rel="noopener noreferrer">Google Play</a> and the{' '}
              <a href={APPLE_URL} target="_blank" rel="noopener noreferrer">App Store</a> — or hire instantly on{' '}
              <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" onClick={() => trackWhatsApp('app_hero_note')}>WhatsApp</a>{' '}
              and at{' '}
              <a href={APP_URL} target="_blank" rel="noopener noreferrer">app.switchlocally.com</a>.
            </p>
          </div>

          <div className="ap-art">
            <div className="sw-blob" aria-hidden="true" />
            <AppScreens />
          </div>
        </section>

        {/* FEATURES */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Why the app</p>
            <h2 className="sw-h2">Everything you need to <em>staff your business.</em></h2>
            <p className="sw-lead">Post a job, track your Switch Players and manage payments — all from one app built for Gurgaon businesses.</p>
          </div>
          <div className="sw-grid sw-g3">
            {FEATURES.map((f, i) => (
              <div className="sw-card sw-ind" key={f.title}>
                <span className={`sw-sq ${TINTS[i % TINTS.length]}`}>
                  <Icon name={f.ico} />
                </span>
                <h3 className="sw-h3">{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Get started</p>
            <h2 className="sw-h2">From download to <em>staffed in three steps.</em></h2>
          </div>
          <div className="sw-grid sw-g3">
            {STEPS.map((s) => (
              <div className="sw-card sw-step" key={s.n}>
                <span className="n">STEP {s.n}</span>
                <h3 className="sw-h3">{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="sw-sec">
          <div className="sw-feature sw-feature-grid ap-cta">
            <div>
              <p className="sw-eyebrow">Free to download</p>
              <h2 style={{ marginTop: 10 }}>
                Download Switch and <em>hire your first Switch Player today.</em>
              </h2>
              <p style={{ marginTop: 10, maxWidth: '52ch' }}>
                Free to download. Transparent rates. Verified Switch Players, replacement guaranteed.
              </p>
              <div className="sw-btns" style={{ marginTop: 18 }}>
                <StoreButtons />
              </div>
              <p className="ap-cta-alt">
                <span>Prefer not to download?</span>
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" onClick={() => trackWhatsApp('app_cta')}>
                  Hire on WhatsApp <Icon name="arrow" />
                </a>
              </p>
              <ul className="ap-perks">
                {PERKS.map((x) => (
                  <li key={x}><Icon name="check" />{x}</li>
                ))}
              </ul>
            </div>
            <div className="sw-f-art" aria-hidden="true">
              <div className="sw-blob" />
              <div className="sw-arch a1">
                <img src="/sw-general-helper.jpg" alt="" loading="lazy" />
              </div>
              <div className="sw-arch a2">
                <img src="/sw-security-guard.jpg" alt="" loading="lazy" />
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
