/* switchlocally.com — the homepage for the new Switch app: one chat with
   Jyoti. Mobile-first (390px), off-white with one green accent, serif
   headings. Own header and footer so the page reads as one piece; the rest of
   the site keeps its shared chrome. Styles: ./sx.css (prefix sx-). */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import PhoneChat from './PhoneChat.jsx'
import Radar from './Radar.jsx'
import { APP_URL, APPLE_URL, PHONE, PLAY_URL, WHATSAPP_URL, trackWhatsApp } from '../../data/site.js'
import CostCalc from './CostCalc.jsx'
import { SxHeader } from './SxChrome.jsx'
import Footer from '../chrome/Footer.jsx'
import { FAQS, LANG_LINES_EMPLOYER as LANG_LINES } from '../../data/switchHome.js'
import HowSteps from './HowSteps.jsx'
import { BRANDS, REVIEWS, REVIEW_VIDEOS } from '../../data/homeContent.js'
import './sx.css'

function Hero() {
  return (
    <section className="sx-hero" id="top">
      <div className="sx-wrap sx-hero-in">
        <div className="sx-hero-copy">
          <p className="sx-kicker">
            <span className="sx-live-dot" aria-hidden="true" /> Gurugram · Jyoti searches the offline world for you
          </p>
          <h1 className="sx-h1">
            Staff chahiye? Bas boliye<span className="sx-dot">.</span>
          </h1>
          <p className="sx-lead">
            Tell Jyoti what you need — in Hindi, Hinglish, English or Telugu. She alerts verified
            workers near you, live. Posting is free; you pay ₹99 only when someone says yes.
          </p>
          <div className="sx-btns">
            <a className="sx-btn" href={APP_URL} target="_blank" rel="noreferrer">
              Book staff <Icon name="arrow" />
            </a>
            <Link className="sx-btn ghost" to="/work">
              Find work
            </Link>
          </div>
          <ul className="sx-hero-facts">
            <li>
              <b>₹0</b> to post
            </li>
            <li>
              <b>₹99</b> after a yes
            </li>
            <li>
              <b>100%</b> fare to the worker
            </li>
          </ul>
        </div>
        <div className="sx-hero-phone">
          <div className="sx-hero-photos" aria-hidden="true">
            <img className="p1" src="/img/sw-cook.webp" alt="" width="520" height="520" fetchpriority="low" />
            <img className="p2" src="/img/sw-waiter.webp" alt="" width="520" height="520" fetchpriority="low" />
            <img className="p3" src="/img/sw-kitchen-helper.webp" alt="" width="520" height="520" fetchpriority="low" />
            <div className="sx-hero-badge b1">
              <img src="/av/ravi.jpg" alt="" width="36" height="36" />
              <span>
                <b>Ravi said yes</b>
                <small>Cook · 0.8 km away</small>
              </span>
            </div>
            <div className="sx-hero-badge b2">
              <span className="sx-otp-mini">4719</span>
              <span>
                <b>Start OTP</b>
                <small>Job starts at your door</small>
              </span>
            </div>
          </div>
          <PhoneChat />
          <p className="sx-cap">Try it — tap your answers. A preview of the Switch app.</p>
        </div>
      </div>
    </section>
  )
}

/* Real clients — the same logo set the site has always shown. Tiles stay
   white in dark mode too, because several marks are dark ink. */
