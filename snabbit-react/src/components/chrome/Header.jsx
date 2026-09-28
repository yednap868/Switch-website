import { useEffect, useState, useSyncExternalStore } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import { EMPLOYER_LOGIN } from '../../data/site.js'

const LINKS = [
  { to: '/staffing-gurgaon', label: 'Services' },
  { to: '/#trial', label: '₹149 Trial' },
  { to: '/#pricing', label: 'Pricing' },
  { to: '/#how', label: 'How it works' },
  { to: '/about', label: 'About' },
  { to: '/blog', label: 'Blog' },
]

/* Theme: dark is the default. The choice lives on <html data-theme>, is saved
   to localStorage, and is applied before first paint by the inline script in
   index.html, so there is no flash. The server always renders the dark icon. */
const themeListeners = new Set()
const readTheme = () => (document.documentElement.dataset.theme === 'light' ? 'light' : 'dark')
const subscribeTheme = (fn) => {
  themeListeners.add(fn)
  return () => themeListeners.delete(fn)
}
function setTheme(next) {
  document.documentElement.dataset.theme = next
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', next === 'light' ? '#f6f4fb' : '#0b0a0f')
  try {
    localStorage.setItem('switch-theme', next)
  } catch {
    /* private mode — the choice just won't persist */
  }
  themeListeners.forEach((fn) => fn())
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, () => 'dark')
  const toLight = theme === 'dark'
  return (
    <button
      type="button"
      className="sw-theme"
      onClick={() => setTheme(toLight ? 'light' : 'dark')}
      aria-label={toLight ? 'Switch to light theme' : 'Switch to dark theme'}
      title={toLight ? 'Light theme' : 'Dark theme'}
    >
      <Icon name={toLight ? 'sun' : 'moon'} />
    </button>
  )
}

export default function Header() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open])

  return (
    <header className="sw-header">
      <div className="sw-wrap">
        <Link to="/" className="sw-brand" aria-label="Switch home">
          <img className="wm-dark" src="/brand/switch-wordmark-white.png" alt="Switch" width="130" height="34" />
          <img className="wm-light" src="/brand/switch-wordmark-black.png" alt="" width="130" height="34" />
          <small>
            <Icon name="pin" />
            Gurgaon
          </small>
        </Link>

        <nav className="sw-nav" aria-label="Main">
          {LINKS.map((l) => (
            <Link key={l.to} to={l.to} aria-current={pathname === l.to ? 'page' : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="sw-hdr-cta">
          <ThemeToggle />
          <Link className="sw-btn sm line" to="/partner">
            Looking for work?
          </Link>
          <a className="sw-btn sm sw-hire" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
            Hire staff <Icon name="arrow" />
          </a>
        </div>

        <button
          type="button"
          className="sw-menu-btn"
          aria-label="Open menu"
          aria-expanded={open}
          onClick={() => setOpen(true)}
        >
          <Icon name="menu" />
        </button>
      </div>

      {open && (
        <div className="sw-sheet" onClick={() => setOpen(false)}>
          <div className="sw-sheet-in" role="dialog" aria-modal="true" aria-label="Menu" onClick={(e) => e.stopPropagation()}>
            {[{ to: '/', label: 'Home' }, ...LINKS, { to: '/app', label: 'Get the app' }, { to: '/partner', label: 'Looking for work?' }].map((l) => (
              <Link key={l.to + l.label} to={l.to} onClick={() => setOpen(false)}>
                {l.label}
                <Icon name="arrow" />
              </Link>
            ))}
            <a className="sw-btn" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
              Hire staff <Icon name="arrow" />
            </a>
          </div>
        </div>
      )}
    </header>
  )
}
