/* "See for yourself how Jyoti searches the offline world" — a live map.
   Your shop sits in the middle of a sketch of Gurugram. A sweep goes out,
   nearby workers (real faces) light up nearest first: ringing → seen → yes.
   A live feed beside it logs each event, and a WhatsApp-style alert shows
   what the worker actually receives. Illustrative positions, labelled.
   Server HTML is the finished frame; the loop runs only in the browser and
   never under prefers-reduced-motion. */
import { useEffect, useState } from 'react'
import Icon from '../ui/Icon.jsx'

/* x,y in a 400×400 map; d = km from you. Nearest first gets alerted first. */
const WORKERS = [
  { n: 'Ravi', role: 'Cook', x: 238, y: 168, d: 0.8, end: 'yes' },
  { n: 'Sunita', role: 'Cook', x: 150, y: 232, d: 1.1, end: 'seen' },
  { n: 'Imran', role: 'Cook', x: 262, y: 262, d: 1.6, end: 'yes' },
  { n: 'Pooja', role: 'Cook', x: 128, y: 140, d: 2.2, end: 'seen' },
  { n: 'Arjun', role: 'Cook', x: 300, y: 110, d: 2.9, end: 'busy' },
  { n: 'Vikas', role: 'Cook', x: 92, y: 290, d: 3.4, end: 'seen' },
]
const FAR = [
  [60, 80], [345, 60], [360, 210], [330, 330], [200, 360], [40, 200], [180, 52], [70, 360], [360, 150],
]
const AREAS = [
  { t: 'Cyber City', x: 300, y: 70 },
  { t: 'DLF Ph 3', x: 70, y: 110 },
  { t: 'Sector 49', x: 300, y: 320 },
  { t: 'Sohna Rd', x: 150, y: 345 },
  { t: 'Golf Course Rd', x: 305, y: 185 },
  { t: 'Udyog Vihar', x: 95, y: 255 },
]
const LOOP = 30

function at(i) {
  return 3 + i * 2.5
}
function stateOf(i, t) {
  const s = at(i)
  if (t < s) return 'idle'
  if (t < s + 1.5) return 'ring'
  if (t < s + 3) return 'seen'
  return WORKERS[i].end
}

