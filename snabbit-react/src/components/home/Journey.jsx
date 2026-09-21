import { useCallback, useEffect, useRef, useState } from 'react'
import Annotate from '../fx/Annotate.jsx'
import CascadeLabel from '../fx/CascadeLabel.jsx'
import { prefersReducedMotion } from '../fx/motion.js'

const STEPS = [
  {
    number: '01',
    title: 'REQUEST',
    line: 'Tell us what you need.',
    note: 'Role, location and timing.',
    meta: 'INPUT / BUSINESS NEED',
    status: 'READY TO START',
    caption: 'One clear brief is all it takes to get started.',
  },
  {
    number: '02',
    title: 'MATCH',
    line: 'We find the right people.',
    note: 'Aadhaar-verified, skill-checked staff.',
    meta: 'SWITCH NETWORK / VERIFIED',
    status: 'PEOPLE FOUND',
    caption: 'Switch matches the requirement to verified people from its network — usually within hours.',
  },
  {
    number: '03',
    title: 'CONFIRM',
    line: 'You confirm the fit.',
    note: 'Review the role and schedule.',
    meta: 'EMPLOYER APP / REVIEW',
    status: 'YOUR CALL',
    caption: 'You review the match and confirm the people you want. Book by the hour, day or a full 7-day team.',
  },
  {
    number: '04',
    title: 'REPORT',
    line: 'They report. You get a clean invoice.',
    note: 'OTP verification on site.',
    meta: 'FIELD / ON ARRIVAL',
    status: 'READY TO WORK',
    caption: 'OTP confirms the right person reached your site. No-show? Instant replacement. Pay against a clear invoice.',
  },
]

const AUTOPLAY_MS = 4000

