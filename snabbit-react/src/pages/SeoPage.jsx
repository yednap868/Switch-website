import { useState } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import { getPageBySlug, SEO_PAGES } from '../data/seoData'
import SeoHead from '../components/SeoHead'
import './SeoPage.css'

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
      <h3 className="sp-cta-h">Book a {service} in Gurgaon Today</h3>
      <p className="sp-cta-p">Verified professionals. Flexible hours. Pay only after you're satisfied.</p>
      <a href="/#download" className="sp-cta-btn">Get the App — It's Free</a>
    </div>
  )
}

function RelatedPages({ serviceId, currentSlug }) {
  const related = SEO_PAGES
    .filter(p => p.serviceId === serviceId && p.slug !== currentSlug)
    .slice(0, 5)
  if (!related.length) return null
  return (
    <div className="sp-related">
      <h3 className="sp-related-h">More about {related[0].service} in Gurgaon</h3>
      <div className="sp-related-links">
        {related.map(p => (
          <Link key={p.slug} to={`/${p.slug}`} className="sp-related-link">{p.h1}</Link>
        ))}
      </div>
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
            <span className="sp-tag">Gurgaon · Book Instantly</span>
            <h1 className="sp-h1">{page.h1}</h1>
            <p className="sp-intro">{page.intro}</p>
            <TrustBadges />
            <a href="/#download" className="sp-cta-btn">Book Now — Free App</a>
          </div>
          <div className="sp-hero-img">
            <img src={page.serviceImg} alt={page.service} />
          </div>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">What's Included</h2>
          <p className="sp-body">{page.longDesc}</p>
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
          <span className="sp-tag">Transparent Pricing · No Hidden Fees</span>
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
          <h2 className="sp-h2">What's Covered</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing FAQs</h2>
          <FaqAccordion faqs={page.faqs} />
        </div>
      </section>

      <section className="sp-section">
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
          <span className="sp-tag">Step-by-Step Guide</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">3 Steps to Book</h2>
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
          <h2 className="sp-h2">What They Can Do</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Common Questions</h2>
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
          <span className="sp-tag">Why Switch?</span>
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
          <h2 className="sp-h2">What They Handle</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section">
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
          <span className="sp-tag">Full Task Checklist</span>
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
          <span className="sp-tag">Nearest Available Worker</span>
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
          <p className="sp-body" style={{marginTop:'1.5rem'}}>Don't see your area? Open the Switch app — we are expanding coverage across Gurgaon every week. Enter your location to check real-time availability.</p>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Why Location Matters</h2>
          <ul className="sp-tasks">
            <li><span className="sp-check">✓</span>Nearby workers arrive faster — less waiting time</li>
            <li><span className="sp-check">✓</span>Lower travel overhead means better value for you</li>
            <li><span className="sp-check">✓</span>Workers familiar with your area navigate easily</li>
            <li><span className="sp-check">✓</span>Same-day slots more likely when worker is local</li>
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
          <span className="sp-tag">Urgent Booking · Confirmed in Hours</span>
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
          <h2 className="sp-h2">Pricing</h2>
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
          <span className="sp-tag">Verified Customer Reviews</span>
          <h1 className="sp-h1">{page.h1}</h1>
          <p className="sp-intro">{page.intro}</p>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
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
          <div className="sp-rating-summary">
            <div className="sp-rating-big">4.8 ★</div>
            <div className="sp-rating-label">Average rating from verified bookings</div>
          </div>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">What They Helped With</h2>
          <ul className="sp-tasks">
            {page.tasks.map((t, i) => <li key={i}><span className="sp-check">✓</span>{t}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section sp-alt">
        <div className="sp-w">
          <h2 className="sp-h2">Why They Keep Coming Back</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
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

function VerifiedPage({ page }) {
  return (
    <>
      <section className="sp-hero sp-hero-sm">
        <div className="sp-w">
          <span className="sp-tag">3-Step Verification Process</span>
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
          <h2 className="sp-h2">Benefits of Booking Verified</h2>
          <ul className="sp-benefits">
            {page.benefits.map((b, i) => <li key={i}><span className="sp-check">✓</span>{b}</li>)}
          </ul>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-w">
          <h2 className="sp-h2">Pricing</h2>
          <PricingTable prices={page.prices} />
        </div>
      </section>

      <section className="sp-section sp-alt">
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
  'landing': LandingPage,
  'pricing': PricingPage,
  'how-to-hire': HowToHirePage,
  'benefits': BenefitsPage,
  'checklist': ChecklistPage,
  'faq': FaqPage,
  'near-me': NearMePage,
  'same-day': SameDayPage,
  'reviews': ReviewsPage,
  'verified': VerifiedPage,
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
          <a href="/#download" className="sp-nav-cta">Get the App</a>
        </div>
      </nav>

      <main className="sp-main">
        <Renderer page={page} />
      </main>

      <RelatedPages serviceId={page.serviceId} currentSlug={page.slug} />

      <footer className="sp-footer">
        <div className="sp-footer-inner">
          <p>© 2025 Switch · <a href="mailto:hello@switchlocally.com">hello@switchlocally.com</a> · <Link to="/">Home</Link></p>
        </div>
      </footer>
    </div>
  )
}