export default function Radar() {
  const [t, setT] = useState(LOOP - 1)
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setT((v) => (v + 1) % LOOP), 800)
    return () => clearInterval(id)
  }, [])

  const states = WORKERS.map((_, i) => stateOf(i, t))
  const alerted = states.filter((s) => s !== 'idle').length
  const seen = states.filter((s) => s === 'seen' || s === 'yes' || s === 'busy').length
  const yes = states.filter((s) => s === 'yes').length
  const done = yes >= 2

  // newest event first
  const feed = WORKERS.map((w, i) => ({ w, i, s: states[i] }))
    .filter((x) => x.s !== 'idle')
    .reverse()
    .slice(0, 4)
  const ringing = WORKERS.findIndex((_, i) => states[i] === 'ring')

  return (
    <div className="rd">
      <div className="rd-map">
        <svg viewBox="0 0 400 400" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Map of nearby workers lighting up as Jyoti alerts them: ringing, seen, then yes.">
          <defs>
            <radialGradient id="rdSweep" cx="0" cy="0" r="1">
              <stop offset="0" stopColor="#059669" stopOpacity="0.35" />
              <stop offset="1" stopColor="#059669" stopOpacity="0" />
            </radialGradient>
            {WORKERS.map((w) => (
              <clipPath id={`rdc-${w.n}`} key={w.n}>
                <circle cx={w.x} cy={w.y} r="15" />
              </clipPath>
            ))}
          </defs>
          {/* parks & blocks */}
          <rect x="0" y="0" width="400" height="400" className="rd-land" />
          <path d="M18 18 h70 v62 h-70 z" className="rd-park" />
          <path d="M318 228 h64 v48 h-64 z" className="rd-park" />
          <path d="M228 318 h56 v64 h-56 z" className="rd-block" />
          <path d="M18 318 h76 v62 h-76 z" className="rd-block" />
          <path d="M140 18 h44 v84 h-44 z" className="rd-block" />
          {/* streets */}
          <g className="rd-roads">
            <path d="M0 120 C 120 140, 260 90, 400 110" />
            <path d="M0 300 C 140 280, 250 320, 400 290" />
            <path d="M110 0 C 130 140, 90 260, 120 400" />
            <path d="M300 0 C 280 120, 320 260, 290 400" />
            <path d="M0 210 L 400 200" className="major" />
            <path d="M200 0 L 210 400" className="major" />
          </g>
          {AREAS.map((a) => (
            <text key={a.t} x={a.x} y={a.y} className="rd-area" textAnchor="middle">
              {a.t}
            </text>
          ))}
          {[60, 110, 160].map((r) => (
            <circle key={r} cx="200" cy="200" r={r} className="rd-ring" />
          ))}
          <g className="rd-sweep">
            <path d="M200,200 L360,200 A160,160 0 0,0 313,87 Z" fill="url(#rdSweep)" />
          </g>
          {FAR.map(([x, y], k) => (
            <circle key={k} cx={x} cy={y} r="4" className="rd-far" />
          ))}
          {WORKERS.map((w, i) => {
            const s = states[i]
            return (
              <g key={w.n} className={`rd-w ${s}`}>
                {s !== 'idle' && <line x1="200" y1="200" x2={w.x} y2={w.y} className="rd-link" />}
                {s === 'ring' && <circle cx={w.x} cy={w.y} r="15" className="rd-halo" />}
                <circle cx={w.x} cy={w.y} r="18" className="rd-ringbg" />
                <image
                  href={`/av/${w.n.toLowerCase()}.jpg`}
                  x={w.x - 15}
                  y={w.y - 15}
                  width="30"
                  height="30"
                  clipPath={`url(#rdc-${w.n})`}
                  preserveAspectRatio="xMidYMid slice"
                />
                {s === 'yes' && (
                  <g className="rd-tick">
                    <circle cx={w.x + 12} cy={w.y - 12} r="8" />
                    <path d={`M${w.x + 8} ${w.y - 12} l3 3 l5 -6`} />
                  </g>
                )}
              </g>
            )
          })}
          <g className="rd-you">
            <circle cx="200" cy="200" r="26" />
            <path d="M190 204 v-8 l10 -7 l10 7 v8 z" />
            <text x="200" y="244" textAnchor="middle">
              Your café
            </text>
          </g>
        </svg>

        {ringing > -1 && (
          <div className="rd-wa" key={ringing}>
            <span className="rd-wa-ico">
              <Icon name="phone" />
            </span>
            <div>
              <small>WhatsApp · Switch</small>
              <b>
                {WORKERS[ringing].n}, naya kaam — Cook, kal 11 AM · {WORKERS[ringing].d} km
              </b>
            </div>
          </div>
        )}
      </div>

      <div className="rd-side">
        <div className="rd-job">
          <small>Your request</small>
          <b>2 × Cook · Kal 11 AM · 4 ghante</b>
          <span className={`rd-status${done ? ' ok' : ''}`}>{done ? 'Filled ✓ — pay ₹99' : 'Searching nearby…'}</span>
        </div>
        <div className="rd-stats" aria-live="polite">
          <div>
            <b>{alerted}</b>
            <small>alerted</small>
          </div>
          <div>
            <b>{seen}</b>
            <small>saw it</small>
          </div>
          <div className="g">
            <b>
              {yes}
              <i>/2</i>
            </b>
            <small>said yes</small>
          </div>
        </div>
        <ul className="rd-feed">
          {feed.length === 0 && <li className="wait">Confirmed for ₹0 — alerting the nearest workers…</li>}
          {feed.map(({ w, s }) => (
            <li key={w.n + s} className={s}>
              <img src={`/av/${w.n.toLowerCase()}.jpg`} alt="" width="32" height="32" />
              <span>
                <b>{w.n}</b>
                <small>{w.d} km away</small>
              </span>
              <em>{{ ring: 'Ringing', seen: 'Seen', yes: 'Haan ✓', busy: 'Busy today' }[s]}</em>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
