/* Site footer for every inner page — the homepage footer plus the full
   directory of service and industry pages (internal links the SEO pages
   rely on). */
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import { SxFooter } from '../sx/SxChrome.jsx'
import { INDUSTRY_LINKS, SERVICE_LIST } from '../../data/siteIndex.js'
import { APP_URL } from '../../data/site.js'
import '../sx/sx.css'

export default function Footer({ cta = true }) {
  return (
    <SxFooter
      className="sx-tok"
      title={
        cta && (
        <>
          Staff chahiye? Bas boliye<span className="sx-dot">.</span>
        </>
        )
      }
      primary={
        <a className="sx-btn" href={APP_URL} target="_blank" rel="noreferrer">
          Book staff <Icon name="arrow" />
        </a>
      }
      secondary={
        <Link className="sx-btn ghost" to="/work">
          Find work
        </Link>
      }
      directory={
        <div className="sx-dir">
          <nav aria-label="Staffing by industry">
            <b>By industry</b>
            <Link to="/staffing-gurgaon">Staffing in Gurgaon</Link>
            {INDUSTRY_LINKS.map((p) => (
              <Link key={p.slug} to={`/${p.slug}`}>
                {p.label || p.title || p.name}
              </Link>
            ))}
          </nav>
          <nav aria-label="Hire in Gurgaon">
            <b>Hire in Gurgaon</b>
            {SERVICE_LIST.map((s) => (
              <Link key={s.slug} to={`/${s.slug}`}>
                {s.name}
              </Link>
            ))}
          </nav>
        </div>
      }
    />
  )
}
