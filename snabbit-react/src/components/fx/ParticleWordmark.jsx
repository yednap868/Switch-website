import { useEffect, useRef, useState } from 'react'
import { prefersReducedMotion } from './motion.js'

/* Canvas wordmark made of particles that scatter away from the cursor and
   spring back. Used for the header logo and the footer SWITCH mark.

   Pointer position is measured against the canvas rect (the prototype's header
   version compared client coords to element coords, so its field sat off the
   glyphs — this uses the corrected math for both). */

export default function ParticleWordmark({
  text = 'SWITCH',
  color = '#f5f7f4',
  fontSize = null,
  density = 6,
  size = 1.6,
  dispersion = 14,
  returnSpeed = 0.08,
  className = '',
  ...rest
}) {
  const hostRef = useRef(null)
  const canvasRef = useRef(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const host = hostRef.current
    const canvas = canvasRef.current
    if (!host || !canvas) return
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return

    let particles = []
    let frame = null
    let width = 0
    let height = 0
    let resizeTimer = 0
    const pointer = { x: -1000, y: -1000 }
    const reduced = prefersReducedMotion()

    function tick() {
      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = color

      if (reduced) {
        for (const p of particles) {
          p.x = p.ox
          p.y = p.oy
          ctx.beginPath()
          ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
          ctx.fill()
        }
        frame = null
        return
      }

      for (const p of particles) {
        const dx = pointer.x - p.x
        const dy = pointer.y - p.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        if (dist < 120 && pointer.x !== -1000) {
          const force = (120 - dist) / 120
          p.vx -= (dx / dist) * force * dispersion
          p.vy -= (dy / dist) * force * dispersion
        }
        p.vx += (p.ox - p.x) * returnSpeed
        p.vy += (p.oy - p.y) * returnSpeed
        p.vx *= 0.85
        p.vy *= 0.85
        if (Math.hypot(p.x - p.ox, p.y - p.oy) < 1 && Math.random() > 0.95) {
          p.vx += (Math.random() - 0.5) * 0.18
          p.vy += (Math.random() - 0.5) * 0.18
        }
        p.x += p.vx
        p.y += p.vy
        ctx.beginPath()
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
        ctx.fill()
      }
      frame = requestAnimationFrame(tick)
    }

    function sample() {
      if (frame) {
        cancelAnimationFrame(frame)
        frame = null
      }
      width = host.clientWidth || 160
      height = host.clientHeight || 48
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      const family = 'Manrope, Arial, sans-serif'
      let px = fontSize || Math.round(height * 0.66)
      ctx.font = `800 ${px}px ${family}`
      const measured = ctx.measureText(text).width
      if (measured > width * 0.92) px = Math.floor(px * ((width * 0.92) / measured))
      px = Math.max(px, 10)

      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = color
      ctx.font = `800 ${px}px ${family}`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(text, width / 2, height / 2)

      const image = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const step = Math.max(1, Math.round((reduced ? density + 1 : density) * dpr))
      particles = []
      for (let y = 0; y < image.height; y += step) {
        for (let x = 0; x < image.width; x += step) {
          if (image.data[(y * image.width + x) * 4 + 3] > 128) {
            const ox = x / dpr
            const oy = y / dpr
            particles.push({
              x: ox + (Math.random() - 0.5) * 10,
              y: oy + (Math.random() - 0.5) * 10,
              ox,
              oy,
              vx: (Math.random() - 0.5) * 4,
              vy: (Math.random() - 0.5) * 4,
            })
          }
        }
      }
      setMounted(true)
      tick()
    }

    const track = (cx, cy) => {
      const rect = canvas.getBoundingClientRect()
      pointer.x = cx - rect.left
      pointer.y = cy - rect.top
    }
    const onMouseMove = (e) => track(e.clientX, e.clientY)
    const onTouchMove = (e) => {
      if (e.touches[0]) track(e.touches[0].clientX, e.touches[0].clientY)
    }
    const onLeave = () => {
      pointer.x = -1000
      pointer.y = -1000
    }

    canvas.addEventListener('mousemove', onMouseMove, { passive: true })
    canvas.addEventListener('mouseleave', onLeave, { passive: true })
    canvas.addEventListener('touchmove', onTouchMove, { passive: true })
    canvas.addEventListener('touchend', onLeave, { passive: true })

    const ro = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer)
      resizeTimer = window.setTimeout(sample, 80)
    })
    ro.observe(host)

    if (document.fonts?.ready) document.fonts.ready.then(sample).catch(() => {})
    const warmup = window.setTimeout(sample, 120)

    return () => {
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseleave', onLeave)
      canvas.removeEventListener('touchmove', onTouchMove)
      canvas.removeEventListener('touchend', onLeave)
      ro.disconnect()
      window.clearTimeout(resizeTimer)
      window.clearTimeout(warmup)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [text, color, fontSize, density, size, dispersion, returnSpeed])

  return (
    <span ref={hostRef} className={className} {...rest}>
      {/* Real text for crawlers, screen readers and the pre-rendered HTML;
          hidden once the canvas has drawn. */}
      <span data-logo-fallback="" style={{ opacity: mounted ? 0 : 1 }}>
        {text}
      </span>
      <canvas ref={canvasRef} aria-hidden="true" />
    </span>
  )
}
