/* switchlocally.com — the homepage for the new Switch app: one chat with
   Jyoti. Mobile-first (390px), off-white with one green accent, serif
   headings. Own header and footer so the page reads as one piece; the rest of
   the site keeps its shared chrome. Styles: ./sx.css (prefix sx-). */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import PhoneChat from './PhoneChat.jsx'
import Radar from './Radar.jsx'
import { APP_URL, APPLE_URL, EMAIL, PHONE, PLAY_URL, SOCIALS, WHATSAPP_URL, trackWhatsApp } from '../../data/site.js'
import { FAQS, LANG_LINES, STEPS, TRUST, WORKER_APP_URL } from '../../data/switchHome.js'
import './sx.css'

/* Theme: light by default here; follows the system until someone toggles,
   and remembers the choice under the same key as the rest of the site. */
function useTheme() {
  const [theme, setTheme] = useState(null)
  useEffect(() => {
    const t = document.documentElement.dataset.theme
    const sys = window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    const id = setTimeout(() => setTheme(t || sys), 0)
    return () => clearTimeout(id)
  }, [])
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem('switch-theme', next)
    } catch {
      /* private mode — the choice just won't stick */
    }
    setTheme(next)
  }
  return [theme, toggle]
}

function SxHeader() {
  const [theme, toggle] = useTheme()
  const [open, setOpen] = useState(false)
  const links = [
    ['#how', 'How it works'],
    ['#pricing', 'Pricing'],
    ['#workers', 'For workers'],
    ['#faq', 'FAQ'],
  ]
  return (
    <header className="sx-head">
      <div className="sx-wrap sx-head-in">
        <a href="#top" className="sx-logo" aria-label="Switch home">
          Switch<span>.</span>
        </a>
        <nav className={`sx-nav${open ? ' open' : ''}`} aria-label="Main">
          {links.map(([h, l]) => (
            <a key={h} href={h} onClick={() => setOpen(false)}>
              {l}
            </a>
          ))}
        </nav>
        <div className="sx-head-cta">
          <button type="button" className="sx-icon-btn" onClick={toggle} aria-label="Switch light or dark mode">
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          </button>
          <a className="sx-btn sm" href={APP_URL} target="_blank" rel="noreferrer">
            Book staff
          </a>
          <button
            type="button"
            className="sx-icon-btn sx-menu"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label="Menu"
          >
            <Icon name={open ? 'x' : 'menu'} />
          </button>
        </div>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="sx-hero" id="top">
      <div className="sx-wrap sx-hero-in">
        <div className="sx-hero-copy">
          <p className="sx-kicker">
            <span className="sx-live-dot" aria-hidden="true" /> Gurugram · one chat with Jyoti
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
            <a className="sx-btn ghost" href="#workers">
              Find work
            </a>
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
          <PhoneChat />
          <p className="sx-cap">Try it — tap your answers. A preview of the Switch app.</p>
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
        <ol className="sx-steps">
          {STEPS.map((s) => (
            <li key={s.n} className="sx-card">
              <span className="sx-n">{s.n}</span>
              <h3>{s.t}</h3>
              <p>{s.d}</p>
            </li>
          ))}
        </ol>
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
      </div>
    </section>
  )
}

function Network() {
  return (
    <section className="sx-sec sx-net" id="network" aria-labelledby="sx-net-h">
      <div className="sx-wrap sx-net-in">
        <div>
          <p className="sx-eyebrow">Live, around you</p>
          <h2 id="sx-net-h" className="sx-h2">
            Watch your shift reach the neighbourhood<span className="sx-dot">.</span>
          </h2>
          <p className="sx-lead">
            The moment you confirm, Jyoti alerts nearby workers — an app ring like a ride request, plus
            WhatsApp. You see each one go from ringing to seen to yes.
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
        </div>
        <div>
          <Radar />
          <p className="sx-cap">Illustration — positions aren’t real workers.</p>
        </div>
      </div>
    </section>
  )
}

