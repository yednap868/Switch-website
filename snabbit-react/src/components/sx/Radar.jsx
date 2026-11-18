/* The live network visual: a radar around your shop. The sweep passes, nearby
   workers light up — ringing (app ring + WhatsApp), seen, then yes — and the
   counters move. Illustrative positions, labelled as such. Server HTML is the
   finished frame; the loop runs only in the browser, never under
   prefers-reduced-motion. */
import { useEffect, useState } from 'react'

/* [angle°, distance 0–1] — nearer dots get alerted first. */
const DOTS = [
  [20, 0.28], [75, 0.42], [130, 0.33], [200, 0.5], [250, 0.3], [310, 0.45],
  [40, 0.62], [100, 0.7], [165, 0.66], [225, 0.78], [285, 0.68], [345, 0.74],
  [60, 0.88], [150, 0.9], [270, 0.9], [330, 0.92],
]
const END = { 0: 'yes', 1: 'seen', 2: 'seen', 3: 'yes', 4: 'seen', 5: 'ring', 6: 'seen', 7: 'yes' }
const ORDER = DOTS.map((d, i) => ({ i, r: d[1] })).sort((a, b) => a.r - b.r).map((d) => d.i)
const LOOP = 22

export default function Radar() {
  const [t, setT] = useState(LOOP - 1)
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setT((v) => (v + 1) % LOOP), 600)
    return () => clearInterval(id)
  }, [])

  const stateOf = (i) => {
    const rank = ORDER.indexOf(i)
    if (!(rank in END)) return 'idle'
    const at = 2 + rank * 1.5
    if (t < at) return 'idle'
    if (t < at + 1.5) return 'ring'
    if (END[rank] === 'yes' && t >= at + 3) return 'yes'
    return END[rank] === 'ring' ? 'ring' : 'seen'
  }
  const states = DOTS.map((_, i) => stateOf(i))
  const alerted = states.filter((s) => s !== 'idle').length
  const seen = states.filter((s) => s === 'seen' || s === 'yes').length
  const yes = states.filter((s) => s === 'yes').length

  return (
    <div className="sx-radar-wrap">
      <svg className="sx-radar" viewBox="-200 -200 400 400" role="img" aria-label="Nearby workers lighting up as Jyoti alerts them: ringing, seen, then yes.">
        <defs>
          <linearGradient id="sxSweep" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#059669" stopOpacity="0" />
            <stop offset="1" stopColor="#059669" stopOpacity="0.35" />
          </linearGradient>
        </defs>
        {[60, 110, 160, 190].map((r) => (
          <circle key={r} r={r} className="ring" />
        ))}
        <line x1="-190" y1="0" x2="190" y2="0" className="axis" />
        <line x1="0" y1="-190" x2="0" y2="190" className="axis" />
        <g className="sweep">
          <path d="M0,0 L190,0 A190,190 0 0,0 134,-134 Z" fill="url(#sxSweep)" />
        </g>
        {DOTS.map(([a, r], i) => {
          const x = Math.cos((a * Math.PI) / 180) * r * 190
          const y = Math.sin((a * Math.PI) / 180) * r * 190
          const s = states[i]
          return (
            <g key={i} transform={`translate(${x.toFixed(1)} ${y.toFixed(1)})`} className={`dot ${s}`}>
              {s === 'ring' && <circle r="14" className="halo" />}
              <circle r="6" />
            </g>
          )
        })}
        <g className="you">
          <circle r="22" />
          <text y="5">You</text>
        </g>
      </svg>
      <div className="sx-radar-stats" aria-live="polite">
        <div>
          <b>{alerted}</b>
          <small>alerted</small>
        </div>
        <div>
          <b>{seen}</b>
          <small>saw it</small>
        </div>
        <div className="g">
          <b>{yes}</b>
          <small>said yes</small>
        </div>
      </div>
      <ul className="sx-legend" aria-hidden="true">
        <li className="ring">Ringing</li>
        <li className="seen">Seen</li>
        <li className="yes">Yes</li>
      </ul>
    </div>
  )
}
