import { useCallback, useEffect, useRef, useState } from 'react'
import Annotate from '../fx/Annotate.jsx'
import CascadeLabel from '../fx/CascadeLabel.jsx'
import { prefersReducedMotion } from '../fx/motion.js'
import { BRANDS, FAQS, REVIEWS, WHY_US } from '../../data/homeContent.js'
import { EMPLOYER_LOGIN, waLink } from '../../data/site.js'

const METRICS = [
  { value: '20,000+', label: 'Verified Switch Players' },
  { value: '1,000+', label: 'Businesses served' },
  { value: '24h', label: 'Replacement time' },
]

const PATHWAYS = [
  {
    kicker: 'TRY FIRST',
    title: 'Trial Shift',
    copy: 'Start with one shift and see the difference.',
    msg: 'Hi Switch — I would like to book a trial shift.',
  },
  {
    kicker: 'SCALE UP',
    title: 'Bulk / Weekly Staffing',
    copy: 'Build a dependable team for the week ahead.',
    msg: 'Hi Switch — I need a bulk or weekly staffing quote.',
  },
]

const PRICES = [
  { tier: 'Hourly', figure: '₹99–199', unit: '/hour' },
  { tier: 'Full Day', figure: '₹999–1,299', unit: '/day' },
  { tier: 'Weekly Team', figure: 'from ₹6,500', unit: '/week' },
]

const PLANS = [
  {
    index: '01 / ESSENTIAL',
    badge: 'CORE TEAM',
    name: 'Essential',
    price: '₹999',
    per: '/mo',
    description: 'Reliable everyday support for your operations.',
    items: ['Housekeeping', 'General Helper', 'Picker & Packer', 'Cleaner · Office Boy', 'Loader · Gardener'],
    cta: 'Ask about Essential',
    msg: "Hi Switch — I'd like to subscribe to the Essential staffing plan (₹999/mo). Please share the details.",
  },
  {
    index: '02 / SECURITY',
    badge: 'PEACE OF MIND',
    name: 'Security',
    price: '₹999',
    per: '/mo',
    featured: true,
    description: 'Consistent security cover with replacement support.',
    items: [
      'Background & Aadhaar verified',
      'Day / night shift cover',
      'Instant replacement',
      'Uniformed & briefed',
    ],
    cta: 'Ask about Security',
    msg: "Hi Switch — I'd like to subscribe to the Security guard plan (₹999/mo). Please share the details.",
  },
  {
    index: '03 / SKILLED',
    badge: 'CUSTOM',
    name: 'Skilled · Custom',
    price: 'On request',
    description: 'A tailored team for specialist or larger staffing needs.',
    items: ['Cook · Chef', 'Waiter · Bartender', 'Delivery Rider · Driver', 'Cashier', 'Bulk / team hiring'],
    cta: 'Talk to Switch',
    msg: 'Hi Switch — I need skilled / custom staff on subscription. Please share pricing.',
  },
]

const INCLUDES = [
  'Aadhaar-verified staff',
  'Replacement guarantee',
  'Same staff, every day',
  'Dedicated ops manager',
  'Cancel anytime',
]

const REVIEW_MS = 4000

