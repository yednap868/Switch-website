/* "How to book", played on a phone: five screens of the Switch employer app,
   each acting out its step (a finger taps, chips select, the UPI sheet slides
   up, a worker is matched, the OTP checks them in), then an end card. It plays
   from step 1 when scrolled into view, pauses off-screen, and has a story bar
   with play/pause; the step list jumps to any step. Screens are markup laid out at
   280×606 inside the shared device frame (.sw-dev, see AppScreens.jsx);
   their styles are .bd-* / .sd-* in src/styles/switch.css. With reduced
   motion it doesn't autoplay and every screen shows its finished state. */
import { useEffect, useRef, useState } from 'react'
import Icon from './Icon.jsx'

const BOOKING_STEPS = [
  { title: 'Pick a role', line: 'Housekeeping, kitchen, security, helpers and more.', ms: 3400, tag: ['Housekeeping', 'Role selected'] },
  { title: 'Choose the time', line: 'Date, start time and hours. Try 4 hours at ₹429.', ms: 3800, tag: ['₹429', '4 hours · 1 worker'] },
  { title: 'Pay by UPI or card', line: 'One tap. The price you see is the price you pay.', ms: 3600, tag: ['UPI or card', 'No hidden charges'] },
  { title: 'Worker matched', line: 'An Aadhaar-verified Switch Player accepts, often within the hour.', ms: 3400, tag: ['Aadhaar verified', 'Worker accepted'] },
  { title: 'OTP check-in', line: 'Share the code on arrival — the shift starts. No-show? We replace.', ms: 3800, tag: ['OTP check-in', 'Right person, right site'] },
]
const END_MS = 3200
const durationOf = (i) => BOOKING_STEPS[i]?.ms ?? END_MS

const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function Status() {
  return (
    <div className="sd-status" aria-hidden="true">
      <b>9:41</b>
      <span className="sd-island" />
      <span className="sd-sig">
        <i />
        <i />
        <i />
        <em />
      </span>
    </div>
  )
}

function Bar({ title }) {
  return (
    <div className="sd-bar">
      <span className="sd-back">←</span>
      <b>{title}</b>
    </div>
  )
}

function PickScreen() {
  const tiles = [
    ['Cleaning', 'sparkles', 't-lav'],
    ['Kitchen', 'chef', 't-peach'],
    ['Security', 'shield', 't-sky'],
    ['Helper', 'package', 't-mint'],
    ['Waiter', 'utensils', 't-pink'],
    ['Caretaker', 'heart', 't-grey'],
  ]
  return (
    <>
      <Status />
      <div className="sd-top">
        <div>
          <img src="/brand/switch-wordmark-white.png" alt="" className="sd-wm" />
          <span className="sd-loc">
            <Icon name="pin" /> DLF Phase 3
          </span>
        </div>
        <span className="sd-wallet">₹1,240</span>
      </div>
      <p className="sd-h" style={{ fontSize: 22, marginTop: 14 }}>
        What do you <b>need?</b>
      </p>
      <div className="bd-search">
        <Icon name="search" /> Search housekeeping, cook, guard…
      </div>
      <div className="bd-tiles">
        {tiles.map(([n, ic, t], i) => (
          <span key={n} className={`${t}${i === 0 ? ' bd-tap-target' : ''}`}>
            <Icon name={ic} />
            {n}
          </span>
        ))}
      </div>
      <div className="bd-mini-trial">
        <b>₹429</b>
        <span>4-hour trial · Housekeeping</span>
      </div>
      <div className="sd-nav">
        <span className="on">
          <Icon name="building" />
        </span>
        <span>
          <Icon name="cal" />
        </span>
        <span className="sd-sw">
          <Icon name="sparkles" />
        </span>
        <span>
          <Icon name="wallet" />
        </span>
        <span>
          <Icon name="heart" />
        </span>
      </div>
      <span className="bd-finger f-pick" aria-hidden="true" />
    </>
  )
}

