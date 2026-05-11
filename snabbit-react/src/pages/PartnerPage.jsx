import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import './PartnerPage.css'

const APP_URL = 'https://app.switchlocally.com/'

const BENEFITS = [
  { ico: '💰', title: 'Earn ₹15,000–₹40,000/month', desc: 'Flexible bookings — work part-time or full-time. Get paid weekly, no agency cuts.' },
  { ico: '📅', title: 'You pick your hours',         desc: 'Choose your availability — 4-hour shifts, full days, or week-long gigs.' },
  { ico: '🛡️', title: 'Verified, trusted jobs',       desc: 'All customers are app-verified. No fake bookings, no last-minute cancellations.' },
  { ico: '⭐', title: 'Build your reputation',        desc: 'Get rated by customers. Higher ratings = more bookings = higher rates.' },
  { ico: '🎓', title: 'Free skill training',          desc: 'Access free training modules to level up your skills and earn more per hour.' },
  { ico: '🚀', title: 'Same-day approval',            desc: 'Apply today, get verified within 24 hours, and start earning the very next day.' },
]

const STEPS = [
  { n: '01', title: 'Apply on the app',          desc: 'Download the Switch Partner app and submit your details. Takes 5 minutes.' },
  { n: '02', title: 'Get Aadhaar verified',      desc: 'Quick background and Aadhaar check — same-day approval for most applicants.' },
  { n: '03', title: 'Accept your first booking', desc: 'Browse nearby jobs that match your skills. Accept the ones that work for you.' },
  { n: '04', title: 'Get paid weekly',           desc: 'Complete work, get rated, and receive payments directly in your bank account every week.' },
]

const CATEGORIES = [
  'Cook','Cleaning Staff','Driver','Security Guard','Factory Helper',
  'General Helper','Caretaker','Kitchen Helper','Promoter','Bouncer','Bartender','Waiter',
]

const REQUIREMENTS = [
  'Aged 18 or above',
  'Valid Aadhaar card',
  'Smartphone with internet',
  'Basic experience in your chosen category',
  'Willing to work in Gurgaon and nearby areas',
]

const FAQS = [
  { q: 'How much can I earn as a Switch partner?',    a: 'Most partners earn between ₹15,000 and ₹40,000 per month depending on the number of hours, skill category, and customer ratings. Top-rated partners can earn even more.' },
  { q: 'Do I have to pay anything to join?',           a: 'No. Joining Switch as a partner is 100% free. We only deduct a small platform fee from each completed booking.' },
  { q: 'When do I get paid?',                          a: 'Payments are credited weekly directly to your bank account. There is no waiting for monthly cycles.' },
  { q: 'Can I choose which jobs to accept?',           a: 'Yes — you have full control. Browse nearby bookings on the app and accept only the ones that fit your schedule and preferred areas.' },
  { q: 'What documents do I need?',                    a: 'Just your Aadhaar card and a smartphone. For some categories (like driver), we may ask for additional documents such as a driving licence.' },
  { q: 'How long does verification take?',             a: 'Most applicants are verified within 24 hours. Once approved, you can start accepting bookings immediately.' },
]

function Check() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <polyline points="3 8.5 6.5 12 13 5"/>
    </svg>
  )
}

