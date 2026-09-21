import { useEffect, useRef } from 'react'
import { prefersReducedMotion } from './motion.js'

/* Full-viewport pixel field that lights up around the pointer.
   Cell size steps down with viewport width; cells inside the pointer radius
   ease up fast (.24) and fade slowly (.035), tinted along green → mint → bone. */

const RAMP = ['#16a34a', '#5ee38a', '#d8e5dc']
const hex = (h) => parseInt(h, 16)

function mix(intensity, phase) {
  const t = (phase + intensity) % 1
  const i = Math.min(RAMP.length - 2, Math.floor(t * (RAMP.length - 1)))
  const f = (t * (RAMP.length - 1)) % 1
  const a = RAMP[i].slice(1)
  const b = RAMP[i + 1].slice(1)
  const ch = (o) =>
    Math.round(hex(a.slice(o, o + 2)) + (hex(b.slice(o, o + 2)) - hex(a.slice(o, o + 2))) * f)
  return `rgb(${ch(0)},${ch(2)},${ch(4)})`
}

export default function PixelCanvas() {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    const reduced = prefersReducedMotion()
    const cell = window.innerWidth < 640 ? 34 : window.innerWidth < 1024 ? 25 : 20
    const state = { width: 0, height: 0, pixels: [], pointer: { x: -1000, y: -1000 } }
    let frame = 0
    let resizeTimer = 0

    function layout() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      state.width = window.innerWidth
      state.height = window.innerHeight
      canvas.width = state.width * dpr
      canvas.height = state.height * dpr
      canvas.style.width = `${state.width}px`
      canvas.style.height = `${state.height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const cols = Math.ceil(state.width / cell)
      const rows = Math.ceil(state.height / cell)
      state.pixels = Array.from({ length: cols }, (_, cx) =>
        Array.from({ length: rows }, (_, cy) => ({
          x: cx * cell,
          y: cy * cell,
          intensity: 0,
          target: 0,
          phase: Math.random(),
        })),
      )
    }

    function draw(animating = 0) {
      ctx.clearRect(0, 0, state.width, state.height)
      const radius = window.innerWidth < 640 ? 72 : 110
      for (const column of state.pixels) {
        for (const px of column) {
          const d = Math.hypot(state.pointer.x - px.x, state.pointer.y - px.y)
          px.target = !reduced && d < radius ? Math.pow(1 - d / radius, 1.5) : 0
          px.intensity += (px.target - px.intensity) * (px.target > px.intensity ? 0.24 : 0.035)
          px.phase = (px.phase + 0.00045 * (animating ? 1 : 0)) % 1
          if (px.intensity > 0.012) {
            ctx.globalAlpha = px.intensity * 0.6
            ctx.fillStyle = mix(px.intensity, px.phase)
            ctx.fillRect(px.x, px.y, cell - 2, cell - 2)
          }
        }
      }
      ctx.globalAlpha = 1
      if (!reduced) frame = requestAnimationFrame(() => draw(1))
    }

    const onMove = (e) => {
      state.pointer.x = e.clientX
      state.pointer.y = e.clientY
    }
    const onLeave = () => {
      state.pointer.x = -1000
      state.pointer.y = -1000
    }
    const onResize = () => {
      window.clearTimeout(resizeTimer)
      resizeTimer = window.setTimeout(layout, 80)
    }

    window.addEventListener('pointermove', onMove, { passive: true })
    window.addEventListener('blur', onLeave)
    window.addEventListener('resize', onResize, { passive: true })
    layout()
    draw()

    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('blur', onLeave)
      window.removeEventListener('resize', onResize)
      window.clearTimeout(resizeTimer)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [])

  return <canvas ref={ref} className="pixel-canvas" aria-hidden="true" />
}
