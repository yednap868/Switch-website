import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import './AppPage.css'

const PLAY_URL = 'https://play.google.com/store/apps/details?id=com.switchlocally.employer'
const PHONE = '+918368828660'
const WA_MSG = encodeURIComponent("Hi Switch — I'd like to hire staff for my business in Gurgaon.")
const WHATSAPP_URL = `https://wa.me/${PHONE.replace('+', '')}?text=${WA_MSG}`

/* ─── ICONS ───────────────────────────────────────── */
function IcoApple() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden="true">
      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
    </svg>
  )
}
function IcoPlay() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden="true">
      <path d="M3.18 23.2c.3.17.64.26.99.26.52 0 1.03-.2 1.41-.58l14.02-8.1c.78-.45 1.25-1.27 1.25-2.17 0-.9-.47-1.72-1.25-2.17L5.58 2.34C5.2 1.96 4.69 1.76 4.17 1.76c-.35 0-.69.09-.99.26C2.47 2.47 2 3.25 2 4.17v15.66c0 .92.47 1.7 1.18 2.11z" />
    </svg>
  )
}
function IcoCheck() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="15" height="15" aria-hidden="true">
      <polyline points="3 8.5 6.5 12 13 5" />
    </svg>
  )
}
function IcoStar() {
  return (
    <svg viewBox="0 0 20 20" width="15" height="15" aria-hidden="true">
      <path fill="#f59e0b" d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  )
}

/* ─── DATA ────────────────────────────────────────── */
const FEATURES = [
  { ico: '⚡', title: 'Hire in a day', desc: 'Post your requirement and get matched with verified workers within hours — no agency runaround.' },
  { ico: '🆔', title: 'Aadhaar-verified staff', desc: 'Every worker is Aadhaar-verified, background-checked and skill-assessed before they reach your site.' },
  { ico: '🔁', title: 'Replacement guarantee', desc: 'A no-show won’t stop your business. We dispatch a replacement fast — usually within 24 hours.' },
  { ico: '📅', title: 'Hourly, daily or weekly', desc: 'Book a few hours, a full shift, or a 7-day team. The longer you book, the lower the per-worker rate.' },
  { ico: '💸', title: 'No advance — pay on arrival', desc: 'Track your bookings, pay only after the work is done, and get clean invoices for your records.' },
  { ico: '📲', title: 'Manage on the go', desc: 'Re-hire favourite workers, scale your team up or down, and chat with support — all from your phone.' },
]

const STEPS = [
  { n: '01', title: 'Download & sign up', desc: 'Install the app from Google Play and create your business account in under a minute.' },
  { n: '02', title: 'Post your requirement', desc: 'Pick the role, how many workers, and how long you need them — hourly to 7 days.' },
  { n: '03', title: 'Get verified staff', desc: 'Matched workers report to your site with OTP verification. Pay on arrival.' },
]

