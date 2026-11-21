/* 404 — prerendered to dist/404.html so a wrong URL gets a real 404 status
   (not a soft 404) and a way back into the site. */
import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import Header from '../chrome/Header.jsx'
import Footer from '../chrome/Footer.jsx'
import './sx.css'

const POPULAR = [
  ['/staffing-gurgaon', 'Staffing in Gurgaon'],
  ['/cook-gurgaon', 'Cook in Gurgaon'],
  ['/home-cleaning-gurgaon', 'Home cleaning'],
  ['/restaurant-staffing-gurgaon', 'Restaurant staff'],
  ['/work', 'Find work'],
  ['/blog', 'Blog'],
]

export default function NotFound() {
  return (
    <>
      <Helmet>
        <title>Page not found | Switch</title>
        <meta name="robots" content="noindex" />
      </Helmet>
      <Header />
      <main className="sx sx-404" id="page-main">
        <div className="sx-wrap">
          <p className="sx-eyebrow">404</p>
          <h1 className="sx-h1">
            Ye page nahi mila<span className="sx-dot">.</span>
          </h1>
          <p className="sx-lead">The link may be old or mistyped. Try one of these, or just ask Jyoti for staff.</p>
          <div className="sx-btns">
            <Link className="sx-btn" to="/">
              Go home <Icon name="arrow" />
            </Link>
            <Link className="sx-btn ghost" to="/staffing-gurgaon">
              All services
            </Link>
          </div>
          <nav className="sx-rolechips" aria-label="Popular pages">
            {POPULAR.map(([to, l]) => (
              <Link key={to} to={to}>
                {l}
              </Link>
            ))}
          </nav>
        </div>
      </main>
      <Footer />
    </>
  )
}