function TimeScreen() {
  return (
    <>
      <Status />
      <Bar title="Housekeeping" />
      <div className="sd-hero" style={{ marginTop: 10 }}>
        <img src="/sw-maid.jpg" alt="" />
        <div>
          <span className="sd-eyebrow" style={{ color: 'rgba(255,255,255,.7)' }}>
            AADHAAR VERIFIED
          </span>
          <b className="sd-role">Housekeeping</b>
          <small style={{ color: 'rgba(255,255,255,.7)', fontSize: 9.5 }}>Floors, washrooms, dusting</small>
        </div>
      </div>
      <div className="sd-card">
        <div className="sd-row">
          <b>Date</b>
        </div>
        <div className="sd-chips">
          <span className="bd-sel-a">Today</span>
          <span>Tomorrow</span>
          <span>Wed 30</span>
        </div>
      </div>
      <div className="sd-card">
        <div className="sd-row">
          <b>Start time</b>
          <small className="sd-ok bd-show-b">11:00 AM – 3:00 PM</small>
        </div>
        <div className="sd-chips">
          <span>10:30</span>
          <span className="bd-sel-b">11:00</span>
          <span>11:30</span>
          <span>12:00</span>
        </div>
      </div>
      <div className="sd-card bd-trial-row">
        <span className="sd-sq">
          <Icon name="sparkles" />
        </span>
        <div>
          <b>4-hour trial</b>
          <small>1 verified worker</small>
        </div>
        <b className="bd-price">₹429</b>
      </div>
      <div className="sd-pay">
        <span className="bd-press-c">Continue · ₹429 →</span>
      </div>
      <span className="bd-finger f-time" aria-hidden="true" />
    </>
  )
}

function PayScreen() {
  return (
    <>
      <Status />
      <Bar title="Pay for your trial" />
      <div className="sd-bill" style={{ marginTop: 12 }}>
        <div>
          <span>Housekeeping · 4 hrs</span>
          <b>₹429</b>
        </div>
        <div>
          <span>Today · 11:00 AM</span>
          <b>1 worker</b>
        </div>
        <div className="sd-total">
          <span>To pay</span>
          <b>₹429</b>
        </div>
      </div>
      <div className="sd-card sd-addr">
        <span className="sd-sq">
          <Icon name="pin" />
        </span>
        <div>
          <b>Café · DLF Phase 3</b>
          <small>Shop 12, Cyber Hub, Gurgaon</small>
        </div>
      </div>
      <div className="sd-pay">
        <span className="bd-press-a">
          <Icon name="sparkles" /> Pay ₹429 →
        </span>
      </div>
      <div className="bd-sheet">
        <i className="bd-grab" />
        <b>Pay ₹429 with UPI</b>
        <div className="bd-upi">
          {['UPI app', 'Card', 'Wallet'].map((u, i) => (
            <span key={u} className={i === 0 ? 'bd-sel-upi' : ''}>
              <i />
              {u}
            </span>
          ))}
        </div>
        <div className="bd-paid">
          <span className="sd-check">
            <Icon name="check" />
          </span>
          <b>Payment successful</b>
          <small>₹429 · Booking confirmed</small>
        </div>
      </div>
      <span className="bd-finger f-pay" aria-hidden="true" />
    </>
  )
}

function MatchScreen() {
  return (
    <>
      <Status />
      <Bar title="Your booking" />
      <div className="bd-radar">
        <i />
        <i />
        <span className="sd-check">
          <Icon name="search" />
        </span>
        <b>Finding a verified worker</b>
        <small>Housekeeping · Today, 11:00 AM</small>
      </div>
      <div className="sd-card sd-worker bd-worker">
        <img src="/sw-maid.jpg" alt="" />
        <div>
          <b>Sunita · Housekeeping</b>
          <small>Aadhaar verified · 4.8 ★ · 120+ shifts</small>
          <span className="sd-live">Accepted · arriving 11:00 AM</span>
        </div>
      </div>
      <div className="sd-steps bd-worker" style={{ animationDelay: '1.9s' }}>
        {[
          ['Booked', true],
          ['Worker assigned', true],
          ['On the way', false],
          ['Checked in with OTP', false],
        ].map(([t, d]) => (
          <span key={t} className={d ? 'done' : ''}>
            <i />
            {t}
          </span>
        ))}
      </div>
    </>
  )
}

function OtpScreen() {
  // A fresh code on every play, like a real booking. Never in the server HTML.
  const [otp] = useState(() => String(1000 + Math.floor(Math.random() * 9000)))
  return (
    <>
      <Status />
      <Bar title="Your shift" />
      <div className="sd-card sd-worker" style={{ marginTop: 12 }}>
        <img src="/sw-maid.jpg" alt="" />
        <div>
          <b>Sunita has arrived</b>
          <small>Café · DLF Phase 3</small>
          <span className="sd-live">At your door</span>
        </div>
      </div>
      <div className="sd-card sd-otp">
        <small>Share this code with the worker</small>
        <div className="sd-otp-code">
          {otp.split('').map((d, i) => (
            <span key={i} className="bd-digit" style={{ animationDelay: `${0.5 + i * 0.35}s` }}>
              {d}
            </span>
          ))}
        </div>
      </div>
      <div className="bd-started">
        <span className="sd-check">
          <Icon name="check" />
        </span>
        <div>
          <b>Checked in · shift started</b>
          <small>11:02 AM · ends 3:02 PM</small>
        </div>
      </div>
      <div className="bd-timer">
        <i />
      </div>
    </>
  )
}

