import { useState } from 'react'
import Annotate from '../fx/Annotate.jsx'
import { FORM_ROLES } from '../../data/homeContent.js'
import {
  CALL_URL,
  EMAIL,
  EMPLOYER_LOGIN,
  MAPS_URL,
  PHONE_DISPLAY,
  waLink,
} from '../../data/site.js'

const encodeForm = (data) =>
  Object.keys(data)
    .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(data[k])}`)
    .join('&')

const EMPTY = { business: '', phone: '', role: '', count: '', area: '', message: '' }

export default function FinalCta({ onToast }) {
  const [form, setForm] = useState(EMPTY)
  const [status, setStatus] = useState('idle') // idle | sending | done | error
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  /* Posts to the Netlify form defined in index.html — field names must stay
     in sync with that hidden form. */
  const submit = (e) => {
    e.preventDefault()
    setStatus('sending')
    fetch('/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: encodeForm({ 'form-name': 'request-staff', 'bot-field': '', ...form }),
    })
      .then(() => {
        setStatus('done')
        onToast?.('Request sent — our team will call you back shortly.')
      })
      .catch(() => {
        setStatus('error')
        onToast?.("Couldn't send — please WhatsApp or call us instead.")
      })
  }

  return (
    <section className="final-cta" id="request">
      <div className="shell">
        <div className="final-cta-main">
          <div className="final-cta-copy">
            <div className="eyebrow">READY TO GET STARTED</div>
            <h2>
              Reliable people
              <br />
              for your business
              <br />
              are just a few{' '}
              <Annotate kind="underline" delay={0.72}>
                clicks away.
              </Annotate>
            </h2>
            <p>
              Tell us what you need, and our team will find verified, trained staff for your
              business — quickly and hassle-free.
            </p>
            <div className="final-actions">
              <a className="btn primary" href={EMPLOYER_LOGIN} target="_blank" rel="noreferrer">
                Hire staff <b>→</b>
              </a>
              <a
                className="btn ghost"
                href={waLink('Hi Switch — I need help hiring staff for my business.')}
                target="_blank"
                rel="noreferrer"
              >
                Talk to our team <b>↗</b>
              </a>
            </div>
            <div className="final-trust">
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

          <figure className="final-worker">
            <div className="final-worker-image">
              <img src="/hero-workers.jpg" alt="Switch workers ready for a shift" loading="lazy" />
              <span className="final-worker-label mono">THE RIGHT PEOPLE / FOR EVERY SHIFT</span>
            </div>
            <figcaption>
              <span>People in motion.</span>
              <strong>Ready when you are.</strong>
            </figcaption>
          </figure>
        </div>

        <div className="support-rail" id="request-staff">
          <div className="support-intro">
            <span className="eyebrow">STILL HAVE QUESTIONS?</span>
            <h3>
              We&apos;re here
              <br />
              <span>to help.</span>
            </h3>
            <p>
              Our team is ready to answer your questions, understand your requirements, and help you
              find the right people for your business.
            </p>

            <div className="request-details">
              <div className="request-summary">Prefer to send your requirement?</div>

              {status === 'done' ? (
                <div className="request-thanks">
                  <span className="request-tick">✓</span>
                  <strong>Got it{form.business ? `, ${form.business}` : ''}.</strong>
                  <p>
                    Our team will call you on <b>{form.phone || 'your number'}</b> shortly. For
                    anything urgent, WhatsApp us now.
                  </p>
                  <a
                    className="btn primary"
                    href={waLink('Hi Switch — I just sent a staffing request.')}
                    target="_blank"
                    rel="noreferrer"
                  >
                    WhatsApp us <b>↗</b>
                  </a>
                </div>
              ) : (
                <form
                  id="request-form"
                  name="request-staff"
                  method="POST"
                  data-netlify="true"
                  netlify-honeypot="bot-field"
                  onSubmit={submit}
                >
                  <input type="hidden" name="form-name" value="request-staff" />
                  <p hidden>
                    <label>
                      Don&apos;t fill this: <input name="bot-field" />
                    </label>
                  </p>
                  <div className="form-grid">
                    <div className="form-field">
                      <label htmlFor="business">Business name</label>
                      <input
                        id="business"
                        name="business"
                        required
                        value={form.business}
                        onChange={set('business')}
                        placeholder="e.g. Yum Yum Cha"
                      />
                    </div>
                    <div className="form-field">
                      <label htmlFor="phone">Phone / WhatsApp</label>
                      <input
                        id="phone"
                        name="phone"
                        required
                        type="tel"
                        autoComplete="tel"
                        value={form.phone}
                        onChange={set('phone')}
                        placeholder="10-digit mobile"
                      />
                    </div>
                    <div className="form-field">
                      <label htmlFor="role">Role needed</label>
                      <select id="role" name="role" required value={form.role} onChange={set('role')}>
                        <option value="">Choose a role</option>
                        {FORM_ROLES.map((role) => (
                          <option key={role}>{role}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-field">
                      <label htmlFor="count">How many?</label>
                      <input
                        id="count"
                        name="count"
                        value={form.count}
                        onChange={set('count')}
                        placeholder="e.g. 3"
                      />
                    </div>
                    <div className="form-field full">
                      <label htmlFor="area">Area / locality</label>
                      <input
                        id="area"
                        name="area"
                        value={form.area}
                        onChange={set('area')}
                        placeholder="e.g. DLF Phase 2, Udyog Vihar"
                      />
                    </div>
                    <div className="form-field full">
                      <label htmlFor="message">Anything else? (optional)</label>
                      <textarea
                        id="message"
                        name="message"
                        value={form.message}
                        onChange={set('message')}
                        placeholder="Shift timing, start date, etc."
                      />
                    </div>
                  </div>
                  <button className="btn form-submit" type="submit" disabled={status === 'sending'}>
                    {status === 'sending' ? 'Sending…' : 'Send request'} <b>↗</b>
                  </button>
                  {status === 'error' && (
                    <p className="form-error">
                      Couldn&apos;t send — please WhatsApp or call us instead.
                    </p>
                  )}
                  <p className="form-fine">No obligation. We call you back to confirm.</p>
                </form>
              )}
            </div>
          </div>

          <div className="support-links">
            <a className="support-link" href={CALL_URL}>
              <span className="support-icon">⌕</span>
              <span>
                <strong>Call</strong>
                <small>{PHONE_DISPLAY}</small>
              </span>
              <b>↗</b>
            </a>
            <a className="support-link" href={waLink()} target="_blank" rel="noreferrer">
              <span className="support-icon">◌</span>
              <span>
                <strong>WhatsApp</strong>
                <small>Chat with our team</small>
              </span>
              <b>↗</b>
            </a>
            <a className="support-link" href={`mailto:${EMAIL}`}>
              <span className="support-icon">@</span>
              <span>
                <strong>Email</strong>
                <small>{EMAIL}</small>
              </span>
              <b>↗</b>
            </a>
            <a className="support-link" href={MAPS_URL} target="_blank" rel="noreferrer">
              <span className="support-icon">⌖</span>
              <span>
                <strong>Visit</strong>
                <small>Gurgaon office</small>
              </span>
              <b>↗</b>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
