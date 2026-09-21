import { Link } from 'react-router-dom'
import ParticleWordmark from '../fx/ParticleWordmark.jsx'
import { SERVICE_LIST } from '../../data/seoData.js'
import {
  ADDRESS,
  APPLE_URL,
  CALL_URL,
  CAREERS_EMAIL,
  MAPS_URL,
  PHONE_DISPLAY,
  PLAY_URL,
  REGISTERED_OFFICE,
  SOCIALS,
  waLink,
} from '../../data/site.js'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-banner">
        <div className="footer-banner-art">
          <img
            src="/switch-banner.jpg"
            alt="Switch — instant staffing with verified professionals in Gurgaon"
            width="1440"
            height="791"
            loading="lazy"
          />
          <a
            className="footer-store-hotspot footer-store-play"
            href={PLAY_URL}
            target="_blank"
            rel="noreferrer"
            aria-label="Get Switch on Google Play"
          />
          <a
            className="footer-store-hotspot footer-store-app"
            href={APPLE_URL}
            target="_blank"
            rel="noreferrer"
            aria-label="Download Switch on the App Store"
          />
        </div>
      </div>

      <div className="shell footer-main">
        <div className="footer-brand">
          <Link className="footer-particle-link" to="/" aria-label="Switch home">
            <ParticleWordmark
              className="footer-switch-particle"
              text="SWITCH"
              color="#f5f7f4"
              fontSize={80}
            />
          </Link>
          <p>
            Gurgaon&apos;s staffing partner for shops, restaurants, warehouses, offices and events —
            verified Switch Players, fast, flexible and replacement-guaranteed.
          </p>
          <div className="footer-address">
            {ADDRESS.map((line) => (
              <span key={line}>{line}</span>
            ))}
            <a href={MAPS_URL} target="_blank" rel="noreferrer">
              View on Google Maps →
            </a>
          </div>
          <a className="footer-phone" href={CALL_URL}>
            <span aria-hidden="true">☎</span>
            <span>
              <small>Call us</small>
              <b>{PHONE_DISPLAY}</b>
            </span>
          </a>
          <div className="footer-socials" aria-label="Switch social media">
            {SOCIALS.map((s) => (
              <a
                key={s.label}
                href={s.href}
                target="_blank"
                rel="noreferrer"
                aria-label={`Switch on ${s.name}`}
              >
                {s.label}
              </a>
            ))}
          </div>
        </div>

        <div className="footer-columns">
          <div className="footer-column">
            <span className="footer-column-title">FOR BUSINESS</span>
            <Link to="/staffing-gurgaon">Staffing in Gurgaon</Link>
            <a href="/#industries">Industries</a>
            <a href={waLink('Hi Switch — I need a bulk staffing quote.')} target="_blank" rel="noreferrer">
              Bulk hiring
            </a>
            <a href="/#request">Request staff</a>
            <a href={CALL_URL}>Contact sales</a>
          </div>
          <div className="footer-column">
            <span className="footer-column-title">COMPANY</span>
            <Link to="/about">About us</Link>
            <Link to="/blog">Blog</Link>
            <a href={`mailto:${CAREERS_EMAIL}`}>Careers</a>
            <Link to="/partner">Become a Switch Player</Link>
          </div>
          <div className="footer-column">
            <span className="footer-column-title">LEGAL</span>
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/privacy">Privacy policy</Link>
            <Link to="/cancellation">Cancellation policy</Link>
          </div>
        </div>
      </div>

      {/* Site-wide service links — these carry the internal linking the nav
          dropdown used to provide. The homepage additionally renders the full
          directory of every generated page. */}
      <div className="shell">
        <div className="footer-directory">
          <span className="mono">HIRE IN GURGAON</span>
          {SERVICE_LIST.map((svc) => (
            <Link key={svc.slug} to={`/${svc.slug}`}>
              {svc.name}
            </Link>
          ))}
        </div>
      </div>

      <div className="shell footer-bottom">
        <div>
          <span>© {new Date().getFullYear()} Third Wave Labs Private Limited. All rights reserved.</span>
          <span>{REGISTERED_OFFICE}</span>
        </div>
        <span>Made in India 🇮🇳</span>
      </div>
    </footer>
  )
}