function EndScreen() {
  return (
    <>
      <Status />
      <div className="bd-end">
        <span className="sd-check">
          <Icon name="check" />
        </span>
        <b>Staff on site.</b>
        <small>Booked in five taps</small>
        <div className="bd-mini-trial">
          <b>₹429</b>
          <span>Try 4 hours · 1 verified worker</span>
        </div>
      </div>
    </>
  )
}

const SCREENS = [PickScreen, TimeScreen, PayScreen, MatchScreen, OtpScreen, EndScreen]

export default function BookingDemo({ children }) {
  // Server HTML (and reduced motion) shows the first screen in its finished state.
  const [step, setStep] = useState(0)
  const [auto, setAuto] = useState(false)
  const [run, setRun] = useState(0)
  const [inView, setInView] = useState(false)
  const [paused, setPaused] = useState(false)
  const root = useRef(null)
  const left = useRef({ run: 0, ms: durationOf(0) })
  const playing = auto && inView && !paused

  const go = (i) => {
    setStep(i)
    setRun((r) => r + 1)
  }

  useEffect(() => {
    if (reduced()) return
    let seen = false
    const io = new IntersectionObserver(
      ([e]) => {
        setAuto(true)
        setInView(e.isIntersecting)
        // The first look starts at step 1, wherever the loop would have been.
        if (e.isIntersecting && !seen) {
          seen = true
          go(0)
        }
      },
      { threshold: 0.4 },
    )
    io.observe(root.current)
    return () => io.disconnect()
  }, [])

  // Pausing keeps the time left, so play resumes mid-step with the animations.
  useEffect(() => {
    if (!playing) return
    if (left.current.run !== run) left.current = { run, ms: durationOf(step) }
    const started = Date.now()
    const t = setTimeout(() => go((step + 1) % SCREENS.length), left.current.ms)
    return () => {
      clearTimeout(t)
      left.current.ms -= Date.now() - started
    }
  }, [playing, step, run])

  const jump = (i) => {
    setPaused(false)
    go(i)
  }

  const Screen = SCREENS[step]
  const now = BOOKING_STEPS[step]
  const live = BOOKING_STEPS[Math.min(step, BOOKING_STEPS.length - 1)]
  return (
    <div
      ref={root}
      className={`bd${auto ? ' is-live' : ''}${auto && !playing ? ' is-paused' : ''}`}
    >
      <div className="bd-left">
        <ol className="bd-steps">
          {BOOKING_STEPS.map((s, i) => (
            <li key={s.title}>
              <button
                type="button"
                className={i === step ? 'on' : i < step ? 'done' : ''}
                onClick={() => jump(i)}
                aria-current={i === step ? 'step' : undefined}
                aria-label={`Step ${i + 1}: ${s.title}`}
              >
                <span className="bd-n">{i < step ? <Icon name="check" /> : i + 1}</span>
                <span className="bd-t">
                  <b>{s.title}</b>
                  <small>{s.line}</small>
                </span>
              </button>
            </li>
          ))}
        </ol>
        {children}
      </div>
      <div className="bd-stage">
        <div className="bd-story">
          <div className="bd-segs" aria-hidden="true">
            {BOOKING_STEPS.map((s, i) => (
              <span key={s.title} className={i < step ? 'done' : ''}>
                {i === step && <i key={run} style={{ animationDuration: `${s.ms}ms` }} />}
              </span>
            ))}
          </div>
          <button
            type="button"
            className="bd-play"
            onClick={() => setPaused((p) => !p)}
            aria-label={paused ? 'Play walkthrough' : 'Pause walkthrough'}
          >
            <Icon name={paused ? 'play' : 'pause'} />
          </button>
        </div>
        <div className="sw-devs bd-devs">
          <div
            className="sw-dev mid"
            role="img"
            aria-label={`Switch app, step ${Math.min(step + 1, BOOKING_STEPS.length)} of ${BOOKING_STEPS.length}: ${live.title}`}
          >
            <div className="sw-dev-in">
              <div className="sd-screen bd-screen" key={`${step}-${run}`}>
                <Screen />
              </div>
            </div>
          </div>
          {now && (
            <div className={`bd-tag ${step % 2 ? 'l' : 'r'}`} key={`tag-${step}-${run}`} aria-hidden="true">
              <b>{now.tag[0]}</b>
              <span>{now.tag[1]}</span>
            </div>
          )}
        </div>
        <p className="bd-now" key={`now-${step}-${run}`}>
          {now ? (
            <>
              <small>
                Step {step + 1} of {BOOKING_STEPS.length}
              </small>
              <b>{now.title}</b>
              {now.line}
            </>
          ) : (
            <>
              <small>Done</small>
              <b>Staff on site.</b>
              Booked in five taps.
            </>
          )}
        </p>
      </div>
    </div>
  )
}
