import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs } from '../components/ui/Blocks.jsx'
import { BLOG_POSTS } from '../data/blogData.js'
import './Blog.css'

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

/* Card used on /blog and in "Keep reading" under each post. */
export function PostCard({ p }) {
  return (
    <Link to={`/blog/${p.slug}`} className="sw-card sw-press bl-card">
      {p.hero && (
        <div className="bl-card-img">
          <img src={p.hero} alt={p.title} loading="lazy" />
        </div>
      )}
      <div className="bl-card-body">
        <div className="bl-tags">
          <span className="sw-pill">{p.category}</span>
          <span className="sw-tag">{p.readMins} min read</span>
        </div>
        <h3 className="bl-card-title">{p.title}</h3>
        <p className="bl-card-excerpt">{p.excerpt}</p>
        <span className="bl-card-foot">
          <span>{formatDate(p.date)}</span>
          <span className="sw-link">
            Read <Icon name="arrow" />
          </span>
        </span>
      </div>
    </Link>
  )
}

export default function BlogIndex() {
  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0)
  }, [])

  const blogSchema = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Switch Blog — Hiring Guides for Gurgaon',
    url: 'https://switchlocally.com/blog',
    description: 'Hiring guides, safety tips and verified-staffing advice for families and businesses in Gurgaon — maids, cooks, caretakers, drivers, security guards, bartenders and more.',
    publisher: { '@type': 'Organization', name: 'Switch', url: 'https://switchlocally.com' },
    blogPost: BLOG_POSTS.map(p => ({
      '@type': 'BlogPosting',
      headline: p.title,
      url: `https://switchlocally.com/blog/${p.slug}`,
      datePublished: p.date,
      description: p.description,
    })),
  }

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://switchlocally.com/' },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: 'https://switchlocally.com/blog' },
    ],
  }

  const [featured, ...rest] = BLOG_POSTS

  return (
    <>
      <Helmet>
        <title>Switch Blog — Hiring Guides for Domestic &amp; Business Staff in Gurgaon</title>
        <meta name="description" content="Complete hiring guides for Gurgaon — how to hire verified maids, cooks, caretakers, drivers, security guards and event staff. Tips on Aadhaar verification, pricing, replacement policies and more — from Switch, Gurgaon's trusted staffing platform." />
        <meta name="keywords" content="Switch blog, hire verified maid Gurgaon guide, home cook Gurgaon, elderly caretaker Gurgaon, security guard vs bouncer, personal driver Gurgaon, event staff Gurgaon, Aadhaar verification domestic help, switchlocally.com" />
        <link rel="canonical" href="https://switchlocally.com/blog" />
        <meta property="og:title" content="Switch Blog — Hiring Guides for Gurgaon" />
        <meta property="og:description" content="Hiring guides, safety tips and verified staffing advice for families and businesses across Gurgaon." />
        <meta property="og:url" content="https://switchlocally.com/blog" />
        <meta property="og:type" content="website" />
        <script type="application/ld+json">{JSON.stringify(blogSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
      </Helmet>
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="sw-wrap bl-root">
        <Crumbs items={[['Blog']]} />

        <section className="bl-hero">
          <p className="sw-eyebrow">Switch Blog</p>
          <h1 className="sw-h1 bl-h1">
            Hiring guides for <em>Gurgaon families &amp; businesses.</em>
          </h1>
          <p className="sw-lead">
            Honest, practical advice on hiring verified maids, cooks, caretakers, drivers,
            security staff and event staff in Gurgaon — written by the team behind Switch.
          </p>
        </section>

        {/* Featured */}
        <section aria-label="Featured guide">
          <Link to={`/blog/${featured.slug}`} className="sw-card sw-press bl-feature">
            {featured.hero && (
              <div className="bl-feature-img">
                <img src={featured.hero} alt={featured.title} loading="eager" />
              </div>
            )}
            <div className="bl-feature-body">
              <div className="bl-tags">
                <span className="sw-pill">{featured.category}</span>
                <span className="sw-tag">{featured.readMins} min read</span>
                <span className="sw-tag">{formatDate(featured.date)}</span>
              </div>
              <h2 className="bl-feature-title">{featured.title}</h2>
              <p className="bl-feature-excerpt">{featured.excerpt}</p>
              <span className="sw-btn sm bl-feature-cta">
                Read the guide <Icon name="arrow" />
              </span>
            </div>
          </Link>
        </section>

        {/* Grid */}
        <section className="sw-sec">
          <div className="sw-head">
            <p className="sw-eyebrow">More guides</p>
            <h2 className="sw-h2">
              Read every <em>guide.</em>
            </h2>
            <p className="sw-lead">
              Everything we know about hiring verified Switch Players in Gurgaon — straight to the point.
            </p>
          </div>
          <div className="sw-grid sw-g3 bl-grid">
            {rest.map((p) => (
              <PostCard p={p} key={p.slug} />
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="sw-sec" style={{ paddingTop: 0 }}>
          <div className="sw-feature bl-cta">
            <p className="sw-eyebrow">Ready when you are</p>
            <h2>
              Ready to hire a verified <em>Switch Player?</em>
            </h2>
            <p>
              Skip the reading and skip ahead. Book a verified maid, cook, caretaker, driver,
              security guard or event staff member in minutes.
            </p>
            <div className="sw-btns">
              <a href="https://app.switchlocally.com/" className="sw-btn white">
                Book Now <Icon name="arrow" />
              </a>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
