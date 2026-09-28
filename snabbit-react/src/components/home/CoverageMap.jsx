/* Coverage, as a live map: a schematic of Gurgaon with the areas we serve,
   and an example booking acted out on it — request → nearby verified
   Switch Players matched → they travel in → OTP check-in. It then moves to
   the next area; tapping an area runs the flow there.
   The map is schematic (relative positions, not to scale) and the booking is
   an illustration, and both say so. Motion stops for prefers-reduced-motion. */
import { useEffect, useState } from 'react'
import Icon from '../ui/Icon.jsx'
import { waLink } from '../../data/site.js'

// Approximate relative positions on a 640×460 board (north up).
const AREAS = [
  { name: 'Cyber City', x: 372, y: 132, job: '2 Kitchen Helpers', place: 'café' },
  { name: 'Udyog Vihar', x: 250, y: 104, job: '5 Picker / Packers', place: 'warehouse' },
  { name: 'MG Road', x: 452, y: 188, job: '3 Waiters', place: 'restaurant' },
  { name: 'DLF', x: 404, y: 250, job: '1 Security Guard', place: 'office' },
  { name: 'Sushant Lok', x: 318, y: 292, job: '2 Housekeeping', place: 'clinic' },
  { name: 'Sectors 1–49', x: 196, y: 262, job: '2 Store Helpers', place: 'shop' },
  { name: 'Palam Vihar', x: 128, y: 146, job: '1 Cook', place: 'staff mess' },
  { name: 'Sohna Road', x: 352, y: 396, job: '4 Loaders', place: 'warehouse' },
]

// Switch Players on the board (deterministic, so server and client agree).
const PLAYERS = [
  [300, 70], [440, 96], [520, 150], [210, 150], [150, 210], [270, 200], [340, 196],
  [480, 250], [250, 320], [390, 330], [160, 330], [300, 380], [430, 420], [540, 300],
  [90, 90], [560, 220], [220, 410], [110, 270],
]

const STEPS = [
  { key: 'request', title: 'Request sent', icon: 'msg' },
  { key: 'match', title: 'Matched nearby', icon: 'search' },
  { key: 'route', title: 'On the way', icon: 'truck' },
  { key: 'done', title: 'Checked in with OTP', icon: 'check' },
]
const STEP_MS = [1700, 1900, 2400, 2600]

