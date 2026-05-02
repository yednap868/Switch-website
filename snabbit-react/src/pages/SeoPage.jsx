import { useState, useEffect } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import { getPageBySlug, SEO_PAGES } from '../data/seoData'
import SeoHead from '../components/SeoHead'
import './SeoPage.css'

/* ─── MICRO COMPONENTS ─── */

function StarFill() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14">
      <path fill="#f59e0b" d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  )
}

function Stars() {
  return <div className="sp-stars">{[0,1,2,3,4].map(i => <StarFill key={i} />)}</div>
}

function TrustBadges() {
  return (
    <div className="sp-trust">
      <span>✓ Aadhaar Verified</span>
      <span>✓ Background Checked</span>
      <span>✓ Pay After Work</span>
      <span>✓ Same-Day Available</span>
    </div>
  )
}

function Breadcrumb({ page }) {
  return (
    <nav className="sp-breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li><Link to="/">Home</Link></li>
        <li aria-hidden="true">/</li>
        <li>
          {page.type === 'landing'
            ? <span aria-current="page">{page.service}</span>
            : <Link to={`/${page.serviceId}-gurgaon`}>{page.service}</Link>
          }
        </li>
        {page.type !== 'landing' && (
          <>
            <li aria-hidden="true">/</li>
            <li><span aria-current="page">{page.h1}</span></li>
          </>
        )}
      </ol>
    </nav>
  )
}

function PricingTable({ prices }) {
  if (!prices?.length) return null
  return (
    <div className="sp-prices">
      {prices.map((p, i) => (
        <div className="sp-price-card" key={i}>
          <div className="sp-price-label">{p.label}</div>
          <div className="sp-price-amt">{p.price}</div>
          <div className="sp-price-desc">{p.desc}</div>
        </div>
      ))}
    </div>
  )
}

