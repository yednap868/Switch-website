import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import { SERVICE_LIST } from '../data/seoData.js'
import './NotFoundPage.css'

/**
 * Real 404 page.
 *
 * Unknown URLs previously did `<Navigate to="/" replace />`, which served
 * homepage content under a bogus URL with an HTTP 200 — a classic "soft 404".
 * Google reports those in Search Console and wastes crawl budget on unlimited
 * junk URLs. We now render a genuine not-found page marked `noindex`, and the
 * host serves dist/404.html with a real 404 status.
 */
export default function NotFoundPage() {
  useEffect(() => { window.scrollTo(0, 0) }, [])

  return (
    <>
      <Helmet>
        <title>Page not found (404) | Switch</title>
        <meta name="description" content="This page doesn't exist. Browse verified staffing services for your business in Gurgaon on Switch." />
        <meta name="robots" content="noindex, follow" />
      </Helmet>
      <Nav />
      <main className="nf">
        <div className="nf-wrap">
          <p className="nf-eyebrow">Error 404</p>
          <h1 className="nf-h1">We couldn&rsquo;t find that page.</h1>
          <p className="nf-intro">
            The link may be broken, or the page may have moved. Here are the most
            useful places to go instead.
          </p>

          <section className="nf-sec">
            <h2 className="nf-h2">Popular pages</h2>
            <div className="nf-links">
              <Link to="/" className="nf-link">Home <span aria-hidden="true">&rarr;</span></Link>
              <Link to="/about" className="nf-link">About Switch <span aria-hidden="true">&rarr;</span></Link>
              <Link to="/blog" className="nf-link">Blog <span aria-hidden="true">&rarr;</span></Link>
              <Link to="/partner" className="nf-link">Looking for work? <span aria-hidden="true">&rarr;</span></Link>
            </div>
          </section>

          <section className="nf-sec">
            <h2 className="nf-h2">Hire staff in Gurgaon</h2>
            <div className="nf-links">
              {SERVICE_LIST.map(svc => (
                <Link key={svc.id} to={`/${svc.slug}`} className="nf-link">
                  {svc.name} <span aria-hidden="true">&rarr;</span>
                </Link>
              ))}
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </>
  )
}
