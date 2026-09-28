import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs, CtaFeature, Faq as FaqList, HeroArt, StatsRow } from '../components/ui/Blocks.jsx'
import { HOME_STATS } from '../data/homeContent.js'
import { GURGAON_AREAS, INDUSTRY_PAGES, getIndustryPage } from '../data/industryPages.js'
import { APP_URL, EMAIL, waLink } from '../data/site.js'
import './IndustryPage.css'

const BASE_URL = 'https://switchlocally.com'
const pad = (n) => String(n + 1).padStart(2, '0')
const TINTS = ['t-lav', 't-peach', 't-sky', 't-mint', 't-pink', 't-grey']

/* Staff photo (arch-cropped in the hero) and CTA photos per industry. */
const ART = {
  'warehouse-staffing-gurgaon': ['/sw-factory-helper.jpg', '/sw-general-helper.jpg', 'warehouse'],
  'event-staffing-gurgaon': ['/sw-bartender.jpg', '/sw-waiter.jpg', 'party'],
  'restaurant-staffing-gurgaon': ['/sw-waiter.jpg', '/sw-cook.jpg', 'utensils'],
  'office-staffing-gurgaon': ['/sw-maid.jpg', '/sw-security-guard.jpg', 'building'],
  'retail-staffing-gurgaon': ['/sw-general-helper.jpg', '/sw-security-guard.jpg', 'store'],
}
const DEFAULT_ART = ['/hero-workers.jpg', '/sw-general-helper.jpg', 'building']

/* "Hire X Staff" books through the app; "Talk to Switch" and
   "Tell Us What You Need" open WhatsApp with the page's context. */
function HireCta({ page, className = 'sw-btn' }) {
  return (
    <a href={APP_URL} className={className}>
      {page.hero.cta} <Icon name="arrow" />
    </a>
  )
}

function NeedCta({ page, className = 'sw-btn line' }) {
  return (
    <a href={waLink(page.waMsg)} target="_blank" rel="noreferrer" className={className}>
      Tell Us What You Need <Icon name="arrow" />
    </a>
  )
}

function SectionHead({ s }) {
  return (
    <div className="sw-head">
      <p className="sw-eyebrow">{s.eyebrow}</p>
      <h2 className="sw-h2">{s.h2}</h2>
      {s.lead && <p className="sw-lead">{s.lead}</p>}
    </div>
  )
}

function Intro({ s, page }) {
  return (
    <div className="ind-split">
      <div className="sw-head">
        <p className="sw-eyebrow">{s.eyebrow}</p>
        <h2 className="sw-h2">{s.h2}</h2>
      </div>
      <div className="ind-prose">
        {s.paras.map((p) => (
          <p key={p}>{p}</p>
        ))}
        <aside className="sw-feature ind-callout">
          <strong>{s.callout.title}</strong>
          <p>{s.callout.text}</p>
          <NeedCta page={page} className="sw-btn white" />
        </aside>
      </div>
    </div>
  )
}

function Roles({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <div className="sw-grid sw-g3">
        {s.groups.map((g, i) => (
          <div className="sw-card ind-role" key={g.name}>
            <span className="ind-n">{pad(i)}</span>
            <h3 className="sw-h3">{g.name}</h3>
            <ul className="ind-tags">
              {g.roles.map((r) => (
                <li className="sw-tag" key={r}>
                  {r}
                </li>
              ))}
            </ul>
            {g.desc && <p>{g.desc}</p>}
          </div>
        ))}
      </div>
      <div className="sw-btns ind-actions">
        <HireCta page={page} />
      </div>
    </>
  )
}

