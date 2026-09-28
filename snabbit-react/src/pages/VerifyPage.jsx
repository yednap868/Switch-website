import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { lookupCertificate } from '../data/certificates'
import './VerifyPage.css'

const BASE_URL = 'https://switchlocally.com'

export default function VerifyPage() {
  const [params] = useSearchParams()
  const idFromUrl = params.get('id') || ''
  const [query, setQuery] = useState(idFromUrl)
  const [syncedId, setSyncedId] = useState(idFromUrl)

  // Re-seed the input when the ?id= in the URL changes, without an effect.
  if (syncedId !== idFromUrl) {
    setSyncedId(idFromUrl)
    setQuery(idFromUrl)
  }

  useEffect(() => { if (!window.location.hash) window.scrollTo(0, 0) }, [])

  const cert = lookupCertificate(idFromUrl)
  const searched = idFromUrl.trim().length > 0

  const onSubmit = (e) => {
    e.preventDefault()
    const clean = query.trim()
    // update the URL so the result is shareable / bookmarkable
    window.location.search = clean ? `?id=${encodeURIComponent(clean)}` : ''
  }

  return (
    <>
      <Helmet>
        <title>Verify a Certificate | Switch</title>
        <meta name="description" content="Verify the authenticity of an internship or experience certificate issued by Switch (Third Wave Labs Private Limited)." />
        <link rel="canonical" href={`${BASE_URL}/verify`} />
        <meta name="robots" content="noindex" />
        <meta property="og:title" content="Verify a Certificate | Switch" />
        <meta property="og:description" content="Confirm a certificate issued by Switch (Third Wave Labs Private Limited)." />
        <meta property="og:url" content={`${BASE_URL}/verify`} />
      </Helmet>
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="sw-wrap verify">
        <div className="verify-wrap">
          <header className="verify-head">
            <span className="verify-seal" aria-hidden="true">
              <Icon name="shield" />
            </span>
            <p className="sw-eyebrow">Certificate Verification</p>
            <h1 className="sw-h1 verify-title">Verify a Switch Certificate</h1>
            <p className="verify-intro">
              Enter or scan the certificate ID to confirm it was genuinely issued by
              Switch (Third Wave Labs Private Limited).
            </p>
          </header>

          <form className="sw-card sw-form verify-form" onSubmit={onSubmit}>
            <label className="sw-field" htmlFor="cert-id">Certificate ID</label>
            <div className="verify-row">
              <input
                id="cert-id"
                className="sw-inp"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. SWITCH/INT/2026/0007"
                aria-label="Certificate ID"
                autoComplete="off"
                spellCheck={false}
              />
              <button className="sw-btn" type="submit">
                <Icon name="search" /> Verify
              </button>
            </div>
          </form>

          {searched && cert && (
            <div className="sw-card verify-card verify-ok" role="status">
              <div className="verify-badge">
                <span className="mark" aria-hidden="true">✓</span> Verified — Genuine Certificate
              </div>
              <dl className="verify-details">
                <div><dt>Name</dt><dd>{cert.name}</dd></div>
                <div><dt>Certificate</dt><dd>Certificate of Completion — {cert.type}</dd></div>
                <div><dt>Role</dt><dd>{cert.role}</dd></div>
                <div><dt>Duration</dt><dd>{cert.duration}</dd></div>
                <div><dt>Period</dt><dd>{cert.start} — {cert.end}</dd></div>
                <div><dt>Date of Issue</dt><dd>{cert.issued} · {cert.location}</dd></div>
                <div><dt>Certificate No.</dt><dd>{cert.displayId}</dd></div>
                <div><dt>Issued by</dt><dd>Switch · Third Wave Labs Private Limited</dd></div>
              </dl>
              <p>
                This confirms the above certificate is recorded in Switch's issuance register.
              </p>
            </div>
          )}

          {searched && !cert && (
            <div className="sw-card verify-card verify-bad" role="status">
              <div className="verify-badge verify-badge-bad">
                <span className="mark" aria-hidden="true">!</span> No match found
              </div>
              <p>
                We couldn't find a certificate with the ID <b>{idFromUrl}</b> in our register.
                Please check the ID and try again, or contact us to confirm.
              </p>
              <p>
                Email <a href="mailto:hr@switchlocally.com">hr@switchlocally.com</a> with a copy of the certificate.
              </p>
            </div>
          )}

          {!searched && (
            <p className="verify-hint">
              Tip: scan the QR code printed on the certificate, or type the Certificate No.
              exactly as shown (e.g. <b>SWITCH/INT/2026/0007</b>).
            </p>
          )}

          <p className="verify-back"><Link to="/">← Back to Switch</Link></p>
        </div>
      </main>
      <Footer />
    </>
  )
}
