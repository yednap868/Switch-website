/* The /work phone: a worker telling Jyoti they're free. She asks what work,
   until when, how far — marks them available — then a job rings in like a
   ride request and one tap accepts it. A preview; nothing is sent. */
import { useEffect, useRef, useState } from 'react'
import Icon from '../ui/Icon.jsx'
import { ROLES } from '../../data/switchHome.js'

const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const STEPS = [
  { key: 'role', q: 'Namaste! Main Jyoti. Aap kaun sa kaam karte ho?', tiles: true },
  { key: 'until', q: 'Aaj kab tak free ho?', opts: ['2 PM tak', '6 PM tak', 'Raat 10 tak'] },
  { key: 'far', q: 'Kitni door tak ja sakte ho?', opts: ['2 km', '5 km', '10 km'] },
]

export default function WorkerChat() {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState([])
  const [stage, setStage] = useState('ask') // ask · available · ringing · accepted
  const bodyRef = useRef(null)
  const timers = useRef([])
  useEffect(() => () => timers.current.forEach(clearTimeout), [])
  useEffect(() => {
    const el = bodyRef.current
    if (el && answers.length) el.scrollTo({ top: el.scrollHeight, behavior: reduced() ? 'auto' : 'smooth' })
  }, [answers, stage])

  const answer = (v) => {
    const next = [...answers, v]
    setAnswers(next)
    if (step + 1 < STEPS.length) setStep(step + 1)
    else {
      setStage('available')
      timers.current.push(setTimeout(() => setStage('ringing'), reduced() ? 0 : 1800))
    }
  }
  const restart = () => {
    timers.current.forEach(clearTimeout)
    timers.current = []
    setStep(0)
    setAnswers([])
    setStage('ask')
  }
  const role = answers[0]

  return (
    <div className="sx-phone" aria-label="Preview: a worker finding work by chatting with Jyoti">
      <div className="sx-phone-notch" aria-hidden="true" />
      <div className="sx-phone-top">
        <span className="sx-jy" aria-hidden="true">
          J
        </span>
        <div>
          <b>Jyoti</b>
          <small>{stage === 'ask' ? 'online' : 'aap available ho'}</small>
        </div>
      </div>

      <div className="sx-phone-body" ref={bodyRef} aria-live="polite">
        <div className="sx-b u">Aaj free hoon, kaam chahiye</div>
        {STEPS.slice(0, step + 1).map((s, i) => {
          const live = i === step && stage === 'ask'
          return (
            <div key={s.key} className="sx-turn">
              <div className="sx-b j">
                <p>{s.q}</p>
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
              </div>
              {answers[i] && <div className="sx-b u">{answers[i]}</div>}
            </div>
          )
        })}

        {stage !== 'ask' && (
          <div className="sx-b j">
            <p>
              Ho gaya! Aap <b>{answers[1]}</b> available ho, <b>{answers[2]}</b> tak. Paas ka kaam aate hi aapka
              phone bajega.
            </p>
          </div>
        )}

        {(stage === 'ringing' || stage === 'accepted') && (
          <div className={`sx-jobring${stage === 'ringing' ? ' on' : ''}`}>
            <div className="sx-ring-top">
              <span className="sx-ring-ico">
                <Icon name="phone" />
              </span>
              <div>
                <small>Naya kaam · abhi</small>
                <b>{role}</b>
              </div>
            </div>
            <dl>
              <div>
                <dt>Doori</dt>
                <dd>1.4 km</dd>
              </div>
              <div>
                <dt>Samay</dt>
                <dd>Aaj 4 PM · 4 ghante</dd>
              </div>
              <div>
                <dt>Kiraya</dt>
                <dd>Poora aapka, seedha</dd>
              </div>
            </dl>
            {stage === 'ringing' && (
              <div className="sx-ring-btns">
                <button type="button" className="no" onClick={restart}>
                  Chhodein
                </button>
                <button type="button" className="yes" onClick={() => setStage('accepted')}>
                  Accept
                </button>
              </div>
            )}
          </div>
        )}

        {stage === 'accepted' && (
          <div className="sx-b j">
            <p>
              Pakka! Employer ke booking confirm karte hi aapko address mil jayega. Pahunch ke OTP se kaam shuru —
              kaam ke baad poora kiraya seedha aapko, cash ya UPI.
            </p>
            <div className="sx-opts">
              <button type="button" onClick={restart}>
                Phir se dekhein
              </button>
            </div>
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