function Cards({ s, page }) {
  const icon = (ART[page.slug] || DEFAULT_ART)[2]
  return (
    <>
      <SectionHead s={s} />
      <div className="sw-grid sw-g3">
        {s.items.map((c, i) => (
          <div className="sw-card sw-ind" key={c.title}>
            <span className={`sw-sq ${TINTS[i % TINTS.length]}`}>
              <Icon name={icon} />
            </span>
            <h3 className="sw-h3">{c.title}</h3>
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
      <ol className="sw-grid sw-g4 ind-ol">
        {s.items.map((f, i) => (
          <li className="sw-card sw-step" key={f.title}>
            <span className="n">{pad(i)}</span>
            <h3 className="sw-h3">{f.title}</h3>
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
      <ul className="sw-chips ind-chips">
        {s.items.map((t) => (
          <li className="sw-chip" key={t}>
            <Icon name="check" />
            {t}
          </li>
        ))}
      </ul>
    </>
  )
}

function Table({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <div className="sw-table">
        <table>
          <thead>
            <tr>
              {s.cols.map((c) => (
                <th scope="col" key={c}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {s.rows.map(([need, how]) => (
              <tr key={need}>
                <td className="ind-need">{need}</td>
                <td>{how}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {s.cta && (
        <div className="sw-btns ind-actions">
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
      <div className="sw-grid sw-g3">
        {s.items.map((w, i) =>
          w.cta ? (
            <div className="sw-dashed ind-why-cta" key={w.title}>
              <span className="ind-n">{pad(i)}</span>
              <h3 className="sw-h3">{w.title}</h3>
              <p>{w.desc}</p>
              <NeedCta page={page} className="sw-link" />
            </div>
          ) : (
            <div className="sw-card sw-step" key={w.title}>
              <Icon name="shield" style={{ color: 'var(--p-t)' }} />
              <h3 className="sw-h3">{w.title}</h3>
              <p>{w.desc}</p>
            </div>
          ),
        )}
      </div>
    </>
  )
}

function Steps({ s, page }) {
  return (
    <>
      <SectionHead s={s} />
      <ol className="sw-grid sw-g3 ind-ol">
        {s.items.map((st, i) => (
          <li className="sw-card sw-step" key={st.title}>
            <span className="n">STEP {i + 1}</span>
            <h3 className="sw-h3">{st.title}</h3>
            <p>{st.desc}</p>
          </li>
        ))}
      </ol>
      <div className="sw-btns ind-actions">
        <HireCta page={page} />
      </div>
    </>
  )
}

function Areas({ s, page }) {
  return (
    <div className="ind-split">
      <div className="sw-head">
        <p className="sw-eyebrow">{s.eyebrow}</p>
        <h2 className="sw-h2">{s.h2}</h2>
        <p className="sw-lead">{s.lead}</p>
      </div>
      <div>
        <ul className="ind-areas">
          {GURGAON_AREAS.map((a) => (
            <li key={a}>
              <Icon name="pin" />
              {a}
            </li>
          ))}
        </ul>
        <p className="ind-area-note">
          Need staff somewhere else in Gurgaon? Tell us your location and we&apos;ll confirm
          availability.{' '}
          <a
            className="sw-link"
            href={waLink(`${page.waMsg} My location is: `)}
            target="_blank"
            rel="noreferrer"
          >
            Check your area <Icon name="arrow" />
          </a>
        </p>
      </div>
    </div>
  )
}

function Faq({ s }) {
  return (
    <>
      <div className="sw-head">
        <p className="sw-eyebrow">{s.eyebrow}</p>
        <h2 className="sw-h2">{s.h2}</h2>
      </div>
      <FaqList items={s.items} />
    </>
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
  const [heroImg, altImg] = ART[page.slug] || DEFAULT_ART

  return (
    <>
      <IndustryHead page={page} />
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="sw-wrap">
        <Crumbs items={[['Staffing in Gurgaon', '/staffing-gurgaon'], [page.name]]} />

        <section className="sw-hero">
          <div>
            <h1 className="sw-eyebrow ind-h1">{page.hero.eyebrow}</h1>
            <p className="sw-h1 ind-title">
              {page.hero.h1} <em>{page.hero.h1Em}</em>
            </p>
            <p className="sw-lead">{page.hero.lead}</p>
            <div className="sw-btns">
              <HireCta page={page} />
              <a href={waLink(page.waMsg)} target="_blank" rel="noreferrer" className="sw-btn line">
                Talk to Switch <Icon name="arrow" />
              </a>
            </div>
            <ul className="sw-checks ind-trust">
              {['Aadhaar-verified', 'Staff in a day', 'Replacement guarantee', 'Transparent billing'].map((x) => (
                <li className="sw-pill sw-live" key={x}>
                  {x}
                </li>
              ))}
            </ul>
          </div>
          <HeroArt
            img={heroImg}
            alt={`${page.name} — a verified Switch Player in Gurgaon`}
            otp
            badge={{ title: 'Staff confirmed', sub: 'Often within the day' }}
          />
        </section>

        <StatsRow items={HOME_STATS} />

        {page.sections.map((s, i) => {
          const Render = RENDERERS[s.type]
          return (
            <section className={`sw-sec ind-sec-${s.type}`} key={`${s.type}-${i}`}>
              <Render s={s} page={page} />
            </section>
          )
        })}

        <section className="sw-sec ind-more" aria-labelledby="ind-more-h">
          <div className="sw-head">
            <p className="sw-eyebrow" id="ind-more-h">
              More industries
            </p>
          </div>
          <div className="sw-grid sw-g3">
            {others.map((p) => {
              const [img] = ART[p.slug] || DEFAULT_ART
              return (
                <Link key={p.slug} className="sw-card sw-press ind-more-link" to={`/${p.slug}`}>
                  <span className="ind-more-img">
                    <img src={img} alt="" loading="lazy" />
                  </span>
                  <b>{p.name}</b>
                  <span className="sw-go">
                    <Icon name="arrow" />
                  </span>
                </Link>
              )
            })}
            <Link className="sw-card sw-press ind-more-link" to="/staffing-gurgaon">
              <span className="sw-sq t-lav">
                <Icon name="sparkles" />
              </span>
              <b>All staffing in Gurgaon</b>
              <span className="sw-go">
                <Icon name="arrow" />
              </span>
            </Link>
          </div>
        </section>

        <CtaFeature
          title={
            <>
              {page.hero.cta} <em>today.</em>
            </>
          }
          msg={page.waMsg}
          photos={[heroImg, altImg]}
        />
      </main>
      <Footer />
    </>
  )
}
