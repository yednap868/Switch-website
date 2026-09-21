import { Link } from 'react-router-dom'
import Annotate from '../fx/Annotate.jsx'
import CascadeLabel from '../fx/CascadeLabel.jsx'
import { INDUSTRIES, SERVICE_TILES, WHY_US } from '../../data/homeContent.js'
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

        {/* Industries — live-site content the prototype dropped, in its
            hairline-grid idiom. */}
        <div className="industry-block">
          <div className="section-head industry-head">
            <div>
              <span className="eyebrow">WHO WE STAFF</span>
              <h3>Built for the businesses that run Gurgaon.</h3>
            </div>
          </div>
          <div className="reasons industry-grid">
            {INDUSTRIES.map((ind, i) => (
              <a
                className="reason industry-card"
                key={ind.name}
                href={waLink(`Hi Switch — I need staff for my ${ind.name} business in Gurgaon.`)}
                target="_blank"
                rel="noreferrer"
              >
                <span className="eyebrow">{String(i + 1).padStart(2, '0')}</span>
                <b>{ind.name}</b>
                <p>{ind.roles}</p>
              </a>
            ))}
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
