import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

// GA4 counts a page view when gtag('config', …) runs — once, on first load.
// This is a single-page app, so every click after that changes the URL without
// a reload and GA would never hear about it. Send a page_view ourselves on each
// route change, skipping the first one so the landing page isn't counted twice.
//
// The title is read a tick late: react-helmet-async writes <title> in its own
// effect, and reading it in the same tick would send the previous page's title.
export default function RouteAnalytics() {
  const { pathname, search } = useLocation()
  const first = useRef(true)

  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    if (typeof window === 'undefined' || typeof window.gtag !== 'function') return
    const id = window.setTimeout(() => {
      window.gtag('event', 'page_view', {
        page_path: pathname + search,
        page_location: window.location.href,
        page_title: document.title,
      })
    }, 50)
    return () => window.clearTimeout(id)
  }, [pathname, search])

  return null
}
