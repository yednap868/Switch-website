import { useEffect } from 'react'

/* Adds `.in-view` to every <section> once 8% of it is on screen, which is what
   the editorial CSS keys its reveal animations off. One observer for the page;
   the class is never removed, so a section animates in exactly once. */

export default function useScrollReveal(deps = []) {
  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return
    const sections = Array.from(document.querySelectorAll('section'))
    if (!sections.length) return

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view')
            io.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.08 },
    )
    sections.forEach((section) => io.observe(section))
    return () => io.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
