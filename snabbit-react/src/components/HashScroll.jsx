import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const HEADER_OFFSET = 90 // sticky header height + a little air
const SETTLE_MS = 4000 // stop correcting once the page has stopped moving

/* The app renders fresh over the pre-rendered markup, so React replaces the DOM
   the browser had already scrolled to and any #anchor is lost. This re-applies
   it, and keeps it pinned while late images change the layout underneath — via
   a ResizeObserver rather than guessed timings. A real scroll gesture hands
   control straight back to the visitor. */
export default function HashScroll() {
  const { hash, pathname } = useLocation()

  useEffect(() => {
    if (!hash) return

    const id = decodeURIComponent(hash.slice(1))
    let cancelled = false
    let frame = 0

    const apply = () => {
      if (cancelled) return true
      const el = document.getElementById(id)
      if (!el) return false
      const top = Math.max(0, Math.round(el.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET))
      // `behavior: instant` overrides the stylesheet's scroll-behavior: smooth —
      // a smooth scroll would be restarted by every correction and never land.
      try {
        window.scrollTo({ top, left: 0, behavior: 'instant' })
      } catch {
        window.scrollTo(0, top)
      }
      return true
    }

    const waitForElement = () => {
      if (!apply()) frame = requestAnimationFrame(waitForElement)
    }
    frame = requestAnimationFrame(waitForElement)

    // Anything that changes the document height (images decoding, fonts
    // swapping) moves the target, so re-pin it.
    const ro = new ResizeObserver(() => apply())
    ro.observe(document.body)
    window.addEventListener('load', apply)

    const stop = () => {
      cancelled = true
      ro.disconnect()
    }
    const gestures = ['wheel', 'touchstart', 'keydown', 'pointerdown']
    gestures.forEach((g) => window.addEventListener(g, stop, { passive: true, once: true }))
    const settle = window.setTimeout(stop, SETTLE_MS)

    return () => {
      cancelled = true
      cancelAnimationFrame(frame)
      window.clearTimeout(settle)
      ro.disconnect()
      window.removeEventListener('load', apply)
      gestures.forEach((g) => window.removeEventListener(g, stop))
    }
  }, [hash, pathname])

  return null
}