export default function Journey() {
  const [active, setActive] = useState(0)
  const sectionRef = useRef(null)
  const timerRef = useRef(0)
  const interactedRef = useRef(false)

  const select = useCallback((index) => {
    interactedRef.current = true
    setActive(index)
  }, [])

  /* Autoplay while the section is on screen; any interaction stops it. */
  useEffect(() => {
    const node = sectionRef.current
    if (!node || prefersReducedMotion()) return

    const io = new IntersectionObserver(
      ([entry]) => {
        window.clearInterval(timerRef.current)
        if (entry.isIntersecting && !interactedRef.current) {
          timerRef.current = window.setInterval(() => {
            setActive((i) => (i + 1) % STEPS.length)
          }, AUTOPLAY_MS)
        }
      },
      { threshold: 0.35 },
    )
    io.observe(node)
    return () => {
      io.disconnect()
      window.clearInterval(timerRef.current)
    }
  }, [])

  const onKeyDown = (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault()
      select((active + 1) % STEPS.length)
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault()
      select((active - 1 + STEPS.length) % STEPS.length)
    }
  }

  return (
    <section
      id="how"
      className="journey-section"
      ref={sectionRef}
      style={{ '--journey-progress': `${(active / (STEPS.length - 1)) * 100}%` }}
      data-active-step={active}
    >
      <div className="shell">
        <div className="journey-heading">
          <div className="journey-heading-copy">
            <CascadeLabel text="HOW SWITCH WORKS" />
            <h2>
              From request
              <br />
              to{' '}
              <Annotate kind="underline" delay={0.24}>
                people who show up.
              </Annotate>
            </h2>
          </div>
          <p>
            Tell us what the shift needs. We find the right people, you confirm, and they report
            ready to work.
          </p>
        </div>

        <div className="journey-layout">
          <nav className="journey-index" aria-label="Switch process" onKeyDown={onKeyDown}>
            <span className="journey-index-label mono">THE OPERATING SEQUENCE</span>
            {STEPS.map((step, i) => (
              <button
                key={step.title}
                className={`journey-step${i === active ? ' is-active' : ''}`}
                type="button"
                data-step={i}
                aria-controls="journey-stage"
                aria-selected={i === active}
                onClick={() => select(i)}
              >
                <span className="journey-step-number">{step.number}</span>
                <span className="journey-step-text">
                  <strong>{step.title}</strong>
                  <small>{step.line}</small>
                  <em>{step.note}</em>
                </span>
                <span className="journey-step-signal" aria-hidden="true" />
              </button>
            ))}
          </nav>

          <div className="journey-core">
            <div className="journey-circuit" aria-hidden="true">
              <svg viewBox="0 0 640 110" preserveAspectRatio="none">
                <path className="journey-trace-base" d="M10 55 H630" />
                <path className="journey-trace-progress" d="M10 55 H630" />
              </svg>
              {STEPS.map((step, i) => (
                <span
                  key={step.title}
                  className={`journey-circuit-node node-${i}${i <= active ? ' is-lit' : ''}`}
                />
              ))}
              <span className="journey-data data-1">REQ</span>
              <span className="journey-data data-2">MATCH</span>
              <span className="journey-data data-3">OK</span>
            </div>

            <div className="journey-stage" id="journey-stage" aria-live="polite">
              {STEPS.map((step, i) => (
                <article
                  key={step.title}
                  className={`journey-panel${i === active ? ' is-active' : ''}`}
                  data-panel={i}
                >
                  <div className="journey-panel-meta">
                    <span className="mono">{step.meta}</span>
                    <span className="journey-status">
                      <i /> {step.status}
                    </span>
                  </div>

                  {i === 0 && (
                    <div className="request-composition">
                      <div className="request-copy">
                        <span className="mono">EMPLOYER APP</span>
                        <strong>Hire staff</strong>
                        <span className="request-row">
                          <b>ROLE</b> Cook <i>⌄</i>
                        </span>
                        <span className="request-row">
                          <b>LOCATION</b> Gurgaon <i>⌄</i>
                        </span>
                        <span className="request-row">
                          <b>WHEN</b> Today <i>⌄</i>
                        </span>
                        <span className="request-submit">
                          Submit request <b>↗</b>
                        </span>
                      </div>
                      <img
                        src="/screen-home.png"
                        alt="Switch employer app request screen"
                        loading="lazy"
                      />
                    </div>
                  )}

                  {i === 1 && (
                    <div className="match-composition">
                      <div className="match-photo">
                        <img src="/sw-cook.jpg" alt="Verified Switch cook" loading="lazy" />
                        <span className="verified-stamp">
                          ✓ Aadhaar
                          <br />
                          verified
                        </span>
                      </div>
                      <div className="match-ui">
                        <span className="mono">SHORTLIST / 03</span>
                        <strong>
                          Right people
                          <br />
                          for the shift.
                        </strong>
                        <span className="match-pill">Cook · Gurgaon</span>
                        <span className="match-check">✓ Trained &amp; experienced</span>
                      </div>
                    </div>
                  )}

                  {i === 2 && (
                    <div className="confirm-composition">
                      <img
                        src="/screen-2.png"
                        alt="Switch app staff selection screen"
                        loading="lazy"
                      />
                      <div className="confirm-note">
                        <span className="mono">SELECTED</span>
                        <strong>
                          Review.
                          <br />
                          Confirm.
                          <br />
                          Move on.
                        </strong>
                        <span>Choose the right fit for the role and schedule.</span>
                      </div>
                    </div>
                  )}

                  {i === 3 && (
                    <div className="report-composition">
                      <div className="report-photo">
                        <img
                          src="/sw-driver.jpg"
                          alt="Switch worker ready to start work"
                          loading="lazy"
                        />
                        <span className="arrival-chip">
                          <i /> Reported ready
                        </span>
                      </div>
                      <div className="report-copy">
                        <span className="mono">SHIFT STATUS</span>
                        <strong>
                          People who
                          <br />
                          <Annotate kind="arrow" delay={0.36}>
                            show up.
                          </Annotate>
                        </strong>
                        <span>They arrive ready for the work. You get on with the day.</span>
                      </div>
                    </div>
                  )}

                  <div className="journey-caption">
                    <strong>
                      {step.number} / {step.title}
                    </strong>
                    <span>{step.caption}</span>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>

        <div className="journey-trust">
          <span className="mono">THE SWITCH STANDARD</span>
          <span>
            <b>✓</b> Aadhaar verified
          </span>
          <span>
            <b>↯</b> Staff in a day
          </span>
          <span>
            <b>↻</b> Replacement guarantee
          </span>
          <span>
            <b>₹</b> Transparent billing
          </span>
        </div>
      </div>
    </section>
  )
}
