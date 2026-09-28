/* The homepage, section by section, in the Switch app's look. Content comes
   from src/data/homeContent.js and site.js; nothing here is invented copy. */
import AppScreens from '../ui/AppScreens.jsx'
import CoverageMap from './CoverageMap.jsx'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import { ReviewVideos, ServiceRow, StoreButtons, StatsRow } from '../ui/Blocks.jsx'
import {
  FORM_ROLES,
  HOME_STATS,
  HOW_STEPS,
  INDUSTRIES,
  PATHWAYS,
  PLANS,
  PRICES,
  REVIEWS,
  ROLES,
  WHY_US,
} from '../../data/homeContent.js'
import {
  ADDRESS,
  EMAIL,
  LEADS_SHEET_URL,
  PHONE_DISPLAY,
  trackWhatsApp,
  waLink,
} from '../../data/site.js'

const TINTS = ['t-lav', 't-peach', 't-sky', 't-mint', 't-pink', 't-grey', 't-lav', 't-peach', 't-sky']
const ROLE_ICON = {
  'store-helper-gurgaon': 'store',
  'security-guard-gurgaon': 'shield',
  'factory-warehouse-gurgaon': 'package',
  'delivery-worker-gurgaon': 'bike',
  'cook-gurgaon': 'chef',
  'home-cleaning-gurgaon': 'sparkles',
  'nanny-gurgaon': 'heart',
}
const IND_ICON = {
  'Retail & Shops': 'store',
  'Restaurants & Cafés': 'utensils',
  'Warehouses & Logistics': 'warehouse',
  'Factories & Production': 'factory',
  'Offices & Co-working': 'building',
  'Events & Banquets': 'party',
  'Hotels & Guest Houses': 'hotel',
  'Grocery & Q-Commerce': 'cart',
  'Salons, Gyms & Clinics': 'scissors',
}

export function RoleTiles() {
  return (
    <section aria-label="Find your people">
      <div className="sw-tiles">
        {ROLES.map((r, i) => (
          <Link key={r.slug} className={`sw-tile sw-press ${TINTS[i % TINTS.length]}`} to={`/${r.slug}`}>
            <Icon name={ROLE_ICON[r.slug] || 'sparkles'} />
            {r.name.split(' / ')[0]}
          </Link>
        ))}
      </div>
    </section>
  )
}

