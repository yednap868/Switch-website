import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import './PartnerPage.css'

const APP_URL = 'https://app.switchlocally.com/'

const BENEFITS = [
  { ico: '💰', title: 'Earn ₹15,000–₹40,000/month', desc: 'Flexible bookings — work part-time or full-time. No agency cuts, no middlemen.' },
  { ico: '⚡', title: 'Daily payouts to your bank', desc: 'Finish work today, money in your account tomorrow. Direct UPI / bank transfers — every single day.' },
  { ico: '📅', title: 'You pick your hours',        desc: 'Choose your availability — 4-hour shifts, full days, or week-long gigs. Total flexibility.' },
  { ico: '🛡️', title: 'Verified, trusted jobs',     desc: 'All customers are app-verified. No fake bookings, no last-minute cancellations, no chasing payments.' },
  { ico: '⭐', title: 'Build your reputation',      desc: 'Higher ratings unlock higher hourly rates and premium clients. Your work earns you growth.' },
  { ico: '🎓', title: 'Free skill training',        desc: 'Free training modules and certifications across 12+ categories. Level up, earn more per hour.' },
  { ico: '🏥', title: 'Insurance &amp; safety cover', desc: 'On-duty insurance and a 24×7 helpline. Your safety on every booking is non-negotiable.' },
  { ico: '🚀', title: 'Same-day approval',          desc: 'Apply today, get verified within 24 hours, start earning the very next day. No waiting.' },
]

const STEPS = [
  { n: '01', title: 'Apply on the app',          desc: 'Download the Switch Partner app, upload Aadhaar and a selfie. Takes under 5 minutes.' },
  { n: '02', title: 'Get verified',              desc: 'Aadhaar + background + skills check. Same-day approval for most applicants.' },
  { n: '03', title: 'Accept your first booking', desc: 'Browse nearby jobs that match your skills, hours, and preferred area. Pick what works.' },
  { n: '04', title: 'Get paid daily',            desc: 'Complete the job, get rated, and receive payment directly to your bank — within 24 hours.' },
]

const CATEGORIES = [
  { name: 'Cook',           pay: '₹109–129/hr' },
  { name: 'Cleaning Staff', pay: '₹99–119/hr' },
  { name: 'Driver',         pay: '₹109–129/hr' },
  { name: 'Security Guard', pay: '₹99–119/hr' },
  { name: 'Factory Helper', pay: '₹99–119/hr' },
  { name: 'General Helper', pay: '₹99–119/hr' },
  { name: 'Caretaker',      pay: '₹109–129/hr' },
  { name: 'Kitchen Helper', pay: '₹99–119/hr' },
  { name: 'Promoter',       pay: '₹109–129/hr' },
  { name: 'Bouncer',        pay: '₹119–129/hr' },
  { name: 'Bartender',      pay: '₹119–129/hr' },
  { name: 'Waiter',         pay: '₹109–129/hr' },
]

const REQUIREMENTS = [
  'Aged 18 or above',
  'Valid Aadhaar card',
  'Smartphone with internet',
  'Basic experience in your category',
  'Willing to work in Gurgaon & nearby',
]

const TRUST = [
  { val: '500+',   lbl: 'Active partners' },
  { val: '₹40K',   lbl: 'Top monthly earner' },
  { val: '24 hrs', lbl: 'Approval time' },
  { val: '4.9 ★',  lbl: 'Partner rating' },
]

const STORIES = [
  { img: '/cook-new.jpg',           name: 'Ramesh K.',  role: 'Cook',           text: 'I used to earn ₹12,000 in a restaurant. With Switch, I make ₹38,000 working only mornings. I pick my own hours now.' },
  { img: '/driver-new.jpg',         name: 'Suresh M.',  role: 'Driver',         text: 'Daily payouts changed everything. No waiting till month-end. I get my earnings in my account by 11 AM every day.' },
  { img: '/cleaning-staff.jpg',     name: 'Priya S.',   role: 'Cleaning Staff', text: 'I started with one booking a week. After 4 months of 5★ ratings, I’m booked solid — full 8-hour days, every day.' },
  { img: '/security-guard-new.jpg', name: 'Vikram T.',  role: 'Security Guard', text: 'No middleman, no agency fee. Whatever the client pays, that’s what I take home. Best decision I made.' },
]

