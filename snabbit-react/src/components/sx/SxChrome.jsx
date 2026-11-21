/* Header and footer for the new-look pages (home and /work). */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import { APP_URL, APPLE_URL, EMAIL, PHONE, PLAY_URL, SOCIALS } from '../../data/site.js'
import { WORKER_APP_URL } from '../../data/switchHome.js'

/* Theme: light by default here; follows the system until someone toggles,
   and remembers the choice under the same key as the rest of the site. */
function useTheme() {
  const [theme, setTheme] = useState(null)
  useEffect(() => {
    const t = document.documentElement.dataset.theme
    const sys = window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    const id = setTimeout(() => setTheme(t || sys), 0)
    return () => clearTimeout(id)
  }, [])
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem('switch-theme', next)
    } catch {
      /* private mode — the choice just won't stick */
    }
    setTheme(next)
  }
  return [theme, toggle]
}

export function SxHeader({ links, cta = { href: APP_URL, label: 'Book staff' }, className = '' }) {
  const [theme, toggle] = useTheme()
  const [open, setOpen] = useState(false)
  return (
    <header className={`sx-head ${className}`}>
      <div className="sx-wrap sx-head-in">
        <Link to="/" className="sx-logo" aria-label="Switch home">
          Switch<span>.</span>
        </Link>
        <nav className={`sx-nav${open ? ' open' : ''}`} aria-label="Main">
          {links.map(([h, l]) =>
            h.startsWith('/') ? (
              <Link key={h} to={h} onClick={() => setOpen(false)}>
                {l}
              </Link>
            ) : (
              <a key={h} href={h} onClick={() => setOpen(false)}>
                {l}
              </a>
            ),
          )}
        </nav>
        <div className="sx-head-cta">
          <button type="button" className="sx-icon-btn" onClick={toggle} aria-label="Switch light or dark mode">
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          </button>
          <a className="sx-btn sm" href={cta.href} target={cta.href.startsWith('http') ? '_blank' : undefined} rel="noreferrer">
            {cta.label}
          </a>
          <button
            type="button"
            className="sx-icon-btn sx-menu"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label="Menu"
          >
            <Icon name={open ? 'x' : 'menu'} />
          </button>
        </div>
      </div>
    </header>
  )
}

export function SxFooter({ title, primary, secondary, directory, className = '' }) {
  return (
    <footer className={`sx-foot ${className}`}>
      <div className="sx-wrap">
        {title && (
          <div className="sx-foot-cta">
            <h2 className="sx-h2">{title}</h2>
            <div className="sx-btns">
              {primary}
              {secondary}
            </div>
          </div>
        )}
        <div className="sx-foot-grid">
          <div>
            <Link to="/" className="sx-logo">
              Switch<span>.</span>
            </Link>
            <p>One chat with Jyoti to book staff or find work in Gurugram.</p>
            <p>
              <a href={`tel:${PHONE}`}>+91 87968 94500</a>
              <br />
              <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
            </p>
          </div>
          <nav aria-label="Switch">
            <b>Switch</b>
            <Link to="/work">Find work</Link>
            <Link to="/about">About</Link>
            <Link to="/staffing-gurgaon">Services</Link>
            <Link to="/blog">Blog</Link>
            <Link to="/partner">Partner with us</Link>
            <Link to="/verify">Verify a certificate</Link>
          </nav>
          <nav aria-label="Apps">
            <b>Apps</b>
            <a href={PLAY_URL} target="_blank" rel="noreferrer">
              Employer app · Android
            </a>
            <a href={APPLE_URL} target="_blank" rel="noreferrer">
              Employer app · iPhone
            </a>
            <a href={WORKER_APP_URL} target="_blank" rel="noreferrer">
              Worker app · Android
            </a>
          </nav>
          <nav aria-label="Legal">
            <b>Legal</b>
            <Link to="/terms">Terms</Link>
            <Link to="/privacy">Privacy</Link>
            <Link to="/cancellation">Cancellation</Link>
          </nav>
        </div>
        {directory}
        <div className="sx-foot-base">
          <span>© {new Date().getFullYear()} Third Wave Labs Private Limited · Gurugram</span>
          <span className="sx-social">
            {SOCIALS.map((s) => (
              <a key={s.name} href={s.href} target="_blank" rel="noreferrer" aria-label={s.name}>
                {s.label}
              </a>
            ))}
          </span>
        </div>
      </div>
    </footer>
  )
}

