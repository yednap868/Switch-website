import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import { GURGAON_AREAS, INDUSTRY_PAGES, getIndustryPage } from '../data/industryPages.js'
import { APP_URL, EMAIL, PHONE, waLink } from '../data/site.js'
import './IndustryPage.css'

const BASE_URL = 'https://switchlocally.com'
const pad = (n) => String(n + 1).padStart(2, '0')

/* "Hire X Staff" books through the app; "Talk to Switch" and
   "Tell Us What You Need" open WhatsApp with the page's context. */
function HireCta({ page, className = 'btn primary' }) {
  return (
    <a href={APP_URL} className={className}>
      {page.hero.cta} <b>→</b>
    </a>
  )
}

function NeedCta({ page, className = 'btn ghost' }) {
  return (
    <a href={waLink(page.waMsg)} target="_blank" rel="noreferrer" className={className}>
      Tell Us What You Need <b>→</b>
    </a>
  )
}

function SectionHead({ s }) {
  return (
    <div className="section-head">
      <div>
        <span className="eyebrow">{s.eyebrow}</span>
        <h2>{s.h2}</h2>
      </div>
      {s.lead && <p>{s.lead}</p>}
    </div>
  )
}

function Intro({ s, page }) {
  return (
    <div className="ind-intro">
      <div>
        <span className="eyebrow">{s.eyebrow}</span>
        <h2 className="ind-h2">{s.h2}</h2>
      </div>
      <div className="ind-intro-body">
        {s.paras.map((p) => (
          <p key={p}>{p}</p>
        ))}
        <aside className="ind-callout">
          <strong>{s.callout.title}</strong>
          <p>{s.callout.text}</p>
          <NeedCta page={page} className="btn primary" />
        </aside>
      </div>
    </div>
  )
}