const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function nearest(area, n) {
  return PLAYERS.map((p, i) => ({ i, d: Math.hypot(p[0] - area.x, p[1] - area.y) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, n)
    .map((p) => p.i)
}

export default function CoverageMap() {
  // Server HTML shows the finished booking; the client then plays it.
  const [ai, setAi] = useState(0)
  const [step, setStep] = useState(3)
  const [live, setLive] = useState(false)

  useEffect(() => {
    if (reduced()) return
    const t = setTimeout(() => {
      setLive(true)
      setStep(0)
    }, 400)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!live) return
    const t = setTimeout(() => {
      if (step < 3) setStep(step + 1)
      else {
        setAi((a) => (a + 1) % AREAS.length)
        setStep(0)
      }
    }, STEP_MS[step])
    return () => clearTimeout(t)
  }, [live, step])

  const pick = (i) => {
    setAi(i)
    setStep(live ? 0 : 3)
  }

  const area = AREAS[ai]
  const count = Math.max(1, Math.min(3, parseInt(area.job, 10) || 1))
  const team = nearest(area, count)
  const eta = 35 + ((ai * 7) % 25)

  return (
    <div className="cm">
      <div className="cm-map sw-card">
        <svg viewBox="0 0 640 460" role="img" aria-label={`Schematic map of Gurgaon showing ${AREAS.map((a) => a.name).join(', ')}`}>
          <defs>
            <radialGradient id="cm-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#7b4dff" stopOpacity="0.55" />
              <stop offset="100%" stopColor="#7b4dff" stopOpacity="0" />
            </radialGradient>
            <pattern id="cm-grid" width="32" height="32" patternUnits="userSpaceOnUse">
              <path d="M32 0H0V32" fill="none" className="cm-gridline" />
            </pattern>
          </defs>
          <rect width="640" height="460" fill="url(#cm-grid)" />
          {/* city boundary */}
          <path
            className="cm-city"
            d="M70 90 C120 40 250 40 330 52 C430 60 540 80 590 150 C620 210 600 300 560 360 C520 420 420 450 330 445 C230 440 120 400 80 330 C50 270 40 150 70 90 Z"
          />
          {/* main roads */}
          <path className="cm-road" d="M600 30 L60 440" />
          <path className="cm-road" d="M455 170 L470 450" />
          <path className="cm-road thin" d="M350 300 L330 455" />
          <path className="cm-road thin" d="M40 120 L300 330" />
          <text className="cm-road-label" x="548" y="92" transform="rotate(-37 548 92)">NH-48</text>
          <text className="cm-road-label" x="478" y="380" transform="rotate(87 478 380)">Golf Course Rd</text>
          <text className="cm-road-label" x="318" y="440" transform="rotate(-82 318 440)">Sohna Rd</text>

          {/* glow + radar at the booking */}
          <circle cx={area.x} cy={area.y} r="120" fill="url(#cm-glow)" className="cm-halo" />
          {live && step === 1 && <circle key={`radar-${ai}`} cx={area.x} cy={area.y} r="10" className="cm-radar" />}

          {/* routes from matched players */}
          {step >= 2 &&
            team.map((pi) => (
              <path
                key={`route-${ai}-${pi}`}
                className="cm-route"
                d={`M${PLAYERS[pi][0]} ${PLAYERS[pi][1]} L${area.x} ${area.y}`}
              />
            ))}

          {/* players */}
          {PLAYERS.map((p, i) => {
            const on = team.includes(i) && step >= 1
            const moved = team.includes(i) && step >= 2
            const k = team.indexOf(i)
            const tx = moved ? area.x - p[0] + (k - 1) * 13 : 0
            const ty = moved ? area.y - p[1] + 16 : 0
            return (
              <g key={i} className={`cm-player${on ? ' on' : ''}`} style={{ transform: `translate(${tx}px, ${ty}px)` }}>
                <circle cx={p[0]} cy={p[1]} r={on ? 7 : 4.5} />
              </g>
            )
          })}

          {/* areas */}
          {AREAS.map((a, i) => (
            <g
              key={a.name}
              className={`cm-area${i === ai ? ' on' : ''}`}
              onClick={() => pick(i)}
              role="button"
              tabIndex={0}
              aria-label={`Show a booking in ${a.name}`}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && pick(i)}
            >
              <circle cx={a.x} cy={a.y} r={i === ai ? 11 : 7} className="cm-pin" />
              <text x={a.x} y={a.y - 18} textAnchor="middle">
                {a.name}
              </text>
            </g>
          ))}

          {/* check-in badge */}
          {step === 3 && (
            <g key={`ok-${ai}`} className="cm-ok">
              <rect x={area.x - 52} y={area.y + 26} width="104" height="30" rx="15" />
              <text x={area.x} y={area.y + 46} textAnchor="middle">
                ✓ Checked in
              </text>
            </g>
          )}
        </svg>
        <p className="cm-note">Schematic map, not to scale · Illustrative booking</p>
      </div>

      <div className="cm-side">
        <div className="sw-card cm-panel">
          <p className="sw-eyebrow">Example booking · {area.name}</p>
          <p className="cm-job">
            {area.job} <span>for a {area.place}</span>
          </p>
          <ol className="cm-steps">
            {STEPS.map((s, i) => (
              <li key={s.key} className={i < step ? 'done' : i === step ? 'now' : ''}>
                <span className="cm-ico">
                  <Icon name={i < step ? 'check' : s.icon} />
                </span>
                <div>
                  <b>{s.title}</b>
                  <small>
                    {i === 0 && `${area.job} at ${area.name}, in the app or on WhatsApp`}
                    {i === 1 && `${count} verified Switch Player${count > 1 ? 's' : ''} nearby`}
                    {i === 2 && `Arriving in about ${eta} min`}
                    {i === 3 && 'The right person, at the right site'}
                  </small>
                </div>
              </li>
            ))}
          </ol>
          <div className="cm-bar" aria-hidden="true">
            <i style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
          </div>
        </div>
        <div className="sw-chips cm-chips">
          {AREAS.map((a, i) => (
            <button key={a.name} type="button" className="sw-chip" aria-pressed={i === ai} onClick={() => pick(i)}>
              {a.name}
            </button>
          ))}
        </div>
        <a
          className="sw-btn"
          href={waLink(`Hi Switch — I need staff in ${area.name}, Gurgaon.`)}
          target="_blank"
          rel="noreferrer"
        >
          Book staff in {area.name} <Icon name="arrow" />
        </a>
      </div>
    </div>
  )
}
