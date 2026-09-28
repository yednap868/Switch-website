/* The homepage hero. Motion, all of it optional (prefers-reduced-motion turns
   it off) and none of it hiding content — the prerendered HTML is the full,
   final hero:
     · the role word cycles (staff → cooks → guards …) on its own line, so the
       rest of the headline never reflows
     · the copy rises in, staggered
     · the purple blob breathes; the photo tilts toward the pointer (desktop)
     · the OTP card acts out a check-in: code typed in, then "Checked in ✓"  */
import { useEffect, useRef, useState } from 'react'
import Icon from '../ui/Icon.jsx'
import { EMPLOYER_LOGIN, WHATSAPP_URL } from '../../data/site.js'

const WORDS = ['staff', 'cooks', 'guards', 'helpers', 'waiters', 'packers']
const OTP = '4719'
const FACES = ['/sw-maid.jpg', '/sw-security-guard.jpg', '/sw-cook.jpg', '/sw-general-helper.jpg']

const reduced = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function useCycle(length, ms) {
  const [i, setI] = useState(0)
  useEffect(() => {
    if (reduced()) return
    const t = setInterval(() => setI((v) => (v + 1) % length), ms)
    return () => clearInterval(t)
  }, [length, ms])
  return i
}

/* 0–4 = digits typed, 5 = checked in. Starts at 4 so the server HTML shows the
   whole code. */
function useOtpStage() {
  const [stage, setStage] = useState(4)
  useEffect(() => {
    if (reduced()) return
    let s = 4
    const steps = { 0: 600, 1: 420, 2: 420, 3: 420, 4: 1400, 5: 2600 }
    let t
    const next = () => {
      s = s === 5 ? 0 : s + 1
      setStage(s)
      t = setTimeout(next, steps[s])
    }
    t = setTimeout(next, 2200)
    return () => clearTimeout(t)
  }, [])
  return stage
}

function HeroVisual() {
  const ref = useRef(null)
  const stage = useOtpStage()

  // Pointer tilt, desktop only: sets --rx / --ry on the art box.
  useEffect(() => {
    const el = ref.current
    if (!el || reduced() || !window.matchMedia('(pointer: fine)').matches) return
    let raf = 0
    const move = (e) => {
      const r = el.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        el.style.setProperty('--ry', `${(x * 10).toFixed(2)}deg`)
        el.style.setProperty('--rx', `${(-y * 8).toFixed(2)}deg`)
      })
    }
    const leave = () => {
      el.style.setProperty('--ry', '0deg')
      el.style.setProperty('--rx', '0deg')
    }
    el.addEventListener('pointermove', move)
    el.addEventListener('pointerleave', leave)
    return () => {
      cancelAnimationFrame(raf)
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerleave', leave)
    }
  }, [])

  const checked = stage === 5
  return (
    <div className="sw-art hh-art" ref={ref}>
      <div className="hh-ring" aria-hidden="true" />
      <div className="sw-blob" aria-hidden="true" />
      <div className="hh-tilt">
        <div className="sw-arch">
          <img
            src="/hero-workers.jpg"
            alt="Switch staff in uniform, ready for the shift"
            fetchPriority="high"
          />
        </div>
      </div>
      <span className="hh-spark s1" aria-hidden="true" />
      <span className="hh-spark s2" aria-hidden="true" />
      <span className="hh-spark s3" aria-hidden="true" />

      <div className="sw-float sw-f-ok hh-in" style={{ '--d': '0.9s' }}>
        <span className="dot">
          <Icon name="check" />
        </span>
        <div>
          <b>Staff confirmed</b>
          <span>Often within the day</span>
        </div>
      </div>

      <div className="sw-float hh-trial hh-in" style={{ '--d': '1.1s' }}>
        <b>₹149</b>
        <span>
          3-hour trial
          <br />1 verified worker
        </span>
      </div>

      <div
        className={`sw-float sw-f-otp hh-in${checked ? ' is-done' : ''}`}
        style={{ '--d': '1.3s' }}
        aria-hidden="true"
      >
        <small>{checked ? 'Right person, right site' : 'Share this code on arrival'}</small>
        <div className="hh-otp">
          {OTP.split('').map((d, i) => (
            <span key={i} className={i < stage || checked ? 'on' : ''}>
              {i < stage || checked ? d : ''}
            </span>
          ))}
        </div>
        <div className="hh-otp-state">
          {checked ? (
            <>
              <Icon name="check" /> Checked in
            </>
          ) : (
            'Waiting for the worker…'
          )}
        </div>
      </div>
    </div>
  )
}

export default function HomeHero() {
  const w = useCycle(WORDS.length, 2200)
  return (
    <section className="sw-hero hh">
      <div className="hh-bg" aria-hidden="true">
        <i />
        <i />
      </div>
      <div className="hh-copy">
        <p className="sw-eyebrow hh-in" style={{ '--d': '0s' }}>
          <span className="hh-dot" /> Gurgaon’s on-demand staffing
        </p>
        <h1 className="sw-h1 hh-h1 hh-in" style={{ '--d': '0.08s' }}>
          Switch to{' '}
          {/* Every word shares one grid cell, so the slot is as wide as the
              longest and nothing around it moves when the word changes. */}
          <span className="hh-rot">
            {WORDS.map((x, j) => (
              <span
                key={j === w ? `on-${w}` : x}
                className={`hh-word${j === w ? ' is-on' : ''}`}
                aria-hidden={j === w ? undefined : 'true'}
              >
                {x}
              </span>
            ))}
          </span>
          <br />
          who <em>show up.</em>
        </h1>
        <p className="sw-lead hh-in" style={{ '--d': '0.2s' }}>
          Aadhaar-verified helpers, cooks, guards and housekeeping for your shop, kitchen, warehouse
          or office. Book in minutes, staffed the same day, replaced within 24 hours if anyone
          doesn’t turn up.
        </p>
        <div className="sw-btns hh-in" style={{ '--d': '0.32s' }}>
          <a className="sw-btn hh-cta" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
            Hire staff now <Icon name="arrow" />
          </a>
          <a className="sw-btn line" href="#trial">
            Try for ₹149
          </a>
          <a className="sw-btn line hh-wa" href={WHATSAPP_URL} target="_blank" rel="noreferrer">
            WhatsApp
          </a>
        </div>
        <div className="hh-proof hh-in" style={{ '--d': '0.44s' }}>
          <span className="hh-faces" aria-hidden="true">
            {FACES.map((f) => (
              <img key={f} src={f} alt="" loading="lazy" />
            ))}
          </span>
          <span>
            <b>20,000+</b> verified Switch Players
          </span>
          <i aria-hidden="true" />
          <span>
            <b>1,500+</b> businesses
          </span>
          <i aria-hidden="true" />
          <span>
            <b>24h</b> replacement
          </span>
        </div>
      </div>
      <HeroVisual />
    </section>
  )
}
