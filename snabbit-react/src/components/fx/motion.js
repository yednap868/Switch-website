/* Shared motion helpers. Every effect in src/components/fx is opt-out under
   prefers-reduced-motion, the same way the design prototype handled it. */

export function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
