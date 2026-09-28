import { useState, useEffect } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import { getPageBySlug, SEO_PAGES } from '../data/seoData'
import { ROLES } from '../data/homeContent.js'
import { waLink } from '../data/site.js'
import SeoHead from '../components/SeoHead'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs, CtaFeature, Faq, HeroArt, ServiceRow, TrialTickets } from '../components/ui/Blocks.jsx'
import './SeoPage.css'

const APP = 'https://app.switchlocally.com'

/* Services that have a 3-hour trial ticket (Housekeeping / Kitchen Helper). */
const TRIAL_SERVICES = new Set(['home-cleaning', 'kitchen-helper'])

/* ─── MICRO COMPONENTS ─── */

function Stars() {
  return (
    <span className="sp-stars" aria-label="5 out of 5 stars">
      ★★★★★
    </span>
  )
}

function TrustBadges() {
  return (
    <div className="sw-checks">
      {['Aadhaar Verified', 'Background Checked', 'Transparent Billing', 'Same-Day Available'].map((x) => (
        <span className="sw-pill sw-live" key={x}>
          {x}
        </span>
      ))}
    </div>
  )
}

function Breadcrumb({ page }) {
  const items =
    page.type === 'landing'
      ? [[page.service]]
      : [
          [page.service, `/${page.serviceId}-gurgaon`],
          [page.h1],
        ]
  return <Crumbs items={items} />
}

/* Page hero: copy on the left, the service photo in the purple-blob arch. */
function SpHero({ page, tag, trust = false, children }) {
  return (
    <section className="sw-hero sp-hero">
      <div>
        <p className="sw-eyebrow">{tag}</p>
        <h1 className="sw-h1 sp-h1">{page.h1}</h1>
        <p className="sw-lead">{page.intro}</p>
        <div className="sw-btns">
          {children || (
            <>
              <a className="sw-btn" href={APP} target="_blank" rel="noreferrer">
                Book {page.service} <Icon name="arrow" />
              </a>
              <a
                className="sw-btn line"
                href={waLink(`Hi Switch — I'd like to book a ${page.service.toLowerCase()} in Gurgaon.`)}
                target="_blank"
                rel="noreferrer"
              >
                Ask on WhatsApp
              </a>
            </>
          )}
        </div>
        {trust && <TrustBadges />}
      </div>
      <HeroArt
        img={page.serviceImg}
        alt={`Hire a verified ${page.service.toLowerCase()} in Gurgaon`}
        badge={{ title: 'Available today', sub: 'in Gurgaon' }}
      />
    </section>
  )
}

/* A titled section with the shared sw-head (eyebrow, h2, lead). */
function Sec({ title, eyebrow, lead, children }) {
  return (
    <section className="sw-sec sp-sec">
      {(title || lead) && (
        <div className="sw-head">
          {eyebrow && <p className="sw-eyebrow">{eyebrow}</p>}
          {title && <h2 className="sw-h2">{title}</h2>}
          {lead && <p className="sw-lead">{lead}</p>}
        </div>
      )}
      {children}
    </section>
  )
}