export default function PartnerPage() {
  useEffect(() => { window.scrollTo(0, 0) }, [])

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title: 'Switch Partner — Earn as a Verified Blue-Collar Worker in Gurgaon',
    description: 'Join Switch as a verified partner. Earn ₹15,000–₹40,000 per month with flexible hours. Work as a cook, cleaner, driver, security guard, helper, bartender or waiter.',
    employmentType: ['FULL_TIME', 'PART_TIME', 'CONTRACTOR'],
    hiringOrganization: { '@type': 'Organization', name: 'Switch', sameAs: 'https://switchlocally.com' },
    jobLocation: {
      '@type': 'Place',
      address: { '@type': 'PostalAddress', addressLocality: 'Gurgaon', addressRegion: 'Haryana', addressCountry: 'IN' },
    },
    baseSalary: {
      '@type': 'MonetaryAmount',
      currency: 'INR',
      value: { '@type': 'QuantitativeValue', minValue: 15000, maxValue: 40000, unitText: 'MONTH' },
    },
    datePosted: '2026-01-01',
    validThrough: '2027-01-01',
    directApply: true,
  }

  return (
    <div className="pp-root">
      <Helmet>
        <title>Become a Switch Partner — Earn as a Verified Worker in Gurgaon</title>
        <meta name="description" content="Join Switch as a partner and earn ₹15,000–₹40,000 per month with flexible hours. Work as a cook, cleaner, driver, security guard, helper, bartender or waiter. Free to join, weekly payouts, same-day approval." />
        <link rel="canonical" href="https://switchlocally.com/partner" />
        <script type="application/ld+json">{JSON.stringify(schema)}</script>
      </Helmet>

      <nav className="pp-nav">
        <div className="pp-nav-inner">
          <Link to="/" className="pp-nav-logo">
            <div className="pp-nav-mark">S</div>
            <span className="pp-nav-name">Switch</span>
          </Link>
          <Link to="/" className="pp-nav-back">← Back to home</Link>
        </div>
      </nav>

      <header className="pp-hero">
        <div className="pp-hero-bg" aria-hidden="true">
          <div className="pp-hero-grid" />
          <div className="pp-hero-glow" />
        </div>
        <div className="pp-hero-inner">
          <div className="pp-tag-row">
            <span className="pp-dot" />
            <span>Now hiring · Gurgaon</span>
          </div>
          <h1 className="pp-h1">
            Earn with Switch.<br />
            <em>Work on your terms.</em>
          </h1>
          <p className="pp-lead">
            Join 1,000+ verified partners earning ₹15,000–₹40,000 every month.
            Pick your hours, pick your jobs, and get paid every week — directly to your bank account.
          </p>
          <div className="pp-cta-row">
            <a href={APP_URL} className="pp-cta-primary">
              Apply on the App
              <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="8" x2="13" y2="8"/>
                <polyline points="9 4 13 8 9 12"/>
              </svg>
            </a>
            <a href="#how-to-join" className="pp-cta-secondary">How it works</a>
          </div>
          <div className="pp-quick-stats">
            <div><strong>₹15K–40K</strong><span>Avg monthly earnings</span></div>
            <div><strong>24 hrs</strong><span>Approval time</span></div>
            <div><strong>Weekly</strong><span>Direct payouts</span></div>
            <div><strong>Free</strong><span>To join</span></div>
          </div>
        </div>
      </header>

      <main>
        <section className="pp-sec">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">Why Switch</span>
              <h2 className="pp-h2">Built for workers who want freedom.</h2>
              <p className="pp-sub">No agency cuts. No middlemen. No hidden fees. Just real jobs, real pay, and real growth.</p>
            </div>
            <div className="pp-benefits">
              {BENEFITS.map((b, i) => (
                <div className="pp-benefit" key={i}>
                  <div className="pp-benefit-ico">{b.ico}</div>
                  <div className="pp-benefit-title">{b.title}</div>
                  <p className="pp-benefit-desc">{b.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="pp-sec pp-sec-alt" id="how-to-join">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">How to join</span>
              <h2 className="pp-h2">4 steps to your first booking.</h2>
              <p className="pp-sub">Apply today. Start earning tomorrow.</p>
            </div>
            <div className="pp-steps">
              {STEPS.map((s, i) => (
                <div className="pp-step" key={i}>
                  <div className="pp-step-num">{s.n}</div>
                  <div className="pp-step-title">{s.title}</div>
                  <p className="pp-step-desc">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="pp-sec">
          <div className="pp-w pp-two-col">
            <div>
              <span className="pp-tag">Categories</span>
              <h2 className="pp-h2">Pick what you’re great at.</h2>
              <p className="pp-sub">We have jobs across 12+ blue-collar categories. Apply for one or multiple.</p>
              <div className="pp-cat-grid">
                {CATEGORIES.map(c => <span className="pp-cat" key={c}>{c}</span>)}
              </div>
            </div>
            <div className="pp-req-card">
              <h3 className="pp-req-title">Eligibility</h3>
              <ul className="pp-req-list">
                {REQUIREMENTS.map((r, i) => (
                  <li key={i}><Check />{r}</li>
                ))}
              </ul>
              <a href={APP_URL} className="pp-cta-primary pp-cta-full">
                Apply on the App
                <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="3" y1="8" x2="13" y2="8"/>
                  <polyline points="9 4 13 8 9 12"/>
                </svg>
              </a>
            </div>
          </div>
        </section>

        <section className="pp-sec pp-sec-alt">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">Partner FAQ</span>
              <h2 className="pp-h2">Common questions.</h2>
            </div>
            <div className="pp-faq">
              {FAQS.map((f, i) => (
                <div className="pp-faq-item" key={i}>
                  <div className="pp-faq-q">{f.q}</div>
                  <p className="pp-faq-a">{f.a}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="pp-final">
          <div className="pp-final-inner">
            <h2 className="pp-final-h">Ready to start earning?</h2>
            <p className="pp-final-p">Download the Switch Partner app and submit your details. Approvals within 24 hours.</p>
            <a href={APP_URL} className="pp-cta-primary pp-cta-big">
              Apply on the App
              <svg viewBox="0 0 16 16" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="8" x2="13" y2="8"/>
                <polyline points="9 4 13 8 9 12"/>
              </svg>
            </a>
            <a href="tel:+918368828660" className="pp-call">Or call us · +91 83688 28660</a>
          </div>
        </section>
      </main>

      <footer className="pp-footer">
        <p>© 2026 Switch · <a href="tel:+918368828660">+91 83688 28660</a> · <a href="mailto:hello@switchlocally.com">hello@switchlocally.com</a> · <Link to="/">Home</Link></p>
      </footer>
    </div>
  )
}