function Workers() {
  return (
    <section className="sx-sec sx-workers" id="workers" aria-labelledby="sx-w-h" lang="hi">
      <div className="sx-wrap sx-workers-in">
        <div>
          <p className="sx-eyebrow">काम ढूँढ रहे हैं?</p>
          <h2 id="sx-w-h" className="sx-h2 deva">
            आज फ्री हो? Jyoti को बोलो<span className="sx-dot">।</span>
          </h2>
          <p className="sx-lead deva-sans">
            बस बोलिए “आज फ्री हूँ, काम चाहिए”। Jyoti पूछेगी आप कौन सा काम करते हैं, कब तक फ्री हैं और कितनी
            दूर जा सकते हैं — फिर आपके पास का काम ढूँढेगी।
          </p>
          <ul className="sx-wlist deva-sans">
            <li>
              <b>नया काम आते ही फ़ोन बजेगा</b> — ride app की तरह, एक टैप में accept
            </li>
            <li>
              <b>पूरा 100% किराया आपका</b> — काम के बाद मालिक सीधे आपको देंगे, cash या UPI
            </li>
            <li>
              <b>Full-time नौकरी भी</b> — salary, खाना और रहने की सुविधा वाली; interview Jyoti बुक करेगी
            </li>
          </ul>
          <a className="sx-btn" href={WORKER_APP_URL} target="_blank" rel="noreferrer" lang="en">
            Download app <Icon name="arrow" />
          </a>
        </div>
        <div className="sx-ringcard" aria-hidden="true">
          <div className="sx-ring-top">
            <span className="sx-ring-ico">
              <Icon name="phone" />
            </span>
            <div>
              <small>Switch · अभी</small>
              <b>नया काम — Kitchen helper</b>
            </div>
          </div>
          <dl>
            <div>
              <dt>दूरी</dt>
              <dd>1.2 km</dd>
            </div>
            <div>
              <dt>समय</dt>
              <dd>आज 3 PM · 4 घंटे</dd>
            </div>
            <div>
              <dt>किराया</dt>
              <dd>सीधे आपको</dd>
            </div>
          </dl>
          <div className="sx-ring-btns">
            <span className="no">छोड़ें</span>
            <span className="yes">Accept</span>
          </div>
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
        <div className="sx-trust">
          {TRUST.map((x) => (
            <div key={x.t} className="sx-card sx-trust-i">
              <span className="sx-ti" aria-hidden="true">
                <Icon name={x.i} />
              </span>
              <h3>{x.t}</h3>
              <p>{x.d}</p>
            </div>
          ))}
        </div>
        <a className="sx-support" href={`tel:${PHONE}`}>
          <Icon name="phone" /> Support: <b>87968 94500</b>
        </a>
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

function SxFooter() {
  return (
    <footer className="sx-foot">
      <div className="sx-wrap">
        <div className="sx-foot-cta">
          <h2 className="sx-h2">
            Staff chahiye? Bas boliye<span className="sx-dot">.</span>
          </h2>
          <div className="sx-btns">
            <a className="sx-btn" href={APP_URL} target="_blank" rel="noreferrer">
              Book staff <Icon name="arrow" />
            </a>
            <a className="sx-btn ghost" href={WORKER_APP_URL} target="_blank" rel="noreferrer">
              Find work
            </a>
          </div>
        </div>
        <div className="sx-foot-grid">
          <div>
            <a href="#top" className="sx-logo">
              Switch<span>.</span>
            </a>
            <p>One chat with Jyoti to book staff or find work in Gurugram.</p>
            <p>
              <a href={`tel:${PHONE}`}>+91 87968 94500</a>
              <br />
              <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
            </p>
          </div>
          <nav aria-label="Switch">
            <b>Switch</b>
            <Link to="/about">About</Link>
            <Link to="/staffing-gurgaon">Services</Link>
            <Link to="/blog">Blog</Link>
            <Link to="/partner">Partner with us</Link>
            <Link to="/verify">Verify a certificate</Link>
          </nav>
          <nav aria-label="Apps">
            <b>Apps</b>
            <a href={PLAY_URL} target="_blank" rel="noreferrer">
              Employer app · Android
            </a>
            <a href={APPLE_URL} target="_blank" rel="noreferrer">
              Employer app · iPhone
            </a>
            <a href={WORKER_APP_URL} target="_blank" rel="noreferrer">
              Worker app · Android
            </a>
          </nav>
          <nav aria-label="Legal">
            <b>Legal</b>
            <Link to="/terms">Terms</Link>
            <Link to="/privacy">Privacy</Link>
            <Link to="/cancellation">Cancellation</Link>
          </nav>
        </div>
        <div className="sx-foot-base">
          <span>© {new Date().getFullYear()} Third Wave Labs Private Limited · Gurugram</span>
          <span className="sx-social">
            {SOCIALS.map((s) => (
              <a key={s.name} href={s.href} target="_blank" rel="noreferrer" aria-label={s.name}>
                {s.label}
              </a>
            ))}
          </span>
        </div>
      </div>
    </footer>
  )
}

export default function SwitchHome() {
  return (
    <div className="sx">
      <a className="skip-link" href="#sx-main">
        Skip to main content
      </a>
      <SxHeader />
      <main id="sx-main">
        <Hero />
        <How />
        <Pricing />
        <Network />
        <Workers />
        <Languages />
        <Trust />
        <Faq />
      </main>
      <SxFooter />
    </div>
  )
}
