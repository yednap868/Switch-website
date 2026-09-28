import { Link } from 'react-router-dom'
import { StoreButtons } from '../ui/Blocks.jsx'
import { SERVICE_LIST } from '../../data/seoData.js'
import { INDUSTRY_PAGES } from '../../data/industryPages.js'
import { TAGLINE } from '../../data/homeContent.js'
import {
  ADDRESS,
  CAREERS_EMAIL,
  EMAIL,
  MAPS_URL,
  PHONE_DISPLAY,
  REGISTERED_OFFICE,
  SOCIALS,
  WHATSAPP_URL,
  waLink,
} from '../../data/site.js'

export default function Footer() {
  return (
    <footer className="sw-footer">
      <div className="sw-wrap">
        <div className="sw-fgrid">
          <div>
            <Link to="/" className="sw-logo-link sw-logo-lg" aria-label="Switch home">
              <span className="sw-mark" aria-hidden="true">
                S
              </span>
              <span className="sw-brand">
              <img className="wm-dark" src="/brand/switch-wordmark-white.png" alt="Switch" width="180" height="48" style={{ height: 48 }} loading="lazy" />
              <img className="wm-light" src="/brand/switch-wordmark-black.png" alt="" width="180" height="48" style={{ height: 48 }} loading="lazy" />
              </span>
            </Link>
            <p className="sw-tagline">{TAGLINE}</p>
            <p className="sw-muted" style={{ marginTop: 8, fontSize: 14, maxWidth: '40ch' }}>
              Gurgaon&apos;s staffing partner for shops, restaurants, warehouses, offices and events —
              verified Switch Players, replacement-guaranteed.
            </p>
            <a href={WHATSAPP_URL} target="_blank" rel="noreferrer" style={{ display: 'block', marginTop: 14, fontWeight: 800 }}>
              WhatsApp {PHONE_DISPLAY}
            </a>
            <a href={`mailto:${EMAIL}`} className="sw-muted" style={{ fontSize: 14 }}>
              {EMAIL}
            </a>
            <p className="sw-muted" style={{ fontSize: 13.5, marginTop: 6 }}>
              {ADDRESS.join(', ')} ·{' '}
              <a href={MAPS_URL} target="_blank" rel="noreferrer" style={{ color: 'var(--p-t)', display: 'inline' }}>
                Map
              </a>
            </p>
            <div className="sw-btns" style={{ marginTop: 16 }}>
              <StoreButtons />
            </div>
          </div>
          <div>
            <h4>For business</h4>
            <Link to="/staffing-gurgaon">Staffing in Gurgaon</Link>
            {INDUSTRY_PAGES.map((p) => (
              <Link key={p.slug} to={`/${p.slug}`}>
                {p.name}
              </Link>
            ))}
            <a href="/#trial">₹149 3-hour trial</a>
            <a href="/#pricing">Pricing</a>
            <a href={waLink('Hi Switch — I need a bulk staffing quote.')} target="_blank" rel="noreferrer">
              Bulk hiring
            </a>
          </div>
          <div>
            <h4>Hire in Gurgaon</h4>
            {SERVICE_LIST.map((s) => (
              <Link key={s.slug} to={`/${s.slug}`}>
                {s.name}
              </Link>
            ))}
          </div>
          <div>
            <h4>Company</h4>
            <Link to="/about">About us</Link>
            <Link to="/blog">Blog</Link>
            <Link to="/app">Get the app</Link>
            <Link to="/partner">Become a Switch Player</Link>
            <a href={`mailto:${CAREERS_EMAIL}`}>Careers</a>
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/privacy">Privacy policy</Link>
            <Link to="/cancellation">Cancellation policy</Link>
            {SOCIALS.map((s) => (
              <a key={s.name} href={s.href} target="_blank" rel="noreferrer">
                {s.name}
              </a>
            ))}
          </div>
        </div>
        <div className="sw-legal">
          <span>© {new Date().getFullYear()} Third Wave Labs Private Limited. All rights reserved.</span>
          <span>{REGISTERED_OFFICE}</span>
          <span>Made in India 🇮🇳</span>
        </div>
      </div>
    </footer>
  )
}
