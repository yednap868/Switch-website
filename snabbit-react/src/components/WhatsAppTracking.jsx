import { useEffect } from 'react'
import { trackWhatsApp, withSource } from '../data/site.js'

// Every WhatsApp link on the site — the shared ones in site.js and the ones
// pages build themselves — goes through this one listener. It runs in the
// capture phase, before the browser follows the link, so rewriting href here
// changes where the click goes.
export default function WhatsAppTracking() {
  useEffect(() => {
    const onClick = (e) => {
      const a = e.target.closest?.('a[href*="wa.me/"]')
      if (!a) return
      a.href = withSource(a.href)
      trackWhatsApp((a.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80))
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [])

  return null
}
