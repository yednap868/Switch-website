import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ParticleWordmark from '../fx/ParticleWordmark.jsx'
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
          <ParticleWordmark
            className="logo-wordmark"
            text="SWITCH"
            color="#f5f7f4"
            density={3}
            size={0.9}
            dispersion={10}
          />
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