export default function TrustEditorial() {
  const [index, setIndex] = useState(0)
  const [changing, setChanging] = useState(false)
  const [openFaq, setOpenFaq] = useState(null)
  const sectionRef = useRef(null)
  const timerRef = useRef(0)
  const swapRef = useRef(0)
  const interactedRef = useRef(false)

  const go = useCallback((next) => {
    setChanging(true)
    window.clearTimeout(swapRef.current)
    swapRef.current = window.setTimeout(() => {
      setIndex((i) => (next(i) + REVIEWS.length) % REVIEWS.length)
      setChanging(false)
    }, 180)
  }, [])

  useEffect(() => () => window.clearTimeout(swapRef.current), [])

  const step = (delta) => {
    interactedRef.current = true
    go((i) => i + delta)
  }

  useEffect(() => {
    const node = sectionRef.current
    if (!node || prefersReducedMotion()) return
    const io = new IntersectionObserver(
      ([entry]) => {
        window.clearInterval(timerRef.current)
        if (entry.isIntersecting && !interactedRef.current) {
          timerRef.current = window.setInterval(() => go((i) => i + 1), REVIEW_MS)
        }
      },
      { threshold: 0.25 },
    )
    io.observe(node)
    return () => {
      io.disconnect()
      window.clearInterval(timerRef.current)
    }
  }, [go])

  const review = REVIEWS[index]
  const total = String(REVIEWS.length).padStart(2, '0')

  return (
    <section
      id="trust"
      className={`trust-editorial${changing ? ' is-changing' : ''}`}
      ref={sectionRef}
    >
      <div className="shell">
        <div className="trust-header">
          <div className="trust-header-copy">
            <CascadeLabel text="TRUSTED BY BUSINESSES" />
            <h2>
              Real businesses.
              <br />
              Real people.
              <br />
              <Annotate kind="underline" delay={0.48}>
                Real results.
              </Annotate>
            </h2>
          </div>
          <div className="trust-header-side">
            <p>
              From restaurants and warehouses to offices and retail businesses, Switch helps teams
              find verified staff when they need them.
            </p>
            <div className="trust-metrics">
              {METRICS.map((m) => (
                <div className="trust-metric" key={m.label}>
                  <strong>{m.value}</strong>
                  <span>{m.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="trust-story">
          <div className="trust-review-column">
            <div className="trust-review-frame">
              <span className="trust-quote-mark">“</span>
              <blockquote id="trust-quote">{review.text}</blockquote>
              <footer>
                <strong id="trust-name">{review.name}</strong>
                <span id="trust-meta">{review.loc}</span>
              </footer>
              <div className="trust-review-controls">
                <button
                  className="trust-arrow"
                  type="button"
                  onClick={() => step(-1)}
                  aria-label="Previous customer story"
                >
                  ←
                </button>
                <span className="trust-progress">
                  <b id="trust-current">{String(index + 1).padStart(2, '0')}</b>
                  <i>
                    <span
                      id="trust-progress-bar"
                      style={{ width: `${((index + 1) / REVIEWS.length) * 100}%` }}
                    />
                  </i>
                  <em>/ {total}</em>
                </span>
                <button
                  className="trust-arrow"
                  type="button"
                  onClick={() => step(1)}
                  aria-label="Next customer story"
                >
                  →
                </button>
              </div>
            </div>
          </div>

          <figure className="trust-worker">
            <div className="trust-worker-image">
              <img src="/hero-workers.jpg" alt="Switch worker ready for a shift" loading="lazy" />
              <span className="trust-worker-tag mono">THE PEOPLE BEHIND THE WORK</span>
              <span className="trust-worker-line" aria-hidden="true" />
            </div>
            <figcaption>
              <span>Built for the moments that cannot wait.</span>
              <strong>People in motion.</strong>
            </figcaption>
          </figure>
        </div>

        <div className="trust-logos">
          {/* Label and lead are wrapped: .trust-logos is a `180px 1fr` grid, so
              a third child would take the logo wall's cell and push the wall
              into the narrow column. */}
          <div className="trust-logos-head">
            <span className="mono">BUSINESSES WE STAFF</span>
            <p className="trust-logos-lead">
              Cafés, warehouses, showrooms, offices and event floors — one verified bench.
            </p>
          </div>
          <div className="trust-logo-list">
            {BRANDS.map((brand) => (
              <span className="trust-logo" key={brand.name} title={brand.name}>
                {brand.logo ? (
                  <img
                    src={brand.logo}
                    alt={brand.name}
                    style={{ height: `${brand.h}px` }}
                    loading="lazy"
                    decoding="async"
                  />
                ) : (
                  <b>{brand.name}</b>
                )}
              </span>
            ))}
            <span className="trust-logo-more">AND 1,000+ MORE</span>
          </div>
        </div>

        <div className="trust-details" id="pricing">
          <div className="trust-detail-block">
            <div className="eyebrow">THE SWITCH STANDARD</div>
            <h3>Why teams keep Switch close.</h3>
            <div className="reasons trust-reasons">
              {WHY_US.map((item, i) => (
                <article className="reason" key={item.title}>
                  <span className="eyebrow">{String(i + 1).padStart(2, '0')}</span>
                  <b>{item.title}</b>
                  <p>{item.desc}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="trust-detail-block">
            <div className="eyebrow">WAYS TO WORK TOGETHER</div>
            <div className="pathways">
              {PATHWAYS.map((p) => (
                <a
                  className="pathway"
                  key={p.title}
                  href={waLink(p.msg)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <span className="mono">{p.kicker}</span>
                  <strong>
                    {p.title} <b>↗</b>
                  </strong>
                  <small>{p.copy}</small>
                </a>
              ))}
            </div>

            <div className="pricing-strip">
              {PRICES.map((p) => (
                <a key={p.tier} href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
                  <span>{p.tier}</span>
                  <strong>
                    {p.figure}
                    <span>{p.unit}</span>
                  </strong>
                </a>
              ))}
            </div>

            <div className="subscription-note" id="subscription">
              <div className="subscription-heading">
                <span className="mono">SUBSCRIPTION / MONTHLY</span>
                <p>For businesses that need dependable people on a regular schedule.</p>
              </div>
              <div className="subscription-cards">
                {PLANS.map((plan) => (
                  <article
                    className={`subscription-card${plan.featured ? ' subscription-card-featured' : ''}`}
                    key={plan.name}
                  >
                    <div className="subscription-card-top">
                      <span className="subscription-index mono">{plan.index}</span>
                      <span className="subscription-badge">{plan.badge}</span>
                    </div>
                    <h4>{plan.name}</h4>
                    <div className="subscription-price">
                      {plan.price}
                      {plan.per && <span>{plan.per}</span>}
                    </div>
                    <p className="subscription-description">{plan.description}</p>
                    <ul>
                      {plan.items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                    <a
                      href={waLink(plan.msg)}
                      target="_blank"
                      rel="noreferrer"
                      className="subscription-cta"
                    >
                      {plan.cta} <b>↗</b>
                    </a>
                  </article>
                ))}
              </div>
              <p className="subscription-includes">
                <span className="mono">EVERY PLAN INCLUDES</span>
                {INCLUDES.map((inc) => (
                  <span key={inc}>{inc}</span>
                ))}
              </p>
              <p className="subscription-fineprint">
                Prices are per staff, per month, exclusive of GST (18%). Monthly subscription with a
                1-month minimum; cancel with 15 days&apos; notice. Rates indicative and subject to
                role, shift and location. T&amp;C apply.
              </p>
            </div>
          </div>

          <div className="trust-detail-block faq-block">
            <div className="eyebrow">QUESTIONS, ANSWERED</div>
            <div className="faq-list">
              {FAQS.map((faq, i) => (
                <details
                  key={faq.q}
                  open={openFaq === i}
                  onToggle={(e) => {
                    if (e.currentTarget.open) setOpenFaq(i)
                    else if (openFaq === i) setOpenFaq(null)
                  }}
                >
                  <summary>{faq.q}</summary>
                  <p>{faq.a}</p>
                </details>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
