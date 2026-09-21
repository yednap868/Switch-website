import { useState } from 'react'
import { Link } from 'react-router-dom'
import Annotate from '../fx/Annotate.jsx'
import CascadeLabel from '../fx/CascadeLabel.jsx'

/* Areas carry their position on the 680×520 map viewBox. Hovering or focusing
   either the pin or the list row highlights both, via the shared area id.
   `anchor` is the matching element id on /staffing-gurgaon. */
const AREAS = [
  { id: 'dlf', name: 'DLF', x: 150, y: 205, anchor: 'dlf-phase-1' },
  { id: 'sushant-lok', name: 'Sushant Lok', x: 296, y: 284, anchor: 'sushant-lok' },
  { id: 'palam-vihar', name: 'Palam Vihar', x: 214, y: 350, anchor: 'palam-vihar' },
  { id: 'udyog-vihar', name: 'Udyog Vihar', x: 360, y: 145, anchor: 'udyog-vihar' },
  { id: 'cyber-city', name: 'Cyber City', x: 453, y: 226, anchor: 'cyber-city' },
  { id: 'mg-road', name: 'MG Road', x: 292, y: 366, anchor: 'mg-road' },
  { id: 'sohna-road', name: 'Sohna Road', x: 465, y: 324, anchor: 'sohna-road' },
  { id: 'sectors', name: 'Sectors 1–49', x: 336, y: 438, anchor: 'areas' },
]

const BOUNDARY =
  'M151 68 214 33 292 47 345 25 417 57 488 45 539 99 584 119 568 177 611 229 581 286 598 345 553 377 538 443 474 462 423 502 354 480 292 506 244 466 177 470 145 416 95 388 112 325 72 276 102 219 81 155Z'

export default function Coverage() {
  const [active, setActive] = useState('dlf')

  /* A full navigation rather than a router push, so the browser scrolls to the
     anchor on the staffing page. */
  const open = (area) => {
    window.location.assign(`/staffing-gurgaon#${area.anchor}`)
  }

  return (
    <section id="coverage" className="coverage-editorial">
      <div className="shell">
        <div className="coverage-heading">
          <div className="coverage-copy">
            <CascadeLabel text="OUR COVERAGE" />
            <h2>
              Built for
              <br />
              <Annotate kind="underline" delay={0.6}>
                Gurgaon.
              </Annotate>
              <br />
              Ready where you work.
            </h2>
            <p>
              From DLF and Sushant Lok to Palam Vihar, Udyog Vihar, Cyber City, Sohna Road, MG Road
              and Sectors 1–49, Switch helps local businesses find dependable staff.
            </p>
            <Link className="coverage-cta" to="/staffing-gurgaon">
              See all coverage areas <b>→</b>
            </Link>
          </div>
          <div className="coverage-data">
            <div>
              <strong>500+</strong>
              <span>Businesses served</span>
            </div>
            <div>
              <strong>GURGAON</strong>
              <span>Our core market</span>
            </div>
            <div>
              <strong>Same-day</strong>
              <span>Staffing available</span>
            </div>
          </div>
        </div>

        <div className="coverage-visual">
          <div className="coverage-map" aria-label="Gurgaon operational coverage map">
            <svg
              viewBox="0 0 680 520"
              role="img"
              aria-label="Gurgaon coverage map showing DLF, Sushant Lok, Palam Vihar, Udyog Vihar, Cyber City, MG Road, Sohna Road and Sectors 1 to 49"
            >
              <defs>
                <linearGradient id="coverage-fill" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#10271a" />
                  <stop offset="1" stopColor="#07100b" />
                </linearGradient>
                <filter id="coverage-glow">
                  <feGaussianBlur stdDeviation="5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <path className="coverage-boundary" d={BOUNDARY} />
              <g className="coverage-roads">
                <path d="M108 294 575 184M146 126 518 424M206 67 371 482M85 357 548 103M127 222 587 327M283 43 290 482M112 394 503 82" />
                <path d="M162 180 254 241 394 214 498 286 449 387 318 365 241 420" />
              </g>
              <path
                className="coverage-route"
                d="M181 181 C253 151 270 245 351 220 S444 177 509 290 S411 405 329 365 S235 392 157 324"
              />
              <g className="coverage-markers">
                {AREAS.map((area) => (
                  <g
                    key={area.id}
                    className={`coverage-marker${active === area.id ? ' is-active' : ''}`}
                    data-area={area.id}
                    transform={`translate(${area.x} ${area.y})`}
                    tabIndex={0}
                    role="button"
                    aria-label={`Highlight ${area.name}`}
                    onMouseEnter={() => setActive(area.id)}
                    onFocus={() => setActive(area.id)}
                    onClick={() => open(area)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        open(area)
                      }
                    }}
                  >
                    <circle cx="0" cy="0" r="6" />
                    <circle className="coverage-marker-pulse" cx="0" cy="0" r="15" />
                    <text x="12" y="4">
                      {area.name}
                    </text>
                  </g>
                ))}
              </g>
            </svg>
            <span className="coverage-map-note mono">LOCAL COVERAGE / GURGAON</span>
            <span className="coverage-map-title">
              Gurgaon
              <br />
              <em>in reach.</em>
            </span>
          </div>

          <div className="coverage-index">
            <div className="coverage-index-head">
              <span className="eyebrow">KEY AREAS WE SERVE</span>
              <span className="mono">SELECT AN AREA TO HIGHLIGHT</span>
            </div>
            <div className="coverage-area-list">
              {AREAS.map((area, i) => (
                <button
                  type="button"
                  key={area.id}
                  className={`coverage-area${active === area.id ? ' is-active' : ''}`}
                  data-area={area.id}
                  onMouseEnter={() => setActive(area.id)}
                  onFocus={() => setActive(area.id)}
                  onClick={() => open(area)}
                >
                  <span>{String(i + 1).padStart(2, '0')}</span>
                  <strong>{area.name}</strong>
                  <i>↗</i>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