function Roles({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <div className="ind-roles">
        {s.groups.map((g, i) => (
          <div className="ind-role" key={g.name}>
            <span className="eyebrow">{pad(i)}</span>
            <h3>{g.name}</h3>
            <ul>
              {g.roles.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            {g.desc && <p>{g.desc}</p>}
          </div>
        ))}
      </div>
      <div className="ind-actions">
        <HireCta page={page} />
      </div>
    </>
  )
}

function Cards({ s }) {
  return (
    <>
      <SectionHead s={s} />
      <div className="reasons ind-cards">
        {s.items.map((c, i) => (
          <div className="reason" key={c.title}>
            <span className="eyebrow">{pad(i)}</span>
            <b>{c.title}</b>
            <p>{c.desc}</p>
          </div>
        ))}
      </div>
    </>
  )
}

function Flow({ s }) {
  return (
    <>
      <SectionHead s={s} />
      <ol className="ind-flow" style={{ '--n': s.items.length }}>
        {s.items.map((f, i) => (
          <li key={f.title}>
            <span className="ind-flow-num">{pad(i)}</span>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </li>
        ))}
      </ol>
    </>
  )
}

function List({ s }) {
  return (
    <>
      <SectionHead s={s} />
      <ul className="ind-chips">
        {s.items.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
    </>
  )
}

function Table({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <div className="ind-table" role="table">
        <div className="ind-table-row ind-table-head" role="row">
          {s.cols.map((c) => (
            <span role="columnheader" key={c}>{c}</span>
          ))}
        </div>
        {s.rows.map(([need, how]) => (
          <div className="ind-table-row" role="row" key={need}>
            <span role="cell">{need}</span>
            <span role="cell">{how}</span>
          </div>
        ))}
      </div>
      {s.cta && (
        <div className="ind-actions">
          <HireCta page={page} />
        </div>
      )}
    </>
  )
}

function Why({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <div className="reasons ind-why">
        {s.items.map((w, i) => (
          <div className={`reason${w.cta ? ' ind-why-cta' : ''}`} key={w.title}>
            <span className="eyebrow">{pad(i)}</span>
            <b>{w.title}</b>
            <p>{w.desc}</p>
            {w.cta && <NeedCta page={page} className="text-link" />}
          </div>
        ))}
      </div>
    </>
  )
}

function Steps({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <ol className="ind-steps">
        {s.items.map((st, i) => (
          <li key={st.title}>
            <span className="eyebrow">Step {i + 1}</span>
            <h3>{st.title}</h3>
            <p>{st.desc}</p>
          </li>
        ))}
      </ol>
      <div className="ind-actions">
        <HireCta page={page} />
      </div>
    </>
  )
}

function Areas({ s, page }) {
  return (
    <div className="ind-areas">
      <div>
        <span className="eyebrow">{s.eyebrow}</span>
        <h2 className="ind-h2">{s.h2}</h2>
        <p className="ind-muted">{s.lead}</p>
      </div>
      <div>
        <ul className="ind-area-list">
          {GURGAON_AREAS.map((a) => (
            <li key={a}>
              <i aria-hidden="true" />
              {a}
            </li>
          ))}
        </ul>
        <p className="ind-area-note">
          Need staff somewhere else in Gurgaon? Tell us your location and we&apos;ll confirm
          availability.{' '}
          <a
            className="text-link"
            href={waLink(`${page.waMsg} My location is: `)}
            target="_blank"
            rel="noreferrer"
          >
            Check your area →
          </a>
        </p>
      </div>
    </div>
  )
}

function Faq({ s }) {
  return (
    <div className="ind-faq">
      <div>
        <span className="eyebrow">{s.eyebrow}</span>
        <h2 className="ind-h2">{s.h2}</h2>
      </div>
      <div className="ind-faq-list">
        {s.items.map((f) => (
          <details key={f.q}>
            <summary>{f.q}</summary>
            <p>{f.a}</p>
          </details>
        ))}
      </div>
    </div>
  )
}

const RENDERERS = {
  intro: Intro,
  roles: Roles,
  cards: Cards,
  flow: Flow,
  list: List,
  table: Table,
  why: Why,
  steps: Steps,
  areas: Areas,
  faq: Faq,
}

function IndustryHead({ page }) {
  const canonical = `${BASE_URL}/${page.slug}`
  const faq = page.sections.find((s) => s.type === 'faq')
  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${BASE_URL}/` },
      { '@type': 'ListItem', position: 2, name: 'Staffing in Gurgaon', item: `${BASE_URL}/staffing-gurgaon` },
      { '@type': 'ListItem', position: 3, name: page.hero.eyebrow, item: canonical },
    ],
  }
  const service = {
    '@context': 'https://schema.org',
    '@type': 'Service',
    serviceType: page.name,
    name: page.hero.eyebrow,
    description: page.description,
    url: canonical,
    areaServed: [
      { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
      ...GURGAON_AREAS.map((n) => ({ '@type': 'Place', name: `${n}, Gurgaon` })),
    ],
    provider: {
      '@type': 'LocalBusiness',
      name: 'Switch',
      url: BASE_URL,
      email: EMAIL,
      telephone: PHONE,
      areaServed: { '@type': 'City', name: 'Gurgaon' },
    },
  }
  const faqSchema = faq && {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faq.items.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  }
  return (
    <Helmet>
      <title>{page.title}</title>
      <meta name="description" content={page.description} />
      <meta name="keywords" content={page.keywords} />
      <meta name="robots" content="index, follow" />
      <meta name="geo.region" content="IN-HR" />
      <meta name="geo.placename" content="Gurgaon" />
      <meta name="geo.position" content="28.4595;77.0266" />
      <meta name="ICBM" content="28.4595, 77.0266" />
      <link rel="canonical" href={canonical} />
      <meta property="og:title" content={page.title} />
      <meta property="og:description" content={page.description} />
      <meta property="og:url" content={canonical} />
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="Switch" />
      <meta property="og:image" content={`${BASE_URL}/hero-workers.jpg`} />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={page.title} />
      <meta name="twitter:description" content={page.description} />
      <meta name="twitter:image" content={`${BASE_URL}/hero-workers.jpg`} />
      <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
      <script type="application/ld+json">{JSON.stringify(service)}</script>
      {faqSchema && <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>}
    </Helmet>
  )
}

export default function IndustryPage({ slug }) {
  const page = getIndustryPage(slug)

  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0)
  }, [slug])

  const others = INDUSTRY_PAGES.filter((p) => p.slug !== slug)

  return (
    <>
      <IndustryHead page={page} />
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="ind-root">
        <section className="ind-hero">
          <div className="shell">
            <nav className="ind-crumbs" aria-label="Breadcrumb">
              <Link to="/">Home</Link>
              <span aria-hidden="true">/</span>
              <Link to="/staffing-gurgaon">Staffing in Gurgaon</Link>
              <span aria-hidden="true">/</span>
              <span aria-current="page">{page.name}</span>
            </nav>
            <h1 className="ind-hero-eyebrow eyebrow">{page.hero.eyebrow}</h1>
            <p className="ind-hero-title">
              {page.hero.h1} <em>{page.hero.h1Em}</em>
            </p>
            <p className="ind-hero-lead">{page.hero.lead}</p>
            <div className="ind-actions ind-hero-actions">
              <HireCta page={page} />
              <a href={waLink(page.waMsg)} target="_blank" rel="noreferrer" className="btn ghost">
                Talk to Switch <b>→</b>
              </a>
            </div>
            <ul className="ind-hero-trust">
              <li>Aadhaar-verified</li>
              <li>Staff in a day</li>
              <li>Replacement guarantee</li>
              <li>Transparent billing</li>
            </ul>
          </div>
        </section>

        {page.sections.map((s, i) => {
          const Render = RENDERERS[s.type]
          return (
            <section className={`ind-sec ind-sec-${s.type}`} key={`${s.type}-${i}`}>
              <div className="shell">
                <Render s={s} page={page} />
              </div>
            </section>
          )
        })}

        <section className="ind-sec ind-more">
          <div className="shell">
            <span className="eyebrow">More industries</span>
            <div className="ind-more-links">
              {others.map((p) => (
                <Link key={p.slug} to={`/${p.slug}`}>
                  {p.name} <b>↗</b>
                </Link>
              ))}
              <Link to="/staffing-gurgaon">
                All staffing in Gurgaon <b>↗</b>
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