const FAQS = [
  { q: 'How much can I really earn?',           a: 'Most partners earn ₹15,000–₹40,000 per month based on hours, category, and ratings. Top-rated bartenders and bouncers can reach the upper end of that range.' },
  { q: 'Do I pay anything to join?',            a: 'No. Joining is 100% free. We only take a small platform fee from each completed booking — never upfront.' },
  { q: 'When do I get paid?',                   a: 'Daily. Finish your booking, get rated, and the money lands in your bank or UPI within 24 hours. No monthly cycles.' },
  { q: 'Can I choose which jobs to accept?',    a: 'Yes. You see every nearby job on the app and decide. Skip what doesn’t fit, accept what does. Full control.' },
  { q: 'What documents do I need?',             a: 'Just an Aadhaar and a smartphone. Drivers also need a valid driving licence. Bouncers may need a fitness declaration.' },
  { q: 'How long does verification take?',      a: 'Same day for most applicants. Background-check heavy categories (driver, bouncer) may take up to 48 hours.' },
  { q: 'Is there an insurance cover?',          a: 'Yes — every Switch partner is covered by on-duty accident insurance and a 24×7 emergency helpline.' },
  { q: 'Can I work in more than one category?', a: 'Absolutely. Many partners are verified in 2–3 categories (e.g., Cook + Kitchen Helper) which doubles their booking opportunities.' },
]

function Check() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
      <polyline points="3 8.5 6.5 12 13 5"/>
    </svg>
  )
}
function Arrow({ size = 16 }) {
  return (
    <svg viewBox="0 0 16 16" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="8" x2="13" y2="8"/>
      <polyline points="9 4 13 8 9 12"/>
    </svg>
  )
}
function Star() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14">
      <path fill="#fbbf24" d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
    </svg>
  )
}

function CtaPrimary({ children, big = false }) {
  return (
    <a href={APP_URL} className={`pp-cta-primary${big ? ' pp-cta-big' : ''}`}>
      {children}<Arrow size={big ? 18 : 16}/>
    </a>
  )
}

