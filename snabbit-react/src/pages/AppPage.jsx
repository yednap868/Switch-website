import PhoneChat from '../components/sx/PhoneChat.jsx'
import '../components/sx/sx.css'
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
  { ico: 'msg', title: 'Just talk to Jyoti', desc: 'Type or speak in Hindi, Hinglish, English or Telugu. Jyoti asks role, day, time, hours, people and address — one small question at a time.' },
  { ico: 'wallet', title: 'You set the rate', desc: 'Choose the hourly rate yourself. Each role has a fixed minimum; paying a little more finds someone faster.' },
  { ico: 'phone', title: 'Watch workers get called live', desc: 'Nearby workers get an app ring and a WhatsApp alert. See who saw it and who said yes, as it happens.' },
  { ico: 'check', title: '₹0 to post, ₹99 after a yes', desc: 'Confirming is free. You pay the ₹99 booking fee only when a worker accepts — then you get the start OTP.' },
  { ico: 'pin', title: 'Live tracking & start OTP', desc: 'Track the worker to your door. The job starts with your OTP, the timer runs, and you rate them after.' },
  { ico: 'book', title: 'Invoice on WhatsApp', desc: 'Every booking comes with a clean invoice on WhatsApp. The fare goes straight to the worker — Switch takes no cut.' },
]
const STEPS = [
  { n: '01', title: 'Download & say hello', desc: 'Install the app from Google Play or the App Store and tell Jyoti what you need.' },
  { n: '02', title: 'Answer a few taps', desc: 'Role, day, time, hours, how many people, your rate and address — Jyoti never decides for you.' },
  { n: '03', title: 'Pay ₹99 when someone says yes', desc: 'You get the start OTP, the worker gets your address, and you pay their fare directly after the work.' },
]
const PERKS = ['₹0 to post', '₹99 only after a yes', 'Fare paid to the worker']

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
    description: 'Switch is one chat with Jyoti, an AI assistant, to book cooks, kitchen helpers, housekeeping, waiters, utility staff and picker-packers in Gurugram — in Hindi, Hinglish, English or Telugu. ₹0 to post, ₹99 only after a worker accepts.',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'INR' },
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
        <meta name="description" content="Download the Switch app — one chat with Jyoti to book staff in Gurugram. ₹0 to post, ₹99 only when a worker says yes. On Google Play and the App Store." />
        <meta name="keywords" content="Switch app download, Switch app Gurgaon, hire staff app, staffing app Gurgaon, Switch Google Play, download Switch app, business staffing app India" />
        <link rel="canonical" href="https://switchlocally.com/app" />
        <meta property="og:title" content="Download the Switch App — Hire Verified Staff in Gurgaon" />
        <meta property="og:description" content="One chat with Jyoti to book staff in Gurugram. ₹0 to post, ₹99 only when a worker says yes." />
        <meta property="og:url" content="https://switchlocally.com/app" />
        <meta property="og:image" content="https://switchlocally.com/og-switch.png" />
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
              Staff chahiye? <em>Bas boliye.</em>
            </h1>
            <p className="sw-lead">
              The Switch app is one chat with Jyoti. Tell her what you need for your shop, restaurant, PG,
              hotel or home — she alerts verified workers nearby. ₹0 to post, ₹99 only when someone says yes.
            </p>
            <div className="sw-btns">
              <StoreButtons />
            </div>
            <div className="ap-trust">
              <span className="ap-stars" aria-hidden="true">★★★★★</span>
              <span><strong>4.8</strong> rating · <strong>20,000+</strong> verified workers</span>
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
            <div className="sx-tok" style={{ width: '100%', maxWidth: 360 }}>
              <PhoneChat />
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Why the app</p>
            <h2 className="sw-h2">Everything you need to <em>staff your business.</em></h2>
            <p className="sw-lead">One chat to post a shift, watch workers respond live, and pay only when it works.</p>
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
            <h2 className="sw-h2">From download to <em>a yes in three steps.</em></h2>
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
                Download Switch and <em>book your first shift today.</em>
              </h2>
              <p style={{ marginTop: 10, maxWidth: '52ch' }}>
                Free to download. Transparent rates. Verified workers, pay ₹99 only after a yes.
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
