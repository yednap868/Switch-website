import { Link } from 'react-router-dom'
import Annotate from '../fx/Annotate.jsx'
import { ROLES } from '../../data/homeContent.js'
import { EMPLOYER_LOGIN, WHATSAPP_URL } from '../../data/site.js'

export default function Hero() {
  return (
    <>
      <div className="shell hero">
        <div className="hero-copy">
          <div className="eyebrow hero-kicker">GURGAON&apos;S STAFFING PARTNER</div>
          <h1>
            <span className="hero-line">Staff your</span>{' '}
            <span className="hero-line">
              <em>business</em> with
            </span>{' '}
            <span className="hero-line">Switch Players</span>{' '}
            <span className="hero-line">who show up.</span>
          </h1>
          <p>
            Aadhaar-verified staff, matched to your business often within the day — cooks, helpers,
            guards, waiters &amp; more for shops, restaurants, warehouses and offices across
            Gurgaon. Replacement guaranteed. No advance, no agency runaround.
          </p>
          <div className="hero-actions">
            <a className="btn primary" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
              Hire staff now ↗
            </a>
            <a className="btn ghost" href={WHATSAPP_URL} target="_blank" rel="noreferrer">
              Talk on WhatsApp
            </a>
          </div>
          <div className="hero-note">
            <strong>01</strong>
            <span>
              Book hourly, daily, weekly or monthly staff.{' '}
              <Annotate kind="circle">Pay on arrival</Annotate> for on-demand shifts.
            </span>
          </div>
        </div>

        <div className="hero-media">
          <div className="hero-ambient" />
          <img
            src="/hero-workers.jpg"
            alt="Switch verified blue-collar professionals — cooks, drivers, cleaners, security guards in Gurgaon"
            width="1000"
            height="789"
            fetchPriority="high"
            decoding="async"
          />
          <div className="image-tag">
            <span className="mono">FIELD NOTE / 001</span> Built for business in Gurgaon.
          </div>
          <div className="hero-corner mono">GURGAON / 122001—122022</div>
        </div>
      </div>

      <div className="hero-bottom shell">
        <div className="hero-services">
          <span className="mono hero-services-label">FIND YOUR PEOPLE</span>
          {ROLES.map((role) => (
            <Link className="hero-service" to={`/${role.slug}`} key={role.slug}>
              <img src={role.img} alt="" loading="lazy" />
              <span>{role.name}</span>
              <b>↗</b>
            </Link>
          ))}
          <a className="hero-service hero-service-all" href="#services">
            <span>All services</span>
            <b>→</b>
          </a>
        </div>
      </div>
    </>
  )
}
