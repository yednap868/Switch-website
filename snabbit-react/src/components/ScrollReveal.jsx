import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/* Fades sections up as they scroll into view. Only sections that start below
   the fold are hidden, and only after this runs in the browser, so the
   prerendered HTML — and anyone without JS — sees the whole page. Styles:
   .sw-pre / .sw-in in src/styles/switch.css (motion-safe only). */
export default function ScrollReveal() {
  const { pathname } = useLocation()
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    if (!('IntersectionObserver' in window)) return
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('sw-in')
            io.unobserve(e.target)
          }
        })
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
    )
    const t = setTimeout(() => {
      document.querySelectorAll('main .sw-sec').forEach((el) => {
        if (el.getBoundingClientRect().top > window.innerHeight * 0.92) {
          el.classList.add('sw-pre')
          io.observe(el)
        }
      })
    }, 60)
    return () => {
      clearTimeout(t)
      io.disconnect()
    }
  }, [pathname])
  return null
}