function ComparisonTable({ service }) {
  const rows = [
    ['Booking time',         'Under 2 min',     '24–48 hrs',    'Hours or days'],
    ['Background verified',  '✓ Aadhaar',       'Sometimes',    'Never'],
    ['Transparent pricing',  '✓ Fixed rate',    '+ Commission', 'Variable'],
    ['Pay after work',       '✓',               '✗',            '✗'],
    ['Same-day available',   '✓',               'Rare',         'Rare'],
    ['Free cancellation',    '✓ Up to 2 hrs',   'Fee charged',  'N/A'],
    ['Rated & reviewed',     '✓ 4.8 ★',        '✗',            '✗'],
  ]
  return (
    <div className="sp-comparison">
      <div className="sp-comparison-scroll">
        <table>
          <thead>
            <tr>
              <th className="sp-comp-feature"></th>
              <th className="sp-comp-switch">Switch</th>
              <th>Agency / Broker</th>
              <th>Find Yourself</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([feat, sw, ag, fy], i) => (
              <tr key={i}>
                <td className="sp-comp-feature">{feat}</td>
                <td className="sp-comp-switch sp-comp-good">{sw}</td>
                <td className="sp-comp-neutral">{ag}</td>
                <td className="sp-comp-neutral">{fy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FaqAccordion({ faqs }) {
  const [open, setOpen] = useState(null)
  if (!faqs?.length) return null
  return (
    <div className="sp-faqs">
      {faqs.map((f, i) => (
        <div className={`sp-faq-item${open === i ? ' open' : ''}`} key={i}>
          <button className="sp-faq-btn" onClick={() => setOpen(o => o === i ? null : i)}>
            <span>{f.q}</span>
            <svg viewBox="0 0 12 12" className="sp-faq-icon"><line x1="6" y1="1" x2="6" y2="11"/><line x1="1" y1="6" x2="11" y2="6"/></svg>
          </button>
          <div className="sp-faq-body">{f.a}</div>
        </div>
      ))}
    </div>
  )
}

function CtaBlock({ service }) {
  return (
    <div className="sp-cta">
      <div className="sp-cta-rating">
        <Stars />
        <span>4.8 · 1,000+ bookings</span>
      </div>
      <h3 className="sp-cta-h">Book a {service} in Gurgaon Today</h3>
      <p className="sp-cta-p">Verified professionals. Flexible hours. Pay only after you're satisfied.</p>
      <a href="/#download" className="sp-cta-btn">Get the App — It's Free</a>
    </div>
  )
}

function RelatedPages({ serviceId, currentSlug }) {
  const related = SEO_PAGES
    .filter(p => p.serviceId === serviceId && p.slug !== currentSlug)
    .slice(0, 9)
  if (!related.length) return null
  return (
    <div className="sp-related">
      <div className="sp-related-inner">
        <h3 className="sp-related-h">More {related[0].service} pages</h3>
        <div className="sp-related-links">
          {related.map(p => (
            <Link key={p.slug} to={`/${p.slug}`} className="sp-related-link">{p.h1}</Link>
          ))}
        </div>
      </div>
    </div>
  )
}

function StickyCTA({ service }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <div className={`sp-sticky${visible ? ' sp-sticky--show' : ''}`}>
      <a href="/#download" className="sp-sticky-btn">Book {service} Now</a>
    </div>
  )
}

/* ─── PAGE TYPE RENDERERS ─── */

function LandingPage({ page }) {
  return (
    <>
      <section className="sp-hero">
        <div className="sp-hero-inner">
          <div className="sp-hero-text">
            <span className="sp-tag">Gurgaon · Book Instantly · Verified Workers</span>
            <h1 className="sp-h1">{page.h1}</h1>
            <p className="sp-intro">{page.intro}</p>
            <TrustBadges />
            <div className="sp-hero-btns">
              <a href="/#download" className="sp-cta-btn">Book Now — Free App</a>
              <a href={`/${page.serviceId}-cost-gurgaon`} className="sp-cta-ghost">View Pricing →</a>
            </div>
          </div>
          <div className="sp-hero-img">
            <img src={page.serviceImg} alt={`${page.service} in Gurgaon`} />
            <div className="sp-hero-badge">
              <span className="sp-hero-badge-dot" />
              <span>Available today in Gurgaon</span>
            </div>
          </div>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">What a {page.service} Does for You</h2>
          <p className="sp-body">{page.longDesc}</p>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Transparent Pricing — No Hidden Fees</h2>
          <p className="sp-body">All rates are fixed and shown upfront. No agency commission, no call-out fees, no surprises. You pay only after the work is completed to your satisfaction.</p>
          <PricingTable prices={page.prices} />
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">How It Works — 3 Simple Steps</h2>
          <div className="sp-steps">
            <div className="sp-step">
              <div className="sp-step-n">Step 1</div>
              <h3 className="sp-step-title">Choose {page.service}</h3>
              <p className="sp-step-desc">Open the Switch app, select {page.service.toLowerCase()} and pick your duration — from 4 hours to 7 days.</p>
            </div>
            <div className="sp-step">
              <div className="sp-step-n">Step 2</div>
              <h3 className="sp-step-title">Set time & address</h3>
              <p className="sp-step-desc">Pick your date, time and Gurgaon address. Confirm in under 2 minutes — no calls, no paperwork.</p>
            </div>
            <div className="sp-step">
              <div className="sp-step-n">Step 3</div>
              <h3 className="sp-step-title">Worker arrives & you pay after</h3>
              <p className="sp-step-desc">Your verified {page.service.toLowerCase()} arrives on time. Pay securely in-app only after the job is done.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Switch vs Other Options</h2>
          <p className="sp-body">See why Gurgaon residents book through Switch instead of agencies or finding workers themselves.</p>
          <ComparisonTable service={page.service} />
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Why Choose Switch?</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">What Customers Say</h2>
          <div className="sp-reviews">
            {page.reviews.map((r, i) => (
              <div className="sp-review" key={i}>
                <Stars />
                <p className="sp-rev-text">"{r.text}"</p>
                <div className="sp-rev-name">{r.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Areas We Serve in Gurgaon</h2>
          <p className="sp-body">Switch {page.service.toLowerCase()} bookings are available across all major sectors and localities in Gurgaon. Check the app for real-time availability in your area.</p>
          <div className="sp-areas">
            {page.areas.map((a, i) => <span className="sp-area" key={i}>{a}</span>)}
          </div>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Frequently Asked Questions</h2>
          <FaqAccordion faqs={page.faqs} />
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function PricingPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Transparent Pricing · No Hidden Fees · Pay After Work</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Rate Card</h2>
          <PricingTable prices={page.prices} />
          <ul className="sp-tasks" style={{marginTop:'2rem'}}>
            {page.pricingNotes.map((n, i) => <li key={i}><span className="sp-check">✓</span>{n}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">What's Included at Every Price</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Switch vs Agency Pricing</h2>
          <ComparisonTable service={page.service} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing FAQs</h2>
          <FaqAccordion faqs={page.faqs} />
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Available in These Areas</h2>
          <div className="sp-areas">
            {page.areas.map((a, i) => <span className="sp-area" key={i}>{a}</span>)}
          </div>
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function HowToHirePage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Step-by-Step Guide · No Agency Needed</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">3 Steps to Book on Switch</h2>
          <div className="sp-steps">
            {page.steps.map((s, i) => (
              <div className="sp-step" key={i}>
                <div className="sp-step-n">Step {s.n}</div>
                <h3 className="sp-step-title">{s.title}</h3>
                <p className="sp-step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Tips Before You Book</h2>
          <ul className="sp-tasks">
            {page.tips.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">What They Can Do for You</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Common Questions About Hiring</h2>
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function BenefitsPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Why Switch · Gurgaon's Top-Rated Platform</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Top Benefits</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">When to Hire a {page.service}</h2>
          <ul className="sp-tasks">
            {page.useCases.map((u, i) => <li key={i}><span className="sp-check">→</span>{u}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Switch vs Other Options</h2>
          <ComparisonTable service={page.service} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Full Task List</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Questions</h2>
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function ChecklistPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Full Task Checklist · No Surprises</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Task Breakdown by Category</h2>
          <div className="sp-checklist-grid">
            {page.checklistCategories.map((cat, i) => (
              <div className="sp-checklist-cat" key={i}>
                <h3 className="sp-cat-title">{cat.cat}</h3>
                <ul>
                  {cat.items.map((item, j) => (
                    <li key={j}><span className="sp-check">✓</span>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Full Task List</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing</h2>
          <PricingTable prices={page.prices} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function FaqPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">All Your Questions Answered</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">All FAQs</h2>
          <FaqAccordion faqs={page.faqs} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing at a Glance</h2>
          <PricingTable prices={page.prices} />
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Serving These Areas in Gurgaon</h2>
          <div className="sp-areas">
            {page.areas.map((a, i) => <span className="sp-area" key={i}>{a}</span>)}
          </div>
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function NearMePage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Nearest Available · Gurgaon</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
          <TrustBadges />
          <a href="/#download" className="sp-cta-btn">Find One Near You</a>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Areas We Cover in Gurgaon</h2>
          <div className="sp-areas">
            {page.areas.map((a, i) => <span className="sp-area" key={i}>{a}</span>)}
          </div>
          <p className="sp-body" style={{marginTop:'1.5rem'}}>Don't see your area? Open the Switch app — we are expanding coverage across Gurgaon every week. Enter your location to check real-time availability in your sector.</p>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Why Location Matters</h2>
          <ul className="sp-tasks">
            <li><span className="sp-check">✓</span>Nearby workers arrive faster — less waiting time</li>
            <li><span className="sp-check">✓</span>Lower travel overhead means better value for you</li>
            <li><span className="sp-check">✓</span>Workers familiar with your area navigate easily</li>
            <li><span className="sp-check">✓</span>Same-day slots more likely when worker is local to your sector</li>
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">What They Can Do</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing</h2>
          <PricingTable prices={page.prices} />
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function SameDayPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Urgent Booking · Confirmed Within Hours · No Surge</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
          <TrustBadges />
          <a href="/#download" className="sp-cta-btn">Book for Today</a>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">How Same-Day Booking Works</h2>
          <div className="sp-steps">
            {page.steps.map((s, i) => (
              <div className="sp-step" key={i}>
                <div className="sp-step-n">Step {s.n}</div>
                <h3 className="sp-step-title">{s.title}</h3>
                <p className="sp-step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Why Switch for Urgent Jobs</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Same-Day Pricing — No Extra Charge</h2>
          <PricingTable prices={page.prices} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Questions About Same-Day Booking</h2>
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function ReviewsPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">Verified Customer Reviews · 4.8 ★ Average</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <div className="sp-rating-summary">
            <div className="sp-rating-big">4.8 ★</div>
            <div className="sp-rating-label">Average from verified {page.service.toLowerCase()} bookings in Gurgaon</div>
          </div>
          <h2 className="sp-h2">Customer Stories</h2>
          <div className="sp-reviews sp-reviews-lg">
            {page.reviews.map((r, i) => (
              <div className="sp-review" key={i}>
                <Stars />
                <p className="sp-rev-text">"{r.text}"</p>
                <div className="sp-rev-name">{r.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Why They Keep Coming Back</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing</h2>
          <PricingTable prices={page.prices} />
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

function VerifiedPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">3-Step Verification · Aadhaar · Background Checked · Skills Tested</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">How We Verify Every Worker</h2>
          <div className="sp-vsteps">
            {page.verificationSteps.map((v, i) => (
              <div className="sp-vstep" key={i}>
                <div className="sp-vstep-n">{i + 1}</div>
                <div>
                  <h3 className="sp-vstep-title">{v.title}</h3>
                  <p className="sp-vstep-desc">{v.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">What Verified Workers Can Do</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Switch vs Unverified Alternatives</h2>
          <ComparisonTable service={page.service} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Benefits of Booking Verified</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
          </ul>
        </div>
      </section>
      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing</h2>
          <PricingTable prices={page.prices} />
        </div>
      </section>
      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">FAQs About Verification</h2>
          <FaqAccordion faqs={page.faqs} />
          <CtaBlock service={page.service} />
        </div>
      </section>
    </>
  )
}

/* ─── MAIN SEO PAGE ─── */

const PAGE_RENDERERS = {
  'landing':      LandingPage,
  'pricing':      PricingPage,
  'how-to-hire':  HowToHirePage,
  'benefits':     BenefitsPage,
  'checklist':    ChecklistPage,
  'faq':          FaqPage,
  'near-me':      NearMePage,
  'same-day':     SameDayPage,
  'reviews':      ReviewsPage,
  'verified':     VerifiedPage,
}

export default function SeoPage() {
  const { slug } = useParams()
  const page = getPageBySlug(slug)

  if (!page) return <Navigate to="/" replace />

  const Renderer = PAGE_RENDERERS[page.type]

  return (
    <div className="sp-root">
      <SeoHead page={page} />

      <nav className="sp-nav">
        <div className="sp-nav-inner">
          <Link to="/" className="sp-nav-logo">
            <div className="sp-nav-mark">S</div>
            <span className="sp-nav-name">Switch</span>
          </Link>
          <div className="sp-nav-links">
            <Link to="/#roles" className="sp-nav-link">Services</Link>
            <Link to="/#how-it-works" className="sp-nav-link">How it works</Link>
            <Link to="/#reviews" className="sp-nav-link">Reviews</Link>
          </div>
          <a href="/#download" className="sp-nav-cta">Get the App</a>
        </div>
      </nav>

      <Breadcrumb page={page} />

      <main className="sp-main">
        <Renderer page={page} />
      </main>

      <RelatedPages serviceId={page.serviceId} currentSlug={page.slug} />

      <footer className="sp-footer">
        <div className="sp-footer-inner">
          <Link to="/" className="sp-footer-logo">
            <div className="sp-nav-mark" style={{width:28,height:28,fontSize:'0.8125rem',borderRadius:7}}>S</div>
            <span style={{fontWeight:800,fontSize:'1rem',color:'#fff',letterSpacing:'-0.025em'}}>Switch</span>
          </Link>
          <p>© 2025 Switch · <a href="mailto:hello@switchlocally.com">hello@switchlocally.com</a> · <Link to="/">Home</Link> · <Link to="/home-cleaning-gurgaon">Services</Link></p>
        </div>
      </footer>

      <StickyCTA service={page.service} />
    </div>
  )
}