function CheckList({ items, arrow = false }) {
  if (!items?.length) return null
  return (
    <div className="sw-card sp-list">
      <ul className="sw-list-check">
        {items.map((t, i) => (
          <li key={i}>
            <Icon name={arrow ? 'arrow' : 'check'} className={arrow ? 'sp-arrow' : ''} />
            <span>{t}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PricingTable({ prices }) {
  if (!prices?.length) return null
  return (
    <div className="sw-grid sw-g4 sp-prices">
      {prices.map((p, i) => (
        <div className="sw-card sw-rate" key={i}>
          <span className="sw-pill">{p.label}</span>
          <b>{p.price}</b>
          <p className="sw-muted sp-small">{p.desc}</p>
        </div>
      ))}
    </div>
  )
}

function Steps({ steps }) {
  return (
    <div className="sw-grid sw-g3">
      {steps.map((s, i) => (
        <div className="sw-card sw-step" key={i}>
          <span className="n">STEP {s.n}</span>
          <h3 className="sw-h3">{s.title}</h3>
          <p>{s.desc}</p>
        </div>
      ))}
    </div>
  )
}

function ComparisonTable({ service }) {
  const rows = [
    ['Booking time', 'Under 2 min', '24–48 hrs', 'Hours or days'],
    ['Background verified', '✓ Aadhaar', 'Sometimes', 'Never'],
    ['Transparent pricing', '✓ Fixed rate', '+ Commission', 'Variable'],
    ['Transparent billing', '✓', '✗', '✗'],
    ['Same-day available', '✓', 'Rare', 'Rare'],
    ['Free cancellation', '✓ Up to 2 hrs', 'Fee charged', 'N/A'],
    ['Rated & reviewed', '✓ 4.8 ★', '✗', '✗'],
  ]
  return (
    <div className="sw-table sp-compare">
      <table>
        <thead>
          <tr>
            <th>Hiring a {service.toLowerCase()}</th>
            <th className="sp-sw">Switch</th>
            <th>Agency / Broker</th>
            <th>Find Yourself</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([feat, sw, ag, fy], i) => (
            <tr key={i}>
              <td className="sp-feat">{feat}</td>
              <td className="sp-sw sp-good">{sw}</td>
              <td className="sw-muted">{ag}</td>
              <td className="sw-muted">{fy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Areas({ areas }) {
  if (!areas?.length) return null
  return (
    <div className="sw-chips sp-chips">
      {areas.map((a, i) => (
        <span className="sw-chip" key={i}>
          <Icon name="pin" />
          {a}
        </span>
      ))}
    </div>
  )
}

function Reviews({ reviews }) {
  if (!reviews?.length) return null
  return (
    <div className="sw-grid sw-g3">
      {reviews.map((r, i) => (
        <figure className="sw-card sw-q sp-review" key={i}>
          <Stars />
          <blockquote>“{r.text}”</blockquote>
          <cite>{r.name}</cite>
        </figure>
      ))}
    </div>
  )
}

function FaqList({ faqs }) {
  if (!faqs?.length) return null
  return <Faq items={faqs} />
}

function RelatedPages({ serviceId, currentSlug }) {
  const related = SEO_PAGES.filter((p) => p.serviceId === serviceId && p.slug !== currentSlug).slice(0, 9)
  const roles = ROLES.filter((r) => r.slug !== `${serviceId}-gurgaon`)
  return (
    <>
      {related.length > 0 && (
        <Sec title={`More ${related[0].service} pages`}>
          <div className="sw-chips">
            {related.map((p) => (
              <Link key={p.slug} to={`/${p.slug}`} className="sw-chip sp-link-chip">
                {p.h1}
                <Icon name="arrow" />
              </Link>
            ))}
          </div>
        </Sec>
      )}
      <Sec eyebrow="Other roles we staff" title="Related services in Gurgaon">
        <div className="sw-grid sw-g2">
          {roles.map((r) => (
            <ServiceRow key={r.slug} to={`/${r.slug}`} img={r.img} name={r.name} desc={r.desc} tags={r.tags} />
          ))}
        </div>
      </Sec>
    </>
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
    <div className={`sw-bar sp-sticky${visible ? ' is-on' : ''}`} aria-hidden={!visible}>
      <a href={APP} tabIndex={visible ? undefined : -1}>
        <span>
          <b>Book {service} Now</b>
          <small>Verified · same-day in Gurgaon</small>
        </span>
        <span className="gob">
          Book <Icon name="arrow" />
        </span>
      </a>
    </div>
  )
}

/* ─── PAGE TYPE RENDERERS ─── */

function LandingPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Gurgaon · Book Instantly · Verified Switch Players" trust>
        <a className="sw-btn" href={APP} target="_blank" rel="noreferrer">
          Book Now — Free App <Icon name="arrow" />
        </a>
        <Link className="sw-btn line" to={`/${page.serviceId}-cost-gurgaon`}>
          View Pricing
        </Link>
      </SpHero>

      {page.uniqueSection && (
        <Sec title={page.uniqueSection.heading}>
          <div className="sw-card sp-prose">
            {page.uniqueSection.paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
            {page.uniqueSection.chipGroups?.map((g, i) => (
              <div key={i} className="sp-group">
                <h3 className="sw-h3">{g.title}</h3>
                <Areas areas={g.chips} />
              </div>
            ))}
          </div>
        </Sec>
      )}

      <Sec title={`What a ${page.service} Does for You`} lead={page.longDesc}>
        <CheckList items={page.tasks} />
      </Sec>

      <Sec
        title="Transparent Pricing — No Hidden Fees"
        lead="All rates are fixed and shown upfront. No agency commission, no call-out fees, no surprises. You pay against a clear invoiced to your satisfaction."
      >
        <PricingTable prices={page.prices} />
      </Sec>

      <Sec title="How It Works — 3 Simple Steps">
        <Steps
          steps={[
            {
              n: 1,
              title: `Choose ${page.service}`,
              desc: `Open the Switch app, select ${page.service.toLowerCase()} and pick your duration — from 4 hours to 7 days.`,
            },
            {
              n: 2,
              title: 'Set time & address',
              desc: 'Pick your date, time and Gurgaon address. Confirm in under 2 minutes — no calls, no paperwork.',
            },
            {
              n: 3,
              title: 'Switch Player arrives & the work gets done',
              desc: `Your verified ${page.service.toLowerCase()} arrives on time. Pay securely in-app only after the job is done.`,
            },
          ]}
        />
      </Sec>

      <Sec
        title="Switch vs Other Options"
        lead="See why Gurgaon residents book through Switch instead of agencies or finding Switch Players themselves."
      >
        <ComparisonTable service={page.service} />
      </Sec>

      <Sec title="Why Choose Switch?">
        <CheckList items={page.benefits} />
      </Sec>

      <Sec title="What Customers Say">
        <Reviews reviews={page.reviews} />
      </Sec>

      <Sec
        title="Areas We Serve in Gurgaon"
        lead={`Switch ${page.service.toLowerCase()} bookings are available across all major sectors and localities in Gurgaon. Check the app for real-time availability in your area.`}
      >
        <Areas areas={page.areas} />
      </Sec>

      <Sec title="Frequently Asked Questions">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function PricingPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Transparent Pricing · No Hidden Fees · Clean Invoices" />
      <Sec title="Rate Card">
        <PricingTable prices={page.prices} />
        <div className="sp-gap">
          <CheckList items={page.pricingNotes} />
        </div>
      </Sec>
      <Sec title="What's Included at Every Price">
        <CheckList items={page.tasks} />
      </Sec>
      <Sec title="Switch vs Agency Pricing">
        <ComparisonTable service={page.service} />
      </Sec>
      <Sec title="Pricing FAQs">
        <FaqList faqs={page.faqs} />
      </Sec>
      <Sec title="Available in These Areas">
        <Areas areas={page.areas} />
      </Sec>
    </>
  )
}

function HowToHirePage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Step-by-Step Guide · No Agency Needed" />
      <Sec title="3 Steps to Book on Switch">
        <Steps steps={page.steps} />
      </Sec>
      <Sec title="Tips Before You Book">
        <CheckList items={page.tips} />
      </Sec>
      <Sec title="What They Can Do for You">
        <CheckList items={page.tasks} />
      </Sec>
      <Sec title="Common Questions About Hiring">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function BenefitsPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Why Switch · Gurgaon's Top-Rated Platform" />
      <Sec title="Top Benefits">
        <CheckList items={page.benefits} />
      </Sec>
      <Sec title={`When to Hire a ${page.service}`}>
        <CheckList items={page.useCases} arrow />
      </Sec>
      <Sec title="Switch vs Other Options">
        <ComparisonTable service={page.service} />
      </Sec>
      <Sec title="Full Task List">
        <CheckList items={page.tasks} />
      </Sec>
      <Sec title="Questions">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function ChecklistPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Full Task Checklist · No Surprises" />
      <Sec title="Task Breakdown by Category">
        <div className="sw-grid sw-g4 sp-cats">
          {page.checklistCategories.map((cat, i) => (
            <div className="sw-card sp-cat" key={i}>
              <h3 className="sw-h3">{cat.cat}</h3>
              <ul className="sw-list-check">
                {cat.items.map((item, j) => (
                  <li key={j}>
                    <Icon name="check" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Sec>
      <Sec title="Full Task List">
        <CheckList items={page.tasks} />
      </Sec>
      <Sec title="Pricing">
        <PricingTable prices={page.prices} />
      </Sec>
      <Sec title="Frequently Asked Questions">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function FaqPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="All Your Questions Answered" />
      <Sec title="All FAQs">
        <FaqList faqs={page.faqs} />
      </Sec>
      <Sec title="Pricing at a Glance">
        <PricingTable prices={page.prices} />
      </Sec>
      <Sec title="Serving These Areas in Gurgaon">
        <Areas areas={page.areas} />
      </Sec>
    </>
  )
}

function NearMePage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Nearest Available · Gurgaon" trust>
        <a className="sw-btn" href={APP} target="_blank" rel="noreferrer">
          Find One Near You <Icon name="arrow" />
        </a>
      </SpHero>
      <Sec
        title="Areas We Cover in Gurgaon"
        lead="Don't see your area? Open the Switch app — we are expanding coverage across Gurgaon every week. Enter your location to check real-time availability in your sector."
      >
        <Areas areas={page.areas} />
      </Sec>
      <Sec title="Why Location Matters">
        <CheckList
          items={[
            'Nearby Switch Players arrive faster — less waiting time',
            'Lower travel overhead means better value for you',
            'Switch Players familiar with your area navigate easily',
            'Same-day slots more likely when Switch Player is local to your sector',
          ]}
        />
      </Sec>
      <Sec title="What They Can Do">
        <CheckList items={page.tasks} />
      </Sec>
      <Sec title="Pricing">
        <PricingTable prices={page.prices} />
      </Sec>
      <Sec title="Frequently Asked Questions">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function SameDayPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Urgent Booking · Confirmed Within Hours · No Surge" trust>
        <a className="sw-btn" href={APP} target="_blank" rel="noreferrer">
          Book for Today <Icon name="arrow" />
        </a>
      </SpHero>
      <Sec title="How Same-Day Booking Works">
        <Steps steps={page.steps} />
      </Sec>
      <Sec title="Why Switch for Urgent Jobs">
        <CheckList items={page.benefits} />
      </Sec>
      <Sec title="Same-Day Pricing — No Extra Charge">
        <PricingTable prices={page.prices} />
      </Sec>
      <Sec title="Questions About Same-Day Booking">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function ReviewsPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="Verified Customer Reviews · 4.8 ★ Average" />
      <Sec title="Customer Stories">
        <div className="sw-card sp-rating">
          <b>4.8 ★</b>
          <span>Average from verified {page.service.toLowerCase()} bookings in Gurgaon</span>
        </div>
        <Reviews reviews={page.reviews} />
      </Sec>
      <Sec title="Why They Keep Coming Back">
        <CheckList items={page.benefits} />
      </Sec>
      <Sec title="Pricing">
        <PricingTable prices={page.prices} />
      </Sec>
      <Sec title="Frequently Asked Questions">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

function VerifiedPage({ page }) {
  return (
    <>
      <SpHero page={page} tag="3-Step Verification · Aadhaar · Background Checked · Skills Tested" />
      <Sec title="How We Verify Every Switch Player">
        <div className="sw-grid sw-g3">
          {page.verificationSteps.map((v, i) => (
            <div className="sw-card sw-step" key={i}>
              <span className="sp-num">{i + 1}</span>
              <h3 className="sw-h3">{v.title}</h3>
              <p>{v.desc}</p>
            </div>
          ))}
        </div>
      </Sec>
      <Sec title="What Verified Switch Players Can Do">
        <CheckList items={page.tasks} />
      </Sec>
      <Sec title="Switch vs Unverified Alternatives">
        <ComparisonTable service={page.service} />
      </Sec>
      <Sec title="Benefits of Booking Verified">
        <CheckList items={page.benefits} />
      </Sec>
      <Sec title="Pricing">
        <PricingTable prices={page.prices} />
      </Sec>
      <Sec title="FAQs About Verification">
        <FaqList faqs={page.faqs} />
      </Sec>
    </>
  )
}

/* ─── MAIN SEO PAGE ─── */

const PAGE_RENDERERS = {
  landing: LandingPage,
  pricing: PricingPage,
  'how-to-hire': HowToHirePage,
  benefits: BenefitsPage,
  checklist: ChecklistPage,
  faq: FaqPage,
  'near-me': NearMePage,
  'same-day': SameDayPage,
  reviews: ReviewsPage,
  verified: VerifiedPage,
}

export default function SeoPage() {
  const { slug } = useParams()
  const page = getPageBySlug(slug)

  if (!page) return <Navigate to="/" replace />

  const Renderer = PAGE_RENDERERS[page.type]

  return (
    <>
      <SeoHead page={page} />
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />

      <main id="page-main" className="sw-wrap sp-main">
        <Breadcrumb page={page} />
        <Renderer page={page} />
        {TRIAL_SERVICES.has(page.serviceId) && <TrialTickets id="trial" />}
        <RelatedPages serviceId={page.serviceId} currentSlug={page.slug} />
        <CtaFeature
          title={
            <>
              Book a {page.service} in Gurgaon <em>today.</em>
            </>
          }
          sub="Verified professionals. Flexible hours. Transparent rates, no hidden charges. Rated 4.8 ★ · 1,500+ businesses served."
          msg={`Hi Switch — I'd like to book a ${page.service.toLowerCase()} in Gurgaon.`}
          photos={[page.serviceImg, page.serviceImg === '/sw-general-helper.jpg' ? '/sw-security-guard.jpg' : '/sw-general-helper.jpg']}
        />
      </main>

      <Footer />

      <StickyCTA service={page.service} />
    </>
  )
}