export function Services() {
  return (
    <section className="sw-sec" id="services">
      <div className="sw-row-head">
        <div className="sw-head" style={{ margin: 0 }}>
          <p className="sw-eyebrow">Our services</p>
          <h2 className="sw-h2">
            Every role your <em>floor needs.</em>
          </h2>
          <p className="sw-lead">
            Kitchens, warehouses, shop floors and front desks. One verified bench for all of them.
          </p>
        </div>
        <Link className="sw-link" to="/staffing-gurgaon">
          All services <Icon name="arrow" />
        </Link>
      </div>
      <div className="sw-grid sw-g2">
        {ROLES.map((r) => (
          <ServiceRow key={r.slug} to={`/${r.slug}`} img={r.img} name={r.name} desc={r.desc} tags={r.tags} />
        ))}
      </div>
      <div className="sw-grid sw-g3" style={{ marginTop: 12 }}>
        {WHY_US.slice(1, 4).map((p) => (
          <div className="sw-card sw-step" key={p.title}>
            <Icon name="shield" style={{ color: 'var(--p-t)' }} />
            <h3 className="sw-h3">{p.title}</h3>
            <p>{p.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export function Industries() {
  return (
    <section className="sw-sec" id="industries">
      <div className="sw-head">
        <p className="sw-eyebrow">Who we staff</p>
        <h2 className="sw-h2">
          Built for the businesses that <em>run Gurgaon.</em>
        </h2>
        <p className="sw-lead">
          From a four-table café to a warehouse on a dispatch deadline. Same verification, same
          replacement guarantee, same day.
        </p>
      </div>
      <div className="sw-grid sw-g3">
        {INDUSTRIES.map((x, i) => {
          const inner = (
            <>
              <span className={`sw-sq ${TINTS[i % TINTS.length]}`}>
                <Icon name={IND_ICON[x.name] || 'building'} />
              </span>
              <h3 className="sw-h3">{x.name}</h3>
              <p>{x.roles}</p>
              <span className="sw-link">
                {x.slug ? 'See staffing' : 'Ask on WhatsApp'} <Icon name="arrow" />
              </span>
            </>
          )
          return x.slug ? (
            <Link key={x.name} className="sw-card sw-ind sw-press" to={`/${x.slug}`}>
              {inner}
            </Link>
          ) : (
            <a
              key={x.name}
              className="sw-card sw-ind sw-press"
              href={waLink(`Hi Switch — I need staff for my ${x.name} business in Gurgaon.`)}
              target="_blank"
              rel="noreferrer"
            >
              {inner}
            </a>
          )
        })}
      </div>
    </section>
  )
}

export function How() {
  return (
    <section className="sw-sec" id="how">
      <div className="sw-head">
        <p className="sw-eyebrow">How Switch works</p>
        <h2 className="sw-h2">
          One message. <em>People on site.</em>
        </h2>
        <p className="sw-lead">
          Tell us the role, place and time. We match verified people, you confirm, they check in
          with an OTP.
        </p>
      </div>
      <div className="sw-grid sw-g4">
        {HOW_STEPS.map((s) => (
          <div className="sw-card sw-step" key={s.n}>
            <span className="n">
              {s.n} · {s.title}
            </span>
            <h3 className="sw-h3">{s.line}</h3>
            <p>{s.caption}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

export function Pricing() {
  return (
    <section className="sw-sec" id="pricing">
      <div className="sw-head">
        <p className="sw-eyebrow">Transparent rates</p>
        <h2 className="sw-h2">
          Pay for the shift. <em>Nothing hidden.</em>
        </h2>
      </div>
      <div className="sw-grid sw-g3">
        {PRICES.map((r) => (
          <div className="sw-card sw-rate" key={r.tier}>
            <p className="sw-eyebrow">{r.tier}</p>
            <b>{r.figure}</b>
            <span className="sw-muted">{r.unit}</span>
          </div>
        ))}
      </div>
      <div id="subscription" style={{ marginTop: 26 }}>
        <p className="sw-eyebrow">Subscription / monthly</p>
        <p className="sw-muted" style={{ marginTop: 4, marginBottom: 14 }}>
          For businesses that need dependable people on a regular schedule.
        </p>
        <div className="sw-grid sw-g3">
          {PLANS.map((p) => (
            <div className={`sw-card sw-plan${p.featured ? ' hl' : ''}`} key={p.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                <h3 className="sw-h3">{p.name}</h3>
                <span className="sw-pill">{p.badge}</span>
              </div>
              <div className="amt">
                {p.price}
                {p.per && <small>{p.per}</small>}
              </div>
              <p className="sw-muted" style={{ fontSize: 14 }}>
                {p.description}
              </p>
              <ul>
                {p.items.map((it) => (
                  <li key={it}>
                    <Icon name="check" />
                    {it}
                  </li>
                ))}
              </ul>
              <a className={`sw-btn sm${p.featured ? ' white' : ''}`} href={waLink(p.msg)} target="_blank" rel="noreferrer">
                {p.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
      <div className="sw-grid sw-g2" style={{ marginTop: 12 }}>
        {PATHWAYS.map((p) => (
          <a className="sw-dashed sw-press" key={p.title} href={waLink(p.msg)} target="_blank" rel="noreferrer">
            <p className="sw-eyebrow">{p.kicker}</p>
            <h3 className="sw-h3" style={{ marginTop: 6 }}>
              {p.title}
            </h3>
            <p className="sw-muted" style={{ marginTop: 4 }}>
              {p.copy}
            </p>
          </a>
        ))}
      </div>
      <p className="sw-fine">
        Monthly prices are per staff, exclusive of GST (18%), with a 1-month minimum and 15 days’
        notice to cancel. Rates depend on role, shift and location. T&amp;C apply.
      </p>
    </section>
  )
}

export function Trust() {
  return (
    <section className="sw-sec" id="trust">
      <div className="sw-head">
        <p className="sw-eyebrow">Trusted by businesses</p>
        <h2 className="sw-h2">
          Real businesses. <em>Real results.</em>
        </h2>
        <p className="sw-lead">Owners and managers across Gurgaon, on camera and in their own words.</p>
      </div>
      <StatsRow items={HOME_STATS} />
      <div style={{ marginTop: 14 }}>
        <ReviewVideos />
      </div>
      <div className="sw-grid sw-g4" style={{ marginTop: 12 }}>
        {WHY_US.filter((w, i) => i === 0 || i >= 4).map((w) => (
          <div className="sw-card sw-step" key={w.title}>
            <span className="sw-pill" style={{ justifySelf: 'start' }}>
              <Icon name="check" />
            </span>
            <h3 className="sw-h3" style={{ fontSize: 15.5 }}>
              {w.title}
            </h3>
            <p>{w.desc}</p>
          </div>
        ))}
        <Link className="sw-card sw-step sw-press" to="/about">
          <span className="sw-pill" style={{ justifySelf: 'start' }}>
            <Icon name="heart" />
          </span>
          <h3 className="sw-h3" style={{ fontSize: 15.5 }}>
            Our story
          </h3>
          <p>Why we built Switch for Gurgaon’s businesses.</p>
        </Link>
      </div>
      <div className="sw-quotes" style={{ marginTop: 18 }}>
        {REVIEWS.map((t) => (
          <figure className="sw-card sw-q" key={t.name} style={{ margin: 0 }}>
            <div className="stars" aria-label="5 stars">
              ★★★★★
            </div>
            <blockquote>“{t.text}”</blockquote>
            <cite>
              {t.name} · {t.loc}
            </cite>
          </figure>
        ))}
      </div>
    </section>
  )
}

export function Coverage() {
  return (
    <section className="sw-sec" id="coverage">
      <div className="sw-row-head">
        <div className="sw-head" style={{ margin: 0 }}>
          <p className="sw-eyebrow">Our coverage</p>
          <h2 className="sw-h2">
            Every corner of Gurgaon. <em>Same day.</em>
          </h2>
          <p className="sw-lead">
            From DLF and Sushant Lok to Palam Vihar, Udyog Vihar, Cyber City, Sohna Road, MG Road
            and Sectors 1–49 — all pincodes 122001 to 122022. Watch a booking move from request to
            check-in, or tap an area.
          </p>
        </div>
      </div>
      <CoverageMap />
      <div className="sw-grid sw-g3" style={{ marginTop: 12 }}>
        {[
          ['1,500+', 'Businesses served'],
          ['8 areas · 22 pincodes', 'Across Gurgaon'],
          ['Same-day', 'Staffing available'],
        ].map(([v, l]) => (
          <div className="sw-card sw-stat" key={l}>
            <b style={{ fontSize: 22 }}>{v}</b>
            <span>{l}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export function AppBlock() {
  return (
    <section className="sw-sec" id="app-section">
      <div className="sw-card" style={{ padding: 'clamp(20px,3vw,32px)', borderRadius: 26 }}>
        <div className="sw-two" style={{ alignItems: 'center' }}>
          <div>
            <p className="sw-eyebrow">The Switch app</p>
            <h2 className="sw-h2" style={{ marginTop: 10 }}>
              Your whole staff, <em>in your pocket.</em>
            </h2>
            <p className="sw-lead" style={{ marginTop: 10 }}>
              Browse verified staff, book in a few taps and keep the day moving. Built for the
              moments you need help now.
            </p>
            <div className="sw-grid" style={{ marginTop: 16 }}>
              {[
                ['01', 'Find verified people', 'Profiles, roles and availability in one place.'],
                ['02', 'Book in minutes', 'Share your shift details without a call.'],
                ['03', 'Stay in control', 'Track bookings, OTPs and payments from the app.'],
              ].map(([n, t, c]) => (
                <div key={n} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <span className="sw-pill">{n}</span>
                  <div>
                    <b>{t}</b>
                    <p className="sw-muted" style={{ fontSize: 13.5 }}>
                      {c}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="sw-btns" style={{ marginTop: 18 }}>
              <StoreButtons />
            </div>
            <p className="sw-muted" style={{ fontSize: 12.5, marginTop: 10 }}>
              Free to download · Built for busy teams
            </p>
          </div>
          <AppScreens />
        </div>
      </div>
    </section>
  )
}

const EMPTY = { business: '', phone: '', role: FORM_ROLES[0], count: '', area: '', message: '' }

/* Request form: hands the request to WhatsApp so every lead lands in one inbox,
   and logs it to the Google Sheet when LEADS_SHEET_URL is set (field names must
   match scripts/lead-sheet.gs). Same behaviour as before the redesign. */
export function RequestForm({ onToast }) {
  const [form, setForm] = useState(EMPTY)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const text = [
    "Hi Switch — I'd like to hire staff.",
    form.business && `Business: ${form.business}`,
    form.phone && `Phone: ${form.phone}`,
    `Role: ${form.role}`,
    form.count && `How many: ${form.count}`,
    form.area && `Area: ${form.area}`,
    form.message && `Notes: ${form.message}`,
  ]
    .filter(Boolean)
    .join('\n')

  const submit = (e) => {
    e.preventDefault()
    window.open(waLink(text), '_blank', 'noopener')
    trackWhatsApp('Request form')
    onToast?.('Opening WhatsApp — hit send to share your request.')
    if (!LEADS_SHEET_URL) return
    fetch(LEADS_SHEET_URL, {
      method: 'POST',
      mode: 'no-cors',
      body: new URLSearchParams({
        ...form,
        page: window.location.pathname,
        'bot-field': e.currentTarget.elements['bot-field']?.value || '',
      }),
    }).catch(() => {})
  }

  return (
    <section className="sw-sec" id="request">
      <div className="sw-two">
        <div>
          <p className="sw-eyebrow">Ready to get started</p>
          <h2 className="sw-h2" style={{ marginTop: 10 }}>
            Tell us the shift. <em>We’ll send the people.</em>
          </h2>
          <p className="sw-lead" style={{ marginTop: 10 }}>
            Tell us what you need, and our team will find verified, trained staff for your business
            — quickly and hassle-free.
          </p>
          <div className="sw-card" style={{ padding: 18, marginTop: 18, display: 'grid', gap: 6 }}>
            <b>We’re here to help.</b>
            <p className="sw-muted" style={{ fontSize: 14 }}>
              Questions, bulk teams or a custom quote — talk to a real person.
            </p>
            <p style={{ fontWeight: 800, marginTop: 6 }}>
              {PHONE_DISPLAY} · {EMAIL}
            </p>
            <p className="sw-muted" style={{ fontSize: 13 }}>
              {ADDRESS.join(', ')}
            </p>
          </div>
        </div>
        <form className="sw-card sw-form" onSubmit={submit}>
          <b className="sw-h3">Prefer to send your requirement?</b>
          <input type="text" name="bot-field" tabIndex={-1} autoComplete="off" style={{ display: 'none' }} aria-hidden="true" />
          <label className="sw-field" htmlFor="rq-business">
            Business name
            <input className="sw-inp" id="rq-business" required value={form.business} onChange={set('business')} placeholder="e.g. Yum Yum Cha" />
          </label>
          <label className="sw-field" htmlFor="rq-phone">
            Phone / WhatsApp
            <input className="sw-inp" id="rq-phone" required inputMode="numeric" value={form.phone} onChange={set('phone')} placeholder="10-digit mobile" />
          </label>
          <div className="sw-grid sw-g2">
            <label className="sw-field" htmlFor="rq-role">
              Role needed
              <select className="sw-inp" id="rq-role" value={form.role} onChange={set('role')}>
                {FORM_ROLES.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </label>
            <label className="sw-field" htmlFor="rq-count">
              How many?
              <input className="sw-inp" id="rq-count" inputMode="numeric" value={form.count} onChange={set('count')} placeholder="e.g. 3" />
            </label>
          </div>
          <label className="sw-field" htmlFor="rq-area">
            Area / locality
            <input className="sw-inp" id="rq-area" value={form.area} onChange={set('area')} placeholder="e.g. DLF Phase 2, Udyog Vihar" />
          </label>
          <label className="sw-field" htmlFor="rq-message">
            Anything else? (optional)
            <textarea className="sw-inp" id="rq-message" value={form.message} onChange={set('message')} placeholder="Shift timings, start date…" />
          </label>
          <button className="sw-btn" type="submit">
            Send on WhatsApp <Icon name="arrow" />
          </button>
        </form>
      </div>
    </section>
  )
}
