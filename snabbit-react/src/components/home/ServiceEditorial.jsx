import { Link } from 'react-router-dom'
import Annotate from '../fx/Annotate.jsx'
import CascadeLabel from '../fx/CascadeLabel.jsx'
import { INDUSTRIES, SERVICE_TILES, WHY_US } from '../../data/homeContent.js'

/* Quoted twice in this section, and the same pair appears in TrustEditorial's
   metrics — keep the three in step when they change. */
const INDUSTRY_STATS = { players: '20,000+', businesses: '1,000+' }
import { waLink } from '../../data/site.js'

export default function ServiceEditorial() {
  return (
    <section id="services" className="service-editorial">
      <div className="shell">
        <div className="section-head service-intro">
          <div>
            <CascadeLabel text="OUR SERVICES" />
            <h2>
              Every role that keeps your business{' '}
              <Annotate kind="underline" delay={0.12}>
                moving.
              </Annotate>
            </h2>
          </div>
          <div className="service-intro-copy">
            <p>
              From kitchens to warehouses, homes to offices — Switch provides trained, verified and
              reliable staff across multiple roles.
            </p>
            <Link className="text-link" to="/staffing-gurgaon">
              Explore all services <b>→</b>
            </Link>
          </div>
        </div>

        <div className="service-layout">
          <div className="service-grid">
            {SERVICE_TILES.map((tile, i) => (
              <Link
                key={tile.slug}
                className={`service-tile service-tile-${i + 1}`}
                to={`/${tile.slug}`}
                data-service-index={i}
              >
                <img
                  src={tile.img}
                  alt={`${tile.name} Switch Player`}
                  style={{ objectPosition: tile.focus }}
                  loading="lazy"
                />
                <span className="service-shade" />
                <span className="service-tile-copy">
                  <strong>{tile.name}</strong>
                  <small>{tile.desc}</small>
                </span>
                <b className="service-arrow">↗</b>
              </Link>
            ))}
          </div>

          <aside className="service-rail">
            <div className="service-rail-image">
              <img src="/hero-workers.jpg" alt="Switch workers ready for a shift" loading="lazy" />
              <span className="service-rail-note">
                Different people.
                <br />
                <em>Same commitment.</em>
              </span>
            </div>
            <div className="service-rail-copy">
              <h3>
                Real people.
                <br />
                Real work.
                <br />
                <em>A stronger Gurgaon.</em>
              </h3>
              {WHY_US.slice(1, 4).map((item, i) => (
                <div className="service-proof" key={item.title}>
                  <b>{String(i + 2).padStart(2, '0')}</b>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.desc}</small>
                  </span>
                </div>
              ))}
            </div>
          </aside>
        </div>

        {/* Sectors. The heading, the figures and the CTA live inside the grid
            as a 2x2 feature cell rather than sitting above it, which is what
            keeps twelve cards from reading as a wall of identical boxes.

            The cell arithmetic that keeps every tier full is in extras.css
            next to the grid it governs. */}
        <div className="sector-block">
          <div className="sector-grid">
            <div className="sector-feature">
              <span className="eyebrow">WHO WE STAFF</span>
              <h3>Built for the businesses that run Gurgaon.</h3>
              <p>
                From a four-table café to a warehouse floor on dispatch deadline — one verified
                bench, the same replacement guarantee, the same day.
              </p>
              <dl className="sector-stats">
                <div>
                  <dt>{INDUSTRY_STATS.players}</dt>
                  <dd>Verified Switch Players</dd>
                </div>
                <div>
                  <dt>{INDUSTRY_STATS.businesses}</dt>
                  <dd>Businesses served</dd>
                </div>
                <div>
                  <dt>{INDUSTRIES.length}</dt>
                  <dd>Sectors staffed</dd>
                </div>
              </dl>
              <a
                className="sector-feature-cta"
                href={waLink('Hi Switch — I need staff for my business in Gurgaon.')}
                target="_blank"
                rel="noreferrer"
              >
                Not on the list? Tell us the role <b>↗</b>
              </a>
            </div>

            {INDUSTRIES.map((ind, i) => {
              const body = (
                <>
                  <span className="sector-num mono">{String(i + 1).padStart(2, '0')}</span>
                  <span className="sector-name">{ind.name}</span>
                  <span className="sector-roles">{ind.roles}</span>
                  <span className="sector-go" aria-hidden="true">↗</span>
                </>
              )
              return ind.slug ? (
                <Link className="sector-card" key={ind.name} to={`/${ind.slug}`}>
                  {body}
                </Link>
              ) : (
                <a
                  className="sector-card"
                  key={ind.name}
                  href={waLink(`Hi Switch — I need staff for my ${ind.name} business in Gurgaon.`)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {body}
                </a>
              )
            })}
          </div>
        </div>

        <div id="industries" className="service-location">
          <span className="eyebrow">SERVING ACROSS GURGAON</span>
          <strong>Local people. Local businesses. Stronger together.</strong>
          <Link className="text-link" to="/staffing-gurgaon">
            See coverage areas →
          </Link>
        </div>
      </div>
    </section>
  )
}
