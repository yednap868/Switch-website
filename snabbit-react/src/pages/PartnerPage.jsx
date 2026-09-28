import { useEffect, useState } from 'react'
import { Helmet } from 'react-helmet-async'
import './PartnerPage.css'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs, Faq, HeroArt, StatsRow } from '../components/ui/Blocks.jsx'
import { PHONE_DISPLAY, trackWhatsApp, waLink } from '../data/site.js'

/* Workers apply on WhatsApp — the Switch app on the stores is the employer app. */
const APPLY_WA = waLink('Hi Switch — I want to work as a Switch Player in Gurgaon.')

const TINTS = ['t-lav', 't-mint', 't-sky', 't-peach', 't-pink', 't-lav', 't-sky', 't-mint']

const BENEFITS = [
  { ico: 'wallet',   title: 'Earn ₹15,000–₹40,000/month', desc: 'Flexible bookings — work part-time or full-time. No agency cuts, no middlemen.' },
  { ico: 'timer',    title: 'Daily payouts to your bank', desc: 'Finish work today, money in your account tomorrow. Direct UPI / bank transfers — every single day.' },
  { ico: 'cal',      title: 'You pick your hours',        desc: 'Choose your availability — 4-hour shifts, full days, or week-long gigs. Total flexibility.' },
  { ico: 'shield',   title: 'Verified, trusted jobs',     desc: 'All customers are app-verified. No fake bookings, no last-minute cancellations, no chasing payments.' },
  { ico: 'star',     title: 'Build your reputation',      desc: 'Higher ratings unlock higher hourly rates and premium clients. Your work earns you growth.' },
  { ico: 'book',     title: 'Free skill training',        desc: 'Free training modules and certifications across 12+ categories. Level up, earn more per hour.' },
  { ico: 'heart',    title: 'Insurance & safety cover',   desc: 'On-duty insurance and a 24×7 helpline. Your safety on every booking is non-negotiable.' },
  { ico: 'sparkles', title: 'Same-day approval',          desc: 'Apply today, get verified within 24 hours, start earning the very next day. No waiting.' },
]

const STEPS = [
  { n: '01', title: 'Apply on WhatsApp',         desc: 'Message us on WhatsApp and share your Aadhaar and a selfie. Takes under 5 minutes.' },
  { n: '02', title: 'Get verified',              desc: 'Aadhaar + background + skills check. Same-day approval for most applicants.' },
  { n: '03', title: 'Accept your first booking', desc: 'Browse nearby jobs that match your skills, hours, and preferred area. Pick what works.' },
  { n: '04', title: 'Get paid daily',            desc: 'Complete the job, get rated, and receive payment directly to your bank — within 24 hours.' },
]

const CATEGORIES = [
  { name: 'Cook',           pay: '₹109–129/hr' },
  { name: 'Cleaning Staff', pay: '₹99–119/hr' },
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
  { value: '20,000+', label: 'Active partners' },
  { value: '₹40K',    label: 'Top monthly earner' },
  { value: '24 hrs',  label: 'Approval time' },
  { value: '4.9 ★',   label: 'Partner rating' },
]

const STORIES = [
  { img: '/sw-cook.jpg',            name: 'Ramesh K.',  role: 'Cook',           text: 'I used to earn ₹12,000 in a restaurant. With Switch, I make ₹38,000 working only mornings. I pick my own hours now.' },
  { img: '/sw-maid.jpg',            name: 'Priya S.',   role: 'Cleaning Staff', text: 'I started with one booking a week. After 4 months of 5★ ratings, I’m booked solid — full 8-hour days, every day.' },
  { img: '/sw-security-guard.jpg',  name: 'Vikram T.',  role: 'Security Guard', text: 'No middleman, no agency fee. Whatever the client pays, that’s what I take home. Best decision I made.' },
]