export default function PartnerPage() {
  useEffect(() => { window.scrollTo(0, 0) }, [])

  const [hours, setHours] = useState(8)
  const [rate, setRate]   = useState(119)
  const monthly = hours * rate * 30
  const daily   = hours * rate

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title: 'Switch Partner — Earn ₹15,000–₹40,000/month with Daily Payouts',
    description: 'Join Switch as a verified partner. Earn ₹15,000–₹40,000 per month with flexible hours and DAILY bank payouts. Work as a cook, cleaner, driver, security guard, helper, bartender, bouncer, or waiter.',
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
        <title>Become a Switch Partner — Daily Payouts · Earn ₹15K–40K/month in Gurgaon</title>
        <meta name="description" content="Join Switch as a verified partner. Earn ₹15,000–₹40,000/month with DAILY bank payouts. Work as a cook, cleaner, driver, security guard, helper, bouncer, bartender or waiter in Gurgaon. Free to join, same-day approval." />
        <link rel="canonical" href="https://switchlocally.com/partner" />
        <script type="application/ld+json">{JSON.stringify(schema)}</script>
      </Helmet>

      {/* NAV */}
      <nav className="pp-nav">
        <div className="pp-nav-inner">
          <Link to="/" className="pp-nav-logo">
            <div className="pp-nav-mark">S</div>
            <span className="pp-nav-name">Switch</span>
            <span className="pp-nav-pill">Partner</span>
          </Link>
          <div className="pp-nav-right">
            <Link to="/" className="pp-nav-back">← Home</Link>
            <a href={APP_URL} className="pp-nav-cta">Apply<Arrow size={14}/></a>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <header className="pp-hero">
        <div className="pp-hero-bg" aria-hidden="true">
          <div className="pp-hero-grid" />
          <div className="pp-hero-glow" />
          <div className="pp-hero-glow pp-hero-glow-2" />
        </div>
        <div className="pp-hero-inner">
          <div className="pp-tag-row">
            <span className="pp-dot" />
            <span>Now hiring in Gurgaon · 500+ partners onboard</span>
          </div>
          <h1 className="pp-h1">
            Earn ₹40,000/month.<br />
            <em>Get paid daily.</em>
          </h1>
          <p className="pp-lead">
            Switch is India’s premium platform for verified blue-collar professionals.
            Pick your hours, pick your jobs, and receive your earnings in your bank
            <strong> every single day</strong>. No agency cuts. No waiting.
          </p>
          <div className="pp-cta-row">
            <CtaPrimary big>Apply on the App</CtaPrimary>
            <a href="#earnings" className="pp-cta-secondary">See earnings →</a>
          </div>

          <div className="pp-trust-row">
            {TRUST.map((t, i) => (
              <div className="pp-trust-cell" key={i}>
                <strong>{t.val}</strong>
                <span>{t.lbl}</span>
              </div>
            ))}
          </div>

          <div className="pp-rating">
            <div className="pp-stars"><Star/><Star/><Star/><Star/><Star/></div>
            <span>Rated <strong>4.9</strong> by Switch partners across Gurgaon</span>
          </div>
        </div>
      </header>

      <main>

        {/* EARNINGS CALCULATOR */}
        <section className="pp-sec pp-sec-alt" id="earnings">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">Earnings</span>
              <h2 className="pp-h2">See exactly what you can earn.</h2>
              <p className="pp-sub">Adjust your daily hours and hourly rate. Earnings update live.</p>
            </div>

            <div className="pp-calc">
              <div className="pp-calc-controls">
                <div className="pp-ctrl">
                  <div className="pp-ctrl-top">
                    <label>Hours per day</label>
                    <span className="pp-ctrl-val">{hours} hrs</span>
                  </div>
                  <input type="range" min="4" max="12" value={hours} onChange={e => setHours(+e.target.value)} />
                  <div className="pp-ctrl-scale"><span>4</span><span>8</span><span>12</span></div>
                </div>
                <div className="pp-ctrl">
                  <div className="pp-ctrl-top">
                    <label>Hourly rate</label>
                    <span className="pp-ctrl-val">₹{rate}</span>
                  </div>
                  <input type="range" min="99" max="129" step="1" value={rate} onChange={e => setRate(+e.target.value)} />
                  <div className="pp-ctrl-scale"><span>₹99</span><span>₹114</span><span>₹129</span></div>
                </div>
              </div>

              <div className="pp-calc-out">
                <div className="pp-calc-card pp-calc-card--hero">
                  <div className="pp-calc-lbl">Estimated monthly earnings</div>
                  <div className="pp-calc-big">₹{monthly.toLocaleString('en-IN')}</div>
                  <div className="pp-calc-note">Based on 30 working days. Paid daily to your bank.</div>
                  <CtaPrimary big>Apply on the App</CtaPrimary>
                </div>
                <div className="pp-calc-side">
                  <div className="pp-calc-card">
                    <div className="pp-calc-lbl">Daily payout</div>
                    <div className="pp-calc-mid">₹{daily.toLocaleString('en-IN')}</div>
                    <div className="pp-calc-note">In your bank by 11 AM next day</div>
                  </div>
                  <div className="pp-calc-card">
                    <div className="pp-calc-lbl">Weekly total</div>
                    <div className="pp-calc-mid">₹{(daily*7).toLocaleString('en-IN')}</div>
                    <div className="pp-calc-note">7-day work week</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* BENEFITS */}
        <section className="pp-sec">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">Why Switch</span>
              <h2 className="pp-h2">Built for workers who want freedom.</h2>
              <p className="pp-sub">No agency cuts. No middlemen. No hidden fees. Just real jobs, real pay, real growth.</p>
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
            <div className="pp-mid-cta">
              <CtaPrimary>Apply on the App</CtaPrimary>
            </div>
          </div>
        </section>

        {/* HOW TO JOIN */}
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
            <div className="pp-mid-cta">
              <CtaPrimary>Apply on the App</CtaPrimary>
            </div>
          </div>
        </section>

        {/* CATEGORIES + ELIGIBILITY */}
        <section className="pp-sec">
          <div className="pp-w pp-two-col">
            <div>
              <span className="pp-tag">Categories &amp; rates</span>
              <h2 className="pp-h2">Pick what you’re great at.</h2>
              <p className="pp-sub">Live hourly rates across our 12 verified categories. Apply for one or several — many partners run two.</p>
              <div className="pp-rate-grid">
                {CATEGORIES.map(c => (
                  <div className="pp-rate" key={c.name}>
                    <span className="pp-rate-name">{c.name}</span>
                    <span className="pp-rate-pay">{c.pay}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="pp-req-card">
              <h3 className="pp-req-title">Eligibility</h3>
              <ul className="pp-req-list">
                {REQUIREMENTS.map((r, i) => (
                  <li key={i}><Check />{r}</li>
                ))}
              </ul>
              <CtaPrimary>Apply on the App</CtaPrimary>
              <a href="tel:+918368828660" className="pp-req-call">or call · +91 83688 28660</a>
            </div>
          </div>
        </section>

        {/* STORIES */}
        <section className="pp-sec pp-sec-alt">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">Partner stories</span>
              <h2 className="pp-h2">Real partners. Real earnings.</h2>
              <p className="pp-sub">From small towns to top-tier neighborhoods — Switch partners are building real careers.</p>
            </div>
            <div className="pp-stories">
              {STORIES.map((s, i) => (
                <div className="pp-story" key={i}>
                  <div className="pp-story-top">
                    <img src={s.img} alt={`${s.name} — ${s.role}`} width="80" height="80" loading="lazy" />
                    <div>
                      <div className="pp-story-name">{s.name}</div>
                      <div className="pp-story-role">{s.role} · Gurgaon</div>
                      <div className="pp-story-stars"><Star/><Star/><Star/><Star/><Star/></div>
                    </div>
                  </div>
                  <p className="pp-story-text">“{s.text}”</p>
                </div>
              ))}
            </div>
            <div className="pp-mid-cta">
              <CtaPrimary>Join 500+ partners</CtaPrimary>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="pp-sec">
          <div className="pp-w">
            <div className="pp-sec-hd">
              <span className="pp-tag">Partner FAQ</span>
              <h2 className="pp-h2">Common questions.</h2>
              <p className="pp-sub">Everything you need to know before applying.</p>
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

        {/* FINAL */}
        <section className="pp-final">
          <div className="pp-final-inner">
            <span className="pp-final-tag">Ready when you are</span>
            <h2 className="pp-final-h">Start earning by tomorrow.</h2>
            <p className="pp-final-p">Download the Switch Partner app, submit your Aadhaar, and we’ll approve you within 24 hours. Daily payouts begin from your very first booking.</p>
            <div className="pp-final-ctas">
              <CtaPrimary big>Apply on the App</CtaPrimary>
              <a href="tel:+918368828660" className="pp-cta-secondary">📞 Call +91 83688 28660</a>
            </div>
            <div className="pp-final-row">
              <span><Check/> Free to join</span>
              <span><Check/> Daily payouts</span>
              <span><Check/> Verified jobs only</span>
              <span><Check/> Insurance included</span>
            </div>
          </div>
        </section>
      </main>

      {/* STICKY MOBILE CTA */}
      <div className="pp-sticky">
        <div className="pp-sticky-info">
          <strong>Earn ₹15K–40K/month</strong>
          <span>Daily payouts · Free to join</span>
        </div>
        <a href={APP_URL} className="pp-sticky-btn">Apply<Arrow size={14}/></a>
      </div>

      {/* FOOTER */}
      <footer className="pp-footer">
        <p>© 2026 Switch · <a href="tel:+918368828660">+91 83688 28660</a> · <a href="mailto:hello@switchlocally.com">hello@switchlocally.com</a> · <Link to="/">Home</Link></p>
      </footer>
    </div>
  )
}
