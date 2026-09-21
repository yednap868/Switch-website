import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EMPLOYER_LOGIN } from '../../data/site.js'

const LINKS = [
  { href: '/#services', label: 'Services' },
  { href: '/#how', label: 'How it works' },
  { href: '/#trust', label: 'Why Switch' },
  { href: '/#pricing', label: 'Pricing' },
  { href: '/#coverage', label: 'Coverage' },
  { href: '/#app-section', label: 'Get the app' },
]

export default function Header() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (typeof document === 'undefined') return
    document.body.classList.toggle('menu-open', open)
    return () => document.body.classList.remove('menu-open')
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false)
        document.querySelector('.menu')?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <header className={`header${scrolled ? ' scrolled' : ''}`}>
      <div className="shell nav">
        <Link to="/" className="logo" aria-label="Switch home">
          <span className="logo-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          {/* Plain text, not the particle canvas. At the header's 19px cap the
              particle sampler only lands a few dots per glyph, so the wordmark
              read as noise rather than "SWITCH". The footer mark is 80px and
              still uses ParticleWordmark, where the effect actually resolves. */}
          <span className="logo-wordmark">SWITCH</span>
        </Link>

        <nav className={`nav-links${open ? ' open' : ''}`}>
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} onClick={() => setOpen(false)}>
              {link.label}
            </a>
          ))}
          {/* The "Looking for work?" button is desktop-only, so the panel keeps
              its own link to /partner. */}
          <Link className="nav-link-jobs" to="/partner" onClick={() => setOpen(false)}>
            Looking for work?
          </Link>
        </nav>

        <div className="nav-actions">
          <Link className="btn ghost" to="/partner">
            Looking for work?
          </Link>
          <a className="btn primary" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
            Hire staff ↗
          </a>
        </div>

        <button
          className="menu"
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? '✕' : '☰'}
        </button>
      </div>
    </header>
  )
}