const FAQS = [
  { q: 'How much can I really earn?',           a: 'Most partners earn ₹15,000–₹40,000 per month based on hours, category, and ratings. Top-rated bartenders and bouncers can reach the upper end of that range.' },
  { q: 'Do I pay anything to join?',            a: 'No. Joining is 100% free. We only take a small platform fee from each completed booking — never upfront.' },
  { q: 'When do I get paid?',                   a: 'Daily. Finish your booking, get rated, and the money lands in your bank or UPI within 24 hours. No monthly cycles.' },
  { q: 'Can I choose which jobs to accept?',    a: 'Yes. You see every nearby job on the app and decide. Skip what doesn’t fit, accept what does. Full control.' },
  { q: 'What documents do I need?',             a: 'Just an Aadhaar and a smartphone. Bouncers may need a fitness declaration.' },
  { q: 'How long does verification take?',      a: 'Same day for most applicants. Background-check heavy categories (bouncer, security guard) may take up to 48 hours.' },
  { q: 'Is there an insurance cover?',          a: 'Yes — every Switch partner is covered by on-duty accident insurance and a 24×7 emergency helpline.' },
  { q: 'Can I work in more than one category?', a: 'Absolutely. Many partners are verified in 2–3 categories (e.g., Cook + Kitchen Helper) which doubles their booking opportunities.' },
]

function Apply({ children = 'Apply on WhatsApp', className = '', label = 'partner_apply' }) {
  return (
    <a
      href={APPLY_WA}
      target="_blank"
      rel="noopener noreferrer"
      className={`sw-btn ${className}`}
      onClick={() => trackWhatsApp(label)}
    >
      {children} <Icon name="arrow" />
    </a>
  )
}

const inr = (n) => `₹${n.toLocaleString('en-IN')}`

