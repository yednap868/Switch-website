/* The hero phone: a working preview of booking with Jyoti. She types each
   question word by word; you answer with tappable tiles/chips, one question
   at a time, exactly the order the app asks. Confirming is ₹0, nearby
   workers get alerted (ringing → seen → yes), and the ₹99 booking fee shows
   up only after someone accepts. Nothing is sent anywhere — it's a preview.

   Server HTML: Jyoti's first question with the role tiles, fully typed. */
import { useEffect, useRef, useState } from 'react'
import { CHAT_STEPS, ROLES } from '../../data/switchHome.js'
import { APP_URL } from '../../data/site.js'

const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const WORKERS = [
  { n: 'Ravi', km: '0.8 km', end: 'yes' },
  { n: 'Sunita', km: '1.1 km', end: 'seen' },
  { n: 'Imran', km: '1.6 km', end: 'yes' },
  { n: 'Pooja', km: '2.2 km', end: 'seen' },
]

/* Types `text` out word by word; returns the visible part. */
function useTyped(text, on) {
  const [n, setN] = useState(() => text.split(' ').length)
  useEffect(() => {
    if (!on || reduced()) return
    const words = text.split(' ').length
    let i = 0
    let id
    const t0 = setTimeout(() => {
      setN(0)
      id = setInterval(() => {
        i += 1
        setN(i)
        if (i >= words) clearInterval(id)
      }, 70)
    }, 0)
    return () => {
      clearTimeout(t0)
      clearInterval(id)
    }
  }, [text, on])
  return text.split(' ').slice(0, n).join(' ')
}

function JyotiLine({ text, live, children }) {
  const shown = useTyped(text, live)
  const done = shown.length >= text.length
  return (
    <div className="sx-b j">
      <p>
        {shown}
        {!done && <span className="sx-caret" aria-hidden="true" />}
      </p>
      {done && children}
    </div>
  )
}

export default function PhoneChat() {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState([])
  const [stage, setStage] = useState('ask') // ask · review · alerting · accepted
  const [alerts, setAlerts] = useState([]) // per worker: 0 · ring · seen · yes
  const [interacted, setInteracted] = useState(false)
  const bodyRef = useRef(null)
  const timers = useRef([])

  useEffect(() => () => timers.current.forEach(clearTimeout), [])
  useEffect(() => {
    const el = bodyRef.current
    if (el && interacted) el.scrollTo({ top: el.scrollHeight, behavior: reduced() ? 'auto' : 'smooth' })
  }, [step, stage, alerts, interacted])

  const later = (fn, ms) => timers.current.push(setTimeout(fn, reduced() ? 0 : ms))

  const answer = (v) => {
    setInteracted(true)
    const next = [...answers, v]
    setAnswers(next)
    if (step + 1 < CHAT_STEPS.length) setStep(step + 1)
    else setStage('review')
  }

  const confirm = () => {
    setStage('alerting')
    setAlerts(WORKERS.map(() => 0))
    WORKERS.forEach((w, i) => {
      later(() => setAlerts((a) => a.map((v, k) => (k === i ? 'ring' : v))), 400 + i * 450)
      later(() => setAlerts((a) => a.map((v, k) => (k === i ? 'seen' : v))), 1500 + i * 600)
      if (w.end === 'yes') later(() => setAlerts((a) => a.map((v, k) => (k === i ? 'yes' : v))), 2600 + i * 700)
    })
    later(() => setStage('accepted'), 3900)
  }

  const restart = () => {
    timers.current.forEach(clearTimeout)
    timers.current = []
    setStep(0)
    setAnswers([])
    setStage('ask')
    setAlerts([])
  }

  const role = answers[0]
  const count = answers[4]
  const yes = WORKERS.filter((w, i) => alerts[i] === 'yes').map((w) => w.n)

  return (
    <div className="sx-phone" aria-label="Preview: booking staff by chatting with Jyoti">
      <div className="sx-phone-notch" aria-hidden="true" />
      <div className="sx-phone-top">
        <img className="sx-jy" src="/img/jyoti-face.webp" alt="" width="36" height="36" />
        <div>
          <b>Jyoti</b>
          <small>{stage === 'alerting' ? 'workers ko alert kar rahi hoon…' : 'online'}</small>
        </div>
      </div>

      <div className="sx-phone-body" ref={bodyRef} aria-live="polite">
        {CHAT_STEPS.slice(0, step + 1).map((s, i) => {
          const live = i === step && stage === 'ask'
          const picked = answers[i]
          return (
            <div key={s.key} className="sx-turn">
              <JyotiLine text={s.q} live={i === step}>
                {live && s.tiles && (
                  <div className="sx-tiles">
                    {ROLES.map((r) => (
                      <button type="button" key={r.k} onClick={() => answer(r.k)}>
                        <span aria-hidden="true">{r.e}</span>
                        {r.k}
                      </button>
                    ))}
                  </div>
                )}
                {live && s.opts && (
                  <div className="sx-opts">
                    {s.opts.map((o) => (
                      <button type="button" key={o} onClick={() => answer(o)}>
                        {o}
                      </button>
                    ))}
                  </div>
                )}
              </JyotiLine>
              {picked && <div className="sx-b u">{picked}</div>}
            </div>
          )
        })}

        {stage !== 'ask' && (
          <div className="sx-turn">
            <div className="sx-sum">
              <small>Aapki booking</small>
              <b>
                {count} × {role}
              </b>
              <span>
                {answers[1]} · {answers[2]} · {answers[3]}
              </span>
              <span>
                Rate: {answers[5]} · {answers[6]}
              </span>
              {stage === 'review' && (
                <button type="button" className="sx-btn sm" onClick={confirm}>
                  Confirm · ₹0
                </button>
              )}
            </div>
          </div>
        )}

        {(stage === 'alerting' || stage === 'accepted') && (
          <div className="sx-turn">
            <JyotiLine text="Paas ke workers ko app ring aur WhatsApp bhej diya. Live dekhiye:" live>
              <ul className="sx-live">
                {WORKERS.map((w, i) => (
                  <li key={w.n} className={`st-${alerts[i] || 'wait'}`}>
                    <img className="sx-av" src={`/av/${w.n.toLowerCase()}.jpg`} alt="" width="28" height="28" loading="lazy" />
                    <span>
                      <b>{w.n}</b> <small>{w.km}</small>
                    </span>
                    <em>
                      {{ ring: 'Ringing', seen: 'Seen', yes: 'Haan ✓' }[alerts[i]] || '—'}
                    </em>
                  </li>
                ))}
              </ul>
            </JyotiLine>
          </div>
        )}

        {stage === 'accepted' && (
          <div className="sx-turn">
            <JyotiLine
              text={`${yes.join(' aur ')} ne haan bola! Ab ₹99 booking fee pay kariye — aapko start OTP milega, aur worker ko aapka address.`}
              live
            >
              <div className="sx-opts">
                <a className="sx-btn sm" href={APP_URL} target="_blank" rel="noreferrer">
                  Book in the app
                </a>
                <button type="button" onClick={restart}>
                  Phir se try karein
                </button>
              </div>
            </JyotiLine>
          </div>
        )}
      </div>

      <div className="sx-phone-in" aria-hidden="true">
        <span>Boliye ya likhiye…</span>
        <i className="sx-mic" />
      </div>
    </div>
  )
}