function Brands() {
  return (
    <section className="sx-brands" aria-labelledby="sx-b-h">
      <div className="sx-wrap">
        <p id="sx-b-h" className="sx-brands-h">
          Trusted by <b>1,500+</b> Gurugram businesses
        </p>
      </div>
      <div className="sx-marquee sx-logo-row">
        <div className="sx-track slow">
          {[...BRANDS, ...BRANDS].map((b, i) => (
            <div key={i} className={`sx-logo-tile${b.light ? ' light' : ''}`} aria-hidden={i >= BRANDS.length ? 'true' : undefined}>
              {b.logo ? <img src={b.logo} alt={i < BRANDS.length ? b.name : ''} loading="lazy" width="112" height="48" /> : <span>{b.name}</span>}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function VideoReview({ v }) {
  const [play, setPlay] = useState(false)
  return (
    <figure className="sx-vid">
      {play ? (
        <video src={v.src} poster={v.poster} controls autoPlay playsInline preload="none" />
      ) : (
        <button type="button" onClick={() => setPlay(true)}>
          <span className="sx-sr">Play review: {v.who}, </span>
          <img src={v.poster} alt="" loading="lazy" />
          <span className="sx-play" aria-hidden="true">
            <Icon name="play" />
          </span>
          <span className="sx-len">{v.len}</span>
        </button>
      )}
      <figcaption>
        <b>{v.who}</b>
        <span>{v.where}</span>
      </figcaption>
    </figure>
  )
}

function Reviews() {
  return (
    <section className="sx-sec" id="reviews" aria-labelledby="sx-r-h">
      <div className="sx-wrap">
        <p className="sx-eyebrow">What customers say</p>
        <h2 id="sx-r-h" className="sx-h2">
          Heard from the people who book<span className="sx-dot">.</span>
        </h2>
        <div className="sx-vids">
          {REVIEW_VIDEOS.map((v) => (
            <VideoReview key={v.src} v={v} />
          ))}
        </div>
        <div className="sx-quotes">
          {REVIEWS.slice(0, 6).map((r) => (
            <blockquote key={r.name} className="sx-card sx-quote">
              <span className="sx-qmark" aria-hidden="true">
                “
              </span>
              <p>{r.text}</p>
              <footer>
                <span className="sx-av" aria-hidden="true">
                  {r.name[0]}
                </span>
                <span>
                  <b>{r.name}</b>
                  <small>{r.loc}</small>
                </span>
              </footer>
            </blockquote>
          ))}
        </div>
      </div>
    </section>
  )
}

function How() {
  return (
    <section className="sx-sec" id="how" aria-labelledby="sx-how-h">
      <div className="sx-wrap">
        <p className="sx-eyebrow">For businesses & homes</p>
        <h2 id="sx-how-h" className="sx-h2">
          Four steps. You only talk<span className="sx-dot">.</span>
        </h2>
        <HowSteps />
        <p className="sx-note">
          Roles: cook, kitchen helper, housekeeping, waiter, utility staff, picker-packer — for shops,
          restaurants, PGs, hotels and homes.
        </p>
      </div>
    </section>
  )
}

function Pricing() {
  return (
    <section className="sx-sec" id="pricing" aria-labelledby="sx-price-h">
      <div className="sx-wrap">
        <p className="sx-eyebrow">Pricing</p>
        <h2 id="sx-price-h" className="sx-h2">
          Pay when it works. Not before<span className="sx-dot">.</span>
        </h2>
        <div className="sx-price">
          <article className="sx-card sx-plan">
            <header>
              <h3>Hourly shifts</h3>
              <p>Same-day and short shifts</p>
            </header>
            <ul className="sx-ledger">
              <li>
                <span>Post & confirm with Jyoti</span>
                <b>₹0</b>
              </li>
              <li>
                <span>Booking fee, only after a worker accepts</span>
                <b>₹99</b>
              </li>
              <li>
                <span>Worker’s fare — you pay them directly after the work, cash or UPI</span>
                <b className="muted">Your rate</b>
              </li>
            </ul>
            <p className="sx-plan-note">
              Switch takes no cut of the fare. First booking: <b>10% off, up to ₹100.</b>
            </p>
            <a className="sx-btn" href={APP_URL} target="_blank" rel="noreferrer">
              Book a shift <Icon name="arrow" />
            </a>
          </article>
          <article className="sx-card sx-plan">
            <header>
              <h3>Full-time staff</h3>
              <p>Monthly salary, your duty hours</p>
            </header>
            <ul className="sx-ledger">
              <li>
                <span>When a worker confirms</span>
                <b>₹1,000</b>
              </li>
              <li>
                <span>When they show up on joining day</span>
                <b>₹1,000</b>
              </li>
              <li>
                <span>Didn’t show up? No second fee — Jyoti finds a replacement</span>
                <b className="ok">₹0</b>
              </li>
            </ul>
            <p className="sx-plan-note">
              Tell Jyoti the role, monthly salary (each role has a minimum), duty hours, food/stay and
              joining date.
            </p>
            <a className="sx-btn ghost" href={APP_URL} target="_blank" rel="noreferrer">
              Hire full-time
            </a>
          </article>
        </div>
        <CostCalc />
      </div>
    </section>
  )
}

function Network() {
  return (
    <section className="sx-sec sx-net" id="network" aria-labelledby="sx-net-h">
      <div className="sx-wrap sx-net-in">
        <div className="sx-net-copy">
          <p className="sx-eyebrow">The best workers aren’t online</p>
          <h2 id="sx-net-h" className="sx-h2">
            See for yourself how Jyoti searches the offline world<span className="sx-dot">.</span>
          </h2>
          <p className="sx-lead">
            Gurugram’s cooks, helpers and housekeepers aren’t scrolling job portals — they answer their
            phone. The moment you confirm, Jyoti alerts the ones nearby with an app ring and WhatsApp, and
            you watch each go from ringing to seen to yes.
          </p>
          <ul className="sx-ticks">
            <li>
              <Icon name="check" /> Nearest workers first
            </li>
            <li>
              <Icon name="check" /> Pay a little more, get a yes sooner
            </li>
            <li>
              <Icon name="check" /> ₹0 until someone accepts
            </li>
          </ul>
          <div className="sx-net-stats">
            <div>
              <b>20,000+</b>
              <span>workers on Switch</span>
            </div>
            <div>
              <b>1,500+</b>
              <span>Gurugram businesses</span>
            </div>
          </div>
        </div>
        <div className="sx-net-viz">
          <Radar />
          <p className="sx-cap">Illustration — names and positions are examples.</p>
        </div>
      </div>
    </section>
  )
}

function Languages() {
  const row = [...LANG_LINES, ...LANG_LINES]
  return (
    <section className="sx-langs" aria-labelledby="sx-l-h">
      <div className="sx-wrap">
        <h2 id="sx-l-h" className="sx-langs-h">
          <span lang="hi">हिंदी</span> · <span>Hinglish</span> · <span>English</span> · <span lang="te">తెలుగు</span>
        </h2>
        <p className="sx-langs-sub">No language screen. Jyoti answers in whatever language you talk in.</p>
      </div>
      <div className="sx-marquee" aria-hidden="true">
        <div className="sx-track">
          {row.map((x, i) => (
            <span key={i} className={`sx-chip l-${x.l}`} lang={x.l === 'hl' ? 'hi-Latn' : x.l}>
              {x.t}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

function Trust() {
  return (
    <section className="sx-sec" id="trust" aria-labelledby="sx-t-h">
      <div className="sx-wrap">
        <p className="sx-eyebrow">Safe on both sides</p>
        <h2 id="sx-t-h" className="sx-h2">
          Built for trust, from the first hello<span className="sx-dot">.</span>
        </h2>
        <div className="tb">
          <figure className="tb-photo">
            <img src="/img/sw-maid.webp" alt="Two Switch housekeeping workers in uniform" loading="lazy" width="820" height="820" />
            <figcaption>
              <b>Verified before the first job</b>
              <span>Every worker is verified before they can accept work.</span>
            </figcaption>
          </figure>
          <div className="tb-card tb-otp">
            <small>Start OTP</small>
            <div className="tb-digits" aria-label="Example OTP 4 7 1 9">
              {'4719'.split('').map((d, k) => (
                <span key={k}>{d}</span>
              ))}
            </div>
            <p>The job starts only when you share this code — then the timer runs.</p>
          </div>
          <div className="tb-card tb-track">
            <div className="tb-route" aria-hidden="true">
              <span className="dot a" />
              <span className="line" />
              <span className="dot b" />
            </div>
            <b>Live tracking</b>
            <p>See the worker on the way to your door.</p>
          </div>
          <div className="tb-card tb-rate">
            <span className="tb-stars" aria-hidden="true">
              ★★★★★
            </span>
            <b>Ratings both ways</b>
            <p>You rate the worker, the worker rates you. Good work rises.</p>
          </div>
          <div className="tb-card tb-inv">
            <div className="tb-wa" aria-hidden="true">
              <small>WhatsApp · Switch</small>
              <span>Invoice · Cook · 4 hrs</span>
              <b>Booking fee ₹99 ✓</b>
            </div>
            <b>Invoice on WhatsApp</b>
            <p>A clean invoice for every booking.</p>
          </div>
          <a className="tb-card tb-call" href={`tel:${PHONE}`}>
            <span className="sx-ti" aria-hidden="true">
              <Icon name="phone" />
            </span>
            <b>A real person to call</b>
            <p>
              Support on <u>87968 94500</u> whenever something isn’t right.
            </p>
          </a>
        </div>
      </div>
    </section>
  )
}

/* Closing band: app QR codes for desktop visitors, buttons on phones. */
function FinalCta() {
  return (
    <section className="fc" aria-labelledby="fc-h">
      <div className="sx-wrap fc-in">
        <div>
          <h2 id="fc-h" className="sx-h2">
            Staff chahiye? Bas boliye<span className="sx-dot">.</span>
          </h2>
          <p className="sx-lead">
            Download the Switch app and tell Jyoti what you need. ₹0 to post — ₹99 only when someone says yes.
          </p>
          <div className="sx-btns">
            <a className="sx-btn" href={APP_URL} target="_blank" rel="noreferrer">
              Book staff <Icon name="arrow" />
            </a>
            <a
              className="sx-btn ghost"
              href={WHATSAPP_URL}
              target="_blank"
              rel="noreferrer"
              onClick={() => trackWhatsApp('Home final')}
            >
              WhatsApp us
            </a>
          </div>
        </div>
        <div className="fc-qr" aria-label="Scan to download the Switch app">
          <a href={PLAY_URL} target="_blank" rel="noreferrer">
            <img src="/qr-android.svg" alt="QR code: Switch on Google Play" width="132" height="132" loading="lazy" />
            <span>Android</span>
          </a>
          <a href={APPLE_URL} target="_blank" rel="noreferrer">
            <img src="/qr-iphone.svg" alt="QR code: Switch on the App Store" width="132" height="132" loading="lazy" />
            <span>iPhone</span>
          </a>
        </div>
      </div>
    </section>
  )
}

function Faq() {
  return (
    <section className="sx-sec" id="faq" aria-labelledby="sx-f-h">
      <div className="sx-wrap sx-faq-in">
        <div>
          <p className="sx-eyebrow">FAQ</p>
          <h2 id="sx-f-h" className="sx-h2">
            Questions, answered<span className="sx-dot">.</span>
          </h2>
          <p className="sx-lead">
            Still unsure?{' '}
            <a
              className="sx-link"
              href={WHATSAPP_URL}
              target="_blank"
              rel="noreferrer"
              onClick={() => trackWhatsApp('Home FAQ')}
            >
              Message us on WhatsApp
            </a>
            .
          </p>
        </div>
        <div className="sx-faq">
          {FAQS.map((f) => (
            <details key={f.q}>
              <summary>
                {f.q}
                <span aria-hidden="true" />
              </summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

/* Phones: a slim bar pinned to the bottom once the hero scrolls away, hidden
   again from the closing call-to-action down. */
function MobileBar() {
  const [show, setShow] = useState(false)
  useEffect(() => {
    const hero = document.getElementById('top')
    const end = document.querySelector('.fc')
    if (!hero || !('IntersectionObserver' in window)) return
    let heroOut = false
    let endIn = false
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.target === hero) heroOut = !e.isIntersecting
        if (e.target === end) endIn = e.isIntersecting || e.boundingClientRect.top < 0
      }
      setShow(heroOut && !endIn)
    })
    io.observe(hero)
    if (end) io.observe(end)
    return () => io.disconnect()
  }, [])
  return (
    <div className={`sx-mbar${show ? ' on' : ''}`} aria-hidden={!show}>
      <div>
        <b>Staff chahiye?</b>
        <small>₹0 to post · ₹99 after a yes</small>
      </div>
      <a
        className="sx-mbar-wa"
        href={WHATSAPP_URL}
        target="_blank"
        rel="noreferrer"
        tabIndex={show ? undefined : -1}
        onClick={() => trackWhatsApp('Home mobile bar')}
      >
        <Icon name="msg" />
        <span className="sx-sr">WhatsApp us</span>
      </a>
      <a className="sx-btn sm" href={APP_URL} target="_blank" rel="noreferrer" tabIndex={show ? undefined : -1}>
        Book staff
      </a>
    </div>
  )
}

export default function SwitchHome() {
  return (
    <div className="sx">
      <a className="skip-link" href="#sx-main">
        Skip to main content
      </a>
      <SxHeader
        links={[
          ['#how', 'How it works'],
          ['#pricing', 'Pricing'],
          ['#reviews', 'Reviews'],
          ['/work', 'Find work'],
        ]}
      />
      <main id="sx-main">
        <Hero />
        <Brands />
        <How />
        <Pricing />
        <Network />
        <Reviews />
        <Languages />
        <Trust />
        <Faq />
        <FinalCta />
      </main>
      <Footer cta={false} />
      <MobileBar />
    </div>
  )
}