export default function AppPage() {
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

  const appSchema = {
    '@context': 'https://schema.org',
    '@type': 'MobileApplication',
    name: 'Switch — Hire Verified Staff in Gurgaon',
    operatingSystem: 'ANDROID',
    applicationCategory: 'BusinessApplication',
    url: 'https://switchlocally.com/app',
    downloadUrl: PLAY_URL,
    installUrl: PLAY_URL,
    description: 'Switch is Gurgaon’s business staffing app. Hire Aadhaar-verified store helpers, security guards, warehouse workers, waiters, cooks, drivers and housekeeping — by the hour, day or week. Replacement guaranteed, pay on arrival.',
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
        <meta name="description" content="Download the Switch app to hire Aadhaar-verified staff for your Gurgaon business — helpers, guards, cooks, waiters & more. Available on Google Play. iOS coming soon." />
        <meta name="keywords" content="Switch app download, Switch app Gurgaon, hire staff app, staffing app Gurgaon, Switch Google Play, download Switch app, business staffing app India" />
        <link rel="canonical" href="https://switchlocally.com/app" />
        <meta property="og:title" content="Download the Switch App — Hire Verified Staff in Gurgaon" />
        <meta property="og:description" content="Hire Aadhaar-verified staff for your business in a day. Available now on Google Play — iOS coming soon." />
        <meta property="og:url" content="https://switchlocally.com/app" />
        <meta property="og:image" content="https://switchlocally.com/switch-banner.jpg" />
        <script type="application/ld+json">{JSON.stringify(appSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
      </Helmet>
      <Nav />
      <main className="ap">

        {/* HERO */}
        <section className="ap-hero">
          <div className="ap-hero-bg" aria-hidden="true">
            <div className="ap-hero-glow" />
          </div>
          <div className="ap-hero-inner">
            <div className="ap-hero-copy" data-anim>
              <div className="ap-live">
                <span className="ap-dot" />
                <span>Now live on Google Play · Gurgaon</span>
              </div>
              <h1 className="ap-h1">Hire verified staff<br /><em>from your phone.</em></h1>
              <p className="ap-lead">
                Get the Switch app to staff your shop, restaurant, warehouse or office with Aadhaar-verified workers — by the hour, day or week. Replacement guaranteed, pay on arrival.
              </p>

              <div className="ap-stores">
                <a href={PLAY_URL} target="_blank" rel="noopener noreferrer" className="ap-store ap-store--live">
                  <IcoPlay />
                  <span className="ap-store-txt">
                    <span className="ap-store-sm">Download on</span>
                    <span className="ap-store-lg">Google Play</span>
                  </span>
                </a>
                <span className="ap-store ap-store--soon" aria-disabled="true" title="iOS app coming soon">
                  <IcoApple />
                  <span className="ap-store-txt">
                    <span className="ap-store-sm">Coming soon to</span>
                    <span className="ap-store-lg">App Store</span>
                  </span>
                  <span className="ap-soon-badge">Soon</span>
                </span>
              </div>

              <div className="ap-trust">
                <div className="ap-trust-stars">{[0, 1, 2, 3, 4].map(i => <IcoStar key={i} />)}</div>
                <span><strong>4.8</strong> rating · <strong>500+</strong> verified workers</span>
              </div>

              <p className="ap-ios-note">
                📱 On an iPhone? The iOS app isn’t out yet — you can still hire instantly on{' '}
                <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer">WhatsApp</a> or at{' '}
                <Link to="/">switchlocally.com</Link>.
              </p>
            </div>

            <div className="ap-hero-phones" data-anim style={{ '--delay': '160ms' }}>
              <img src="/screen-2.png" alt="Switch app — browse staff categories" className="ap-ph ap-ph-side ap-ph-left" width="390" height="844" loading="eager" decoding="async" />
              <img src="/screen-home.png" alt="Switch app — hire verified workers in Gurgaon" className="ap-ph ap-ph-main" width="390" height="844" loading="eager" decoding="async" fetchpriority="high" />
              <img src="/screen-3.png" alt="Switch app — verified worker profiles" className="ap-ph ap-ph-side ap-ph-right" width="390" height="844" loading="eager" decoding="async" />
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="ap-sec ap-sec-border">
          <div className="ap-w">
            <div className="ap-hd" data-anim>
              <span className="ap-tag">Why the app</span>
              <h2 className="ap-h2">Everything you need to<br />staff your business.</h2>
              <p className="ap-sub">Post a job, track your workers and manage payments — all from one app built for Gurgaon businesses.</p>
            </div>
            <div className="ap-feat-grid" data-anim style={{ '--delay': '80ms' }}>
              {FEATURES.map((f, i) => (
                <div className="ap-feat" key={i} style={{ '--delay': `${(i % 3) * 70}ms` }}>
                  <div className="ap-feat-ico">{f.ico}</div>
                  <h3 className="ap-feat-title">{f.title}</h3>
                  <p className="ap-feat-desc">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="ap-sec ap-sec-alt ap-sec-border">
          <div className="ap-w">
            <div className="ap-hd" data-anim>
              <span className="ap-tag">Get started</span>
              <h2 className="ap-h2">From download to<br />staffed in three steps.</h2>
            </div>
            <div className="ap-steps" data-anim style={{ '--delay': '80ms' }}>
              {STEPS.map((s, i) => (
                <div className="ap-step" key={i} style={{ '--delay': `${i * 100}ms` }}>
                  <div className="ap-step-n">{s.n}</div>
                  <h3 className="ap-step-title">{s.title}</h3>
                  <p className="ap-step-desc">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="ap-cta">
          <div className="ap-cta-inner" data-anim>
            <h2 className="ap-cta-h">Download Switch and<br />hire your first worker today.</h2>
            <p className="ap-cta-p">Free to download. No advance payment. Verified workers, replacement guaranteed.</p>
            <div className="ap-stores ap-stores--center">
              <a href={PLAY_URL} target="_blank" rel="noopener noreferrer" className="ap-store ap-store--live">
                <IcoPlay />
                <span className="ap-store-txt">
                  <span className="ap-store-sm">Download on</span>
                  <span className="ap-store-lg">Google Play</span>
                </span>
              </a>
              <span className="ap-store ap-store--soon" aria-disabled="true" title="iOS app coming soon">
                <IcoApple />
                <span className="ap-store-txt">
                  <span className="ap-store-sm">Coming soon to</span>
                  <span className="ap-store-lg">App Store</span>
                </span>
                <span className="ap-soon-badge">Soon</span>
              </span>
            </div>
            <div className="ap-cta-alt">
              <span>Prefer not to download?</span>
              <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" className="ap-cta-wa">💬 Hire on WhatsApp</a>
            </div>
            <ul className="ap-cta-perks">
              <li><IcoCheck /> Aadhaar-verified</li>
              <li><IcoCheck /> Replacement guarantee</li>
              <li><IcoCheck /> Pay on arrival</li>
            </ul>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
