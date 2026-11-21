/* "Four steps. You only talk." — an auto-playing stepper. The left list is
   the four steps with a progress bar on the active one; the right stage acts
   each step out: a chat being typed, the rate slider moving up, workers going
   ringing → seen → yes, then the ₹99 receipt with the start OTP.
   Click a step to jump; hover/focus pauses. Reduced motion: no autoplay, each
   stage shows its finished frame. Server HTML: step 1, finished. */
import { useEffect, useRef, useState } from 'react'
import Icon from '../ui/Icon.jsx'
import { STEPS } from '../../data/switchHome.js'

const DUR = 5200
const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/* t: 0→1 progress through the active step (1 = finished frame). */
function StageTalk({ t }) {
  const line = 'Kal 11 baje 2 cook chahiye, Sector 49'
  const shown = line.slice(0, Math.round(line.length * Math.min(1, t / 0.45)))
  return (
    <div className="hs-chat">
      <div className="sx-b j">
        <p>Namaste! Kaun sa kaam hai?</p>
      </div>
      <div className="sx-b u">
        {shown}
        {t < 0.45 && <span className="sx-caret" aria-hidden="true" />}
      </div>
      {t > 0.55 && (
        <div className="sx-b j hs-pop">
          <p>Theek hai — 2 Cook, kal 11 AM. Kitne ghante ka kaam hai?</p>
          <div className="sx-opts">
            {['2 ghante', '4 ghante', '6 ghante'].map((o, i) => (
              <span key={o} className={t > 0.8 && i === 1 ? 'on' : ''}>
                {o}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StageRate({ t }) {
  const p = Math.min(1, Math.max(0, (t - 0.15) / 0.55))
  const level = p < 0.34 ? 0 : p < 0.8 ? 1 : 2
  const labels = ['Role minimum', 'Minimum + ₹20', 'Minimum + ₹50']
  const speed = ['Normal', 'Faster', 'Fastest']
  return (
    <div className="hs-rate">
      <small>Hourly rate · Cook</small>
      <b className="hs-rate-v">{labels[level]}</b>
      <div className="hs-track" aria-hidden="true">
        <span className="hs-fill" style={{ width: `${8 + p * 84}%` }} />
        <span className="hs-knob" style={{ left: `${8 + p * 84}%` }} />
      </div>
      <div className="hs-ticks" aria-hidden="true">
        <span>Min</span>
        <span>+₹20</span>
        <span>+₹50</span>
      </div>
      <div className="hs-speed">
        <Icon name="timer" /> Match speed: <b>{speed[level]}</b>
      </div>
      <p className="hs-note">You decide. Jyoti never picks the rate for you.</p>
    </div>
  )
}

const PEOPLE = [
  { n: 'Ravi', km: '0.8 km', at: 0.12, end: 'yes', endAt: 0.62 },
  { n: 'Sunita', km: '1.1 km', at: 0.22, end: 'seen' },
  { n: 'Imran', km: '1.6 km', at: 0.32, end: 'yes', endAt: 0.78 },
  { n: 'Pooja', km: '2.2 km', at: 0.42, end: 'seen' },
]
function StageLive({ t }) {
  const st = (w) => (t < w.at ? 'wait' : t < w.at + 0.14 ? 'ring' : w.endAt && t >= w.endAt ? 'yes' : 'seen')
  const yes = PEOPLE.filter((w) => st(w) === 'yes').length
  return (
    <div className="hs-live">
      <div className="hs-live-top">
        <span className="hs-free">Confirmed · ₹0</span>
        <span>
          <b>{yes}</b>/2 said yes
        </span>
      </div>
      <ul className="sx-live">
        {PEOPLE.map((w) => {
          const s = st(w)
          return (
            <li key={w.n} className={`st-${s}`}>
              <img className="sx-av" src={`/av/${w.n.toLowerCase()}.jpg`} alt="" width="28" height="28" loading="lazy" />
              <span>
                <b>{w.n}</b> <small>{w.km}</small>
              </span>
              <em>{{ ring: 'Ringing', seen: 'Seen', yes: 'Haan ✓', wait: '—' }[s]}</em>
            </li>
          )
        })}
      </ul>
      <p className="hs-note">App ring + WhatsApp to the nearest workers.</p>
    </div>
  )
}

function StagePay({ t }) {
  const paid = t > 0.3
  const otp = t > 0.5
  const addr = t > 0.7
  return (
    <div className="hs-pay">
      <div className={`hs-receipt${paid ? ' paid' : ''}`}>
        <span>Booking fee</span>
        <b>₹99</b>
        <em>{paid ? 'Paid ✓' : 'Pay now'}</em>
      </div>
      <div className={`hs-otp${otp ? ' on' : ''}`}>
        <small>Start OTP</small>
        <div>
          {'4719'.split('').map((d, i) => (
            <span key={i}>{otp ? d : '•'}</span>
          ))}
        </div>
      </div>
      <ul className="hs-after">
        <li className={addr ? 'on' : ''}>
          <Icon name="pin" /> Ravi & Imran get your address
        </li>
        <li className={t > 0.85 ? 'on' : ''}>
          <Icon name="wallet" /> Fare goes to them after the work — cash or UPI
        </li>
      </ul>
    </div>
  )
}

const STAGES = [StageTalk, StageRate, StageLive, StagePay]

export default function HowSteps() {
  const [i, setI] = useState(0)
  const [t, setT] = useState(1)
  const [paused, setPaused] = useState(false)
  const [visible, setVisible] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el || reduced() || !('IntersectionObserver' in window)) return
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { threshold: 0.35 })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    if (!visible || paused) return
    let start = performance.now() - t * DUR
    if (t >= 1) start = performance.now()
    let raf
    const tick = (now) => {
      const p = (now - start) / DUR
      if (p >= 1.15) {
        setI((v) => (v + 1) % STEPS.length)
        setT(0)
        return
      }
      setT(Math.min(1, p))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // restart the loop on step change; t is read only at start
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i, visible, paused])

  const go = (n) => {
    setI(n)
    setT(reduced() ? 1 : 0)
  }
  const Stage = STAGES[i]

  return (
    <div
      className="hs"
      ref={ref}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <ol className="hs-list">
        {STEPS.map((s, n) => (
          <li key={s.n} className={n === i ? 'on' : n < i ? 'done' : ''}>
            <button type="button" onClick={() => go(n)} aria-current={n === i ? 'step' : undefined}>
              <span className="sx-n">{n < i ? <Icon name="check" /> : s.n}</span>
              <span className="hs-txt">
                <b>{s.t}</b>
                <span className="hs-d">{s.d}</span>
              </span>
            </button>
            {n === i && (
              <span className="hs-bar" aria-hidden="true">
                <span style={{ transform: `scaleX(${t})` }} />
              </span>
            )}
          </li>
        ))}
      </ol>
      <div className="hs-stage" aria-live="polite">
        <div className="hs-stage-top">
          <span className="sx-jy" aria-hidden="true">
            J
          </span>
          <b>Step {STEPS[i].n}</b>
          <span>{STEPS[i].t}</span>
        </div>
        <div className="hs-stage-body" key={i}>
          <Stage t={t} />
        </div>
      </div>
    </div>
  )
}