export default function PartnerPage() {
  useEffect(() => { if (!window.location.hash) window.scrollTo(0, 0) }, [])

  const [hours, setHours] = useState(8)
  const [rate, setRate]   = useState(119)
  const monthly = hours * rate * 30
  const daily   = hours * rate

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title: 'Switch Partner — Earn ₹15,000–₹40,000/month with Daily Payouts',
    description: 'Join Switch as a verified partner. Earn ₹15,000–₹40,000 per month with flexible hours and DAILY bank payouts. Work as a cook, cleaner, security guard, helper, bartender, bouncer, or waiter.',
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
    <>
      <Helmet>
        <title>Become a Switch Partner — Daily Payouts · Earn ₹15K–40K/month in Gurgaon</title>
        <meta name="description" content="Join Switch as a verified partner. Earn ₹15,000–₹40,000/month with DAILY bank payouts. Work as a cook, cleaner, security guard, helper, bouncer, bartender or waiter in Gurgaon. Free to join, same-day approval." />
        <link rel="canonical" href="https://switchlocally.com/partner" />
        <script type="application/ld+json">{JSON.stringify(schema)}</script>
      </Helmet>

      <a className="skip-link" href="#page-main">Skip to main content</a>
      <Header />

      <main id="page-main" className="sw-wrap pp">
        <Crumbs items={[['Become a Switch Player']]} />

        {/* HERO */}
        <section className="sw-hero">
          <div>
            <span className="sw-pill sw-live">Now hiring in Gurgaon · 20,000+ partners onboard</span>
            <h1 className="sw-h1" style={{ marginTop: 14 }}>
              Earn ₹40,000/month. <em>Get paid daily.</em>
            </h1>
            <p className="sw-lead">
              Switch is India’s premium platform for verified blue-collar professionals.
              Pick your hours, pick your jobs, and receive your earnings in your bank
              <strong> every single day</strong>. No agency cuts. No waiting.
            </p>
            <div className="sw-btns">
              <Apply label="partner_hero" />
              <a href="#earnings" className="sw-btn line">See earnings</a>
            </div>
            <div className="pp-rating">
              <span className="pp-stars" aria-hidden="true">★★★★★</span>
              <span>Rated <strong>4.9</strong> by Switch partners across Gurgaon</span>
            </div>
          </div>
          <HeroArt
            img="/delivery-rider.jpg"
            badge={{ icon: 'wallet', title: 'Paid daily', sub: 'In your bank by 11 AM' }}
          />
        </section>

        <StatsRow items={TRUST} />

        {/* EARNINGS CALCULATOR */}
        <section className="sw-sec" id="earnings">
          <div className="sw-head">
            <p className="sw-eyebrow">Earnings</p>
            <h2 className="sw-h2">See exactly <em>what you can earn.</em></h2>
            <p className="sw-lead">Adjust your daily hours and hourly rate. Earnings update live.</p>
          </div>

          <div className="sw-card pp-calc">
            <div className="pp-calc-controls">
              <div className="pp-ctrl">
                <div className="pp-ctrl-top">
                  <label htmlFor="pp-hours">Hours per day</label>
                  <span className="pp-ctrl-val">{hours} hrs</span>
                </div>
                <input id="pp-hours" type="range" min="4" max="12" value={hours} onChange={(e) => setHours(+e.target.value)} />
                <div className="pp-ctrl-scale"><span>4</span><span>8</span><span>12</span></div>
              </div>
              <div className="pp-ctrl">
                <div className="pp-ctrl-top">
                  <label htmlFor="pp-rate">Hourly rate</label>
                  <span className="pp-ctrl-val">₹{rate}</span>
                </div>
                <input id="pp-rate" type="range" min="99" max="129" step="1" value={rate} onChange={(e) => setRate(+e.target.value)} />
                <div className="pp-ctrl-scale"><span>₹99</span><span>₹114</span><span>₹129</span></div>
              </div>
              <div className="pp-calc-side">
                <div className="pp-mini">
                  <span>Daily payout</span>
                  <b>{inr(daily)}</b>
                  <small>In your bank by 11 AM next day</small>
                </div>
                <div className="pp-mini">
                  <span>Weekly total</span>
                  <b>{inr(daily * 7)}</b>
                  <small>7-day work week</small>
                </div>
              </div>
            </div>

            <div className="pp-calc-out" aria-live="polite">
              <p className="sw-eyebrow">Estimated monthly earnings</p>
              <div className="pp-calc-big">{inr(monthly)}</div>
              <p className="sw-muted">Based on 30 working days. Paid daily to your bank.</p>
              <Apply label="partner_calc" />
            </div>
          </div>
        </section>

        {/* BENEFITS */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Why Switch</p>
            <h2 className="sw-h2">Built for Switch Players who <em>want freedom.</em></h2>
            <p className="sw-lead">No agency cuts. No middlemen. No hidden fees. Just real jobs, real pay, real growth.</p>
          </div>
          <div className="sw-grid sw-g4">
            {BENEFITS.map((b, i) => (
              <div className="sw-card sw-ind" key={b.title}>
                <span className={`sw-sq ${TINTS[i % TINTS.length]}`}>
                  <Icon name={b.ico} />
                </span>
                <h3 className="sw-h3">{b.title}</h3>
                <p>{b.desc}</p>
              </div>
            ))}
          </div>
          <div className="pp-mid-cta">
            <Apply label="partner_benefits" />
          </div>
        </section>

        {/* HOW TO JOIN */}
        <section className="sw-sec" id="how-to-join">
          <div className="sw-head">
            <p className="sw-eyebrow">How to join</p>
            <h2 className="sw-h2">4 steps to your <em>first booking.</em></h2>
            <p className="sw-lead">Apply today. Start earning tomorrow.</p>
          </div>
          <div className="sw-grid sw-g4">
            {STEPS.map((s) => (
              <div className="sw-card sw-step" key={s.n}>
                <span className="n">STEP {s.n}</span>
                <h3 className="sw-h3">{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            ))}
          </div>
          <div className="pp-mid-cta">
            <Apply label="partner_steps" />
          </div>
        </section>

        {/* CATEGORIES + ELIGIBILITY */}
        <section className="sw-sec">
          <div className="sw-two">
            <div>
              <div className="sw-head">
                <p className="sw-eyebrow">Categories &amp; rates</p>
                <h2 className="sw-h2">Pick what you’re <em>great at.</em></h2>
                <p className="sw-lead">Live hourly rates across our 12 verified categories. Apply for one or several — many partners run two.</p>
              </div>
              <div className="pp-rate-grid">
                {CATEGORIES.map((c) => (
                  <div className="sw-card pp-rate" key={c.name}>
                    <span>{c.name}</span>
                    <b>{c.pay}</b>
                  </div>
                ))}
              </div>
            </div>
            <div className="sw-card pp-req">
              <span className="sw-sq t-mint"><Icon name="check" /></span>
              <h3 className="sw-h3">Eligibility</h3>
              <ul className="sw-list-check">
                {REQUIREMENTS.map((r) => (
                  <li key={r}><Icon name="check" />{r}</li>
                ))}
              </ul>
              <Apply label="partner_eligibility" />
              <a
                href={APPLY_WA}
                target="_blank"
                rel="noopener noreferrer"
                className="sw-link"
                onClick={() => trackWhatsApp('partner_eligibility_phone')}
              >
                or WhatsApp · {PHONE_DISPLAY}
              </a>
            </div>
          </div>
        </section>

        {/* STORIES */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Partner stories</p>
            <h2 className="sw-h2">Real partners. <em>Real earnings.</em></h2>
            <p className="sw-lead">From small towns to top-tier neighborhoods — Switch partners are building real careers.</p>
          </div>
          <div className="sw-grid sw-g4">
            {STORIES.map((s) => (
              <figure className="sw-card pp-story" key={s.name}>
                <div className="pp-story-top">
                  <img src={s.img} alt={`${s.name} — ${s.role}`} width="56" height="56" loading="lazy" />
                  <div>
                    <b>{s.name}</b>
                    <span>{s.role} · Gurgaon</span>
                  </div>
                </div>
                <span className="pp-stars" aria-label="5 out of 5 stars">★★★★★</span>
                <blockquote>“{s.text}”</blockquote>
              </figure>
            ))}
          </div>
          <div className="pp-mid-cta">
            <Apply label="partner_stories">Join 20,000+ partners</Apply>
          </div>
        </section>

        {/* FAQ */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">Partner FAQ</p>
            <h2 className="sw-h2">Common <em>questions.</em></h2>
            <p className="sw-lead">Everything you need to know before applying.</p>
          </div>
          <Faq items={FAQS} />
        </section>

        {/* FINAL */}
        <section className="sw-sec">
          <div className="sw-feature sw-feature-grid">
            <div>
              <p className="sw-eyebrow">Ready when you are</p>
              <h2 style={{ marginTop: 10 }}>Start earning <em>by tomorrow.</em></h2>
              <p style={{ marginTop: 10, maxWidth: '52ch' }}>
                Message us on WhatsApp, submit your Aadhaar, and we’ll approve you within 24 hours.
                Daily payouts begin from your very first booking.
              </p>
              <div className="sw-btns" style={{ marginTop: 18 }}>
                <Apply className="white" label="partner_final" />
                <a
                  href={APPLY_WA}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="sw-btn line"
                  onClick={() => trackWhatsApp('partner_final_phone')}
                >
                  WhatsApp {PHONE_DISPLAY}
                </a>
              </div>
              <ul className="pp-final-row">
                {['Free to join', 'Daily payouts', 'Verified jobs only', 'Insurance included'].map((x) => (
                  <li key={x}><Icon name="check" />{x}</li>
                ))}
              </ul>
            </div>
            <div className="sw-f-art" aria-hidden="true">
              <div className="sw-blob" />
              <div className="sw-arch a1">
                <img src="/sw-general-helper.jpg" alt="" loading="lazy" />
              </div>
              <div className="sw-arch a2">
                <img src="/sw-cook.jpg" alt="" loading="lazy" />
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />

      {/* STICKY MOBILE CTA */}
      <div className="sw-bar pp-bar" aria-label="Quick actions">
        <a href={APPLY_WA} target="_blank" rel="noopener noreferrer" onClick={() => trackWhatsApp('partner_sticky')}>
          <span>
            <b>Earn ₹15K–40K/month</b>
            <small>Daily payouts · Free to join</small>
          </span>
          <span className="gob">
            Apply <Icon name="arrow" />
          </span>
        </a>
      </div>
    </>
  )
}
