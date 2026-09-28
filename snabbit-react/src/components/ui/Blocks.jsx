/* Shared building blocks of the redesign. Home and the inner pages compose
   their sections from these, so a trial ticket or a review video looks the
   same everywhere. Styles live in src/styles/switch.css (sw-* classes). */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon.jsx'
import {
  BRANDS,
  REVIEW_VIDEOS,
  TRIALS,
  TRIAL_INCLUDES,
  ALL_ROLES_MARQUEE,
} from '../../data/homeContent.js'
import { APPLE_URL, EMPLOYER_LOGIN, PLAY_URL, waLink } from '../../data/site.js'

/* Time left until midnight IST — the trial offer is daily and renews each day,
   the same clock the employer app shows. */
function untilIstMidnight() {
  const IST = 5.5 * 3_600_000
  const ist = Date.now() + IST
  const next = Math.floor(ist / 86_400_000 + 1) * 86_400_000
  const s = Math.max(0, Math.floor((next - ist) / 1000))
  return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60]
    .map((n) => String(n).padStart(2, '0'))
    .join(':')
}

export function TrialTickets({ id = 'trial' }) {
  // Empty on the server so prerendered HTML never ships a stale time.
  const [left, setLeft] = useState('--:--:--')
  useEffect(() => {
    const tick = () => setLeft(untilIstMidnight())
    tick()
    const t = setInterval(tick, 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <section className="sw-sec" id={id} style={{ paddingBottom: 0 }}>
      <div className="sw-trial">
        <div className="sw-trial-top">
          <div>
            <p className="sw-eyebrow">3-hour trial · today’s offer</p>
            <h2>
              Try Switch for <em>3 hours.</em>
              <br />
              Decide after.
            </h2>
          </div>
          <div className="sw-clock">
            <Icon name="timer" />
            <span>Offer resets in</span>
            <b>{left}</b>
          </div>
        </div>
        <div className="sw-tickets">
          {TRIALS.map((t) => (
            <div className="sw-ticket" key={t.role}>
              <div className="sw-ticket-in">
                <div className="t-head">
                  <div>
                    <span className="t-kicker">
                      <Icon name="sparkles" />
                      {t.kicker}
                    </span>
                    <h3 className="t-role">{t.role}</h3>
                    <p className="t-blurb">{t.blurb}</p>
                    <div className="t-price">
                      <b>₹{t.price}</b>
                      <span>
                        for 3 hours
                        <br />1 worker
                      </span>
                    </div>
                  </div>
                  <div className="t-art" aria-hidden="true">
                    <div className="sw-blob" />
                    <div className="sw-arch">
                      <img src={t.img} alt="" loading="lazy" />
                    </div>
                  </div>
                </div>
                <div className="t-perf" aria-hidden="true">
                  <i />
                  <i />
                </div>
                <div className="t-foot">
                  <ul className="t-list">
                    {TRIAL_INCLUDES.map((x) => (
                      <li key={x}>
                        <Icon name="check" />
                        {x}
                      </li>
                    ))}
                  </ul>
                  <div className="t-cta">
                    <a className="sw-btn" href={t.book} target="_blank" rel="noreferrer">
                      Book {t.role} · ₹{t.price} <Icon name="arrow" />
                    </a>
                    <a
                      className="sw-btn ghost"
                      href={waLink(`Hi Switch — I want the 3-hour ${t.role} trial (₹${t.price}).`)}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`Ask about the ${t.role} trial on WhatsApp`}
                    >
                      WhatsApp
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
        <p className="t-note">
          Starts from 7 AM, at least 90 minutes after booking · Booking opens the Switch app’s
          payment page
        </p>
      </div>
    </section>
  )
}

export function BrandBand({ title = true }) {
  return (
    <section className="sw-sec" style={{ paddingBlock: '34px 6px' }} aria-label="Businesses we staff">
      {title && (
        <div className="sw-row-head">
          <div>
            <p className="sw-eyebrow">Businesses we staff</p>
            <h2 className="sw-h2" style={{ marginTop: 8 }}>
              Trusted by <em>1,500+</em> Gurgaon businesses.
            </h2>
          </div>
        </div>
      )}
      <div className="sw-logos">
        {BRANDS.map((b) => (
          <div className={`sw-logo${b.light ? ' is-light' : ''}`} key={b.name} title={b.name}>
            {b.logo ? <img src={b.logo} alt={b.name} loading="lazy" /> : <span>{b.name}</span>}
          </div>
        ))}
      </div>
    </section>
  )
}

export function ReviewVideos() {
  const [open, setOpen] = useState(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && setOpen(null)
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])
  return (
    <>
      <div className="sw-vids">
        {REVIEW_VIDEOS.map((r) => (
          <button
            type="button"
            className="sw-vcard"
            key={r.src}
            onClick={() => setOpen(r)}
            aria-label={`Play review from ${r.who}, ${r.len}`}
          >
            <img src={r.poster} alt="" loading="lazy" />
            <span className="sw-vlen">{r.len}</span>
            <span className="sw-vplay">
              <Icon name="play" />
            </span>
            <span className="sw-vmeta">
              <span className="sw-pill sw-live">Employer review</span>
              <b>{r.who}</b>
              <span>{r.where}</span>
              <small>{r.line}</small>
            </span>
          </button>
        ))}
      </div>
      {open && (
        <div className="sw-vm" onClick={() => setOpen(null)}>
          <div
            className="sw-vm-in"
            role="dialog"
            aria-modal="true"
            aria-label={`Review from ${open.who}`}
            onClick={(e) => e.stopPropagation()}
          >
            <button type="button" className="sw-vm-x" onClick={() => setOpen(null)} aria-label="Close video">
              ✕
            </button>
            <video src={open.src} poster={open.poster} controls autoPlay playsInline />
          </div>
        </div>
      )}
    </>
  )
}

export function Ticker() {
  const row = ALL_ROLES_MARQUEE.concat(['Waiter', 'Kitchen Helper', 'Bartender', 'Loader'])
  return (
    <div className="sw-ticker" aria-hidden="true">
      <div className="sw-ticker-row">
        {[...row, ...row].map((x, i) => (
          <span key={i} style={{ display: 'contents' }}>
            <span>{x}</span>
            <i>✦</i>
          </span>
        ))}
      </div>
    </div>
  )
}

export function Faq({ items }) {
  return (
    <div className="sw-faq">
      {items.map((f) => (
        <details className="sw-card" key={f.q}>
          <summary>
            {f.q}
            <span className="pm">+</span>
          </summary>
          <p>{f.a}</p>
        </details>
      ))}
    </div>
  )
}

export function StoreButtons() {
  return (
    <>
      <a className="sw-store" href={PLAY_URL} target="_blank" rel="noreferrer">
        <Icon name="play" />
        <span>
          <small>GET IT ON</small>
          <b>Google Play</b>
        </span>
      </a>
      <a className="sw-store" href={APPLE_URL} target="_blank" rel="noreferrer">
        <Icon name="phone" />
        <span>
          <small>Download on the</small>
          <b>App Store</b>
        </span>
      </a>
    </>
  )
}

/* Closing call-to-action card: dark in both themes, two arched staff photos. */
export function CtaFeature({
  title = (
    <>
      Staff your business <em>today.</em>
    </>
  ),
  sub = 'Aadhaar-verified people, replacement guaranteed, clear invoices.',
  msg = "Hi Switch — I'd like to hire staff for my business in Gurgaon.",
  photos = ['/sw-general-helper.jpg', '/sw-security-guard.jpg'],
}) {
  return (
    <section className="sw-sec">
      <div className="sw-feature sw-feature-grid">
        <div>
          <p className="sw-eyebrow">Ready when you are</p>
          <h2 style={{ marginTop: 10 }}>{title}</h2>
          <p style={{ marginTop: 10, maxWidth: '46ch' }}>{sub}</p>
          <div className="sw-btns" style={{ marginTop: 18 }}>
            <a className="sw-btn white" href={waLink(msg)} target="_blank" rel="noreferrer">
              Hire on WhatsApp <Icon name="arrow" />
            </a>
            <a className="sw-btn line" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
              Open the Switch app
            </a>
          </div>
        </div>
        <div className="sw-f-art" aria-hidden="true">
          <div className="sw-blob" />
          <div className="sw-arch a1">
            <img src={photos[0]} alt="" loading="lazy" />
          </div>
          <div className="sw-arch a2">
            <img src={photos[1]} alt="" loading="lazy" />
          </div>
        </div>
      </div>
    </section>
  )
}

export function Crumbs({ items }) {
  return (
    <nav className="sw-crumbs" aria-label="Breadcrumb">
      <Link to="/">Home</Link>
      {items.map(([label, to]) => (
        <span key={label}>
          {' / '}
          {to ? <Link to={to}>{label}</Link> : <span>{label}</span>}
        </span>
      ))}
    </nav>
  )
}

export function StatsRow({ items }) {
  return (
    <div className="sw-grid sw-g4">
      {items.map((s) => (
        <div className="sw-card sw-stat" key={s.label}>
          <b>{s.value}</b>
          <span>{s.label}</span>
        </div>
      ))}
    </div>
  )
}

/* Photo-in-arch hero art with optional floating cards. */
export function HeroArt({ img, alt = '', otp = false, badge }) {
  return (
    <div className="sw-art" aria-hidden={alt ? undefined : 'true'}>
      <div className="sw-blob" />
      <div className="sw-arch">
        <img src={img} alt={alt} fetchPriority="high" />
      </div>
      {badge && (
        <div className="sw-float sw-f-ok">
          <span className="dot">
            <Icon name={badge.icon || 'check'} />
          </span>
          <div>
            <b>{badge.title}</b>
            <span>{badge.sub}</span>
          </div>
        </div>
      )}
      {otp && (
        <div className="sw-float sw-f-otp">
          <small>Share this code on arrival</small>
          <div className="sw-otp">4719</div>
        </div>
      )}
    </div>
  )
}

export function ServiceRow({ to, img, name, desc, tags = [], badge }) {
  return (
    <Link className="sw-card sw-svc sw-press" to={to}>
      <div className="sw-thumb">
        <img src={img} alt={name} loading="lazy" />
        {badge && (
          <span
            style={{
              position: 'absolute',
              left: 6,
              top: 6,
              borderRadius: 999,
              background: 'var(--p)',
              color: '#fff',
              fontSize: 11,
              fontWeight: 800,
              padding: '3px 8px',
            }}
          >
            {badge}
          </span>
        )}
      </div>
      <div>
        <h3>{name}</h3>
        <p>{desc}</p>
        {tags.length > 0 && (
          <div className="tags">
            {tags.map((t) => (
              <span className="sw-tag" key={t}>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
      <span className="sw-go">
        <Icon name="arrow" />
      </span>
    </Link>
  )
}
