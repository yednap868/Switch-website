import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import { BLOG_POSTS } from '../data/blogData.js'
import './Blog.css'

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function BlogIndex() {
  useEffect(() => {
    window.scrollTo(0, 0)
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('anim-in'); obs.unobserve(e.target) }
      }),
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    )
    document.querySelectorAll('[data-anim]').forEach(el => obs.observe(el))
    return () => obs.disconnect()
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
      <Nav />
      <main className="bl-root">
        {/* Header */}
        <section className="bl-hero">
          <div className="bl-hero-bg" aria-hidden="true">
            <div className="bl-hero-grid" />
            <div className="bl-hero-glow" />
          </div>
          <div className="bl-w">
            <div className="bl-hero-inner" data-anim>
              <span className="bl-tag">Switch Blog</span>
              <h1 className="bl-h1">
                Hiring guides for<br />
                <em>Gurgaon families &amp; businesses.</em>
              </h1>
              <p className="bl-lead">
                Honest, practical advice on hiring verified maids, cooks, caretakers, drivers,
                security staff and event staff in Gurgaon — written by the team behind Switch.
              </p>
            </div>
          </div>
        </section>

        {/* Featured */}
        <section className="bl-sec">
          <div className="bl-w">
            <Link to={`/blog/${featured.slug}`} className="bl-feature" data-anim>
              <div className="bl-feature-img">
                <img src={featured.hero} alt={featured.title} loading="eager" />
                <div className="bl-feature-overlay" />
              </div>
              <div className="bl-feature-body">
                <div className="bl-meta">
                  <span className="bl-chip">{featured.category}</span>
                  <span className="bl-meta-sep">·</span>
                  <span>{formatDate(featured.date)}</span>
                  <span className="bl-meta-sep">·</span>
                  <span>{featured.readMins} min read</span>
                </div>
                <h2 className="bl-feature-title">{featured.title}</h2>
                <p className="bl-feature-excerpt">{featured.excerpt}</p>
                <span className="bl-feature-cta">Read the guide →</span>
              </div>
            </Link>
          </div>
        </section>

        {/* Grid */}
        <section className="bl-sec">
          <div className="bl-w">
            <div className="bl-sec-hd" data-anim>
              <span className="bl-tag">More guides</span>
              <h2 className="bl-h2">Read every guide.</h2>
              <p className="bl-sub">Everything we know about hiring verified workers in Gurgaon — straight to the point.</p>
            </div>
            <div className="bl-grid">
              {rest.map((p, i) => (
                <Link to={`/blog/${p.slug}`} className="bl-card" key={p.slug} data-anim style={{'--delay':`${(i%3)*80}ms`}}>
                  <div className="bl-card-img">
                    <img src={p.hero} alt={p.title} loading="lazy" />
                  </div>
                  <div className="bl-card-body">
                    <div className="bl-meta bl-meta--sm">
                      <span className="bl-chip">{p.category}</span>
                      <span>{p.readMins} min</span>
                    </div>
                    <h3 className="bl-card-title">{p.title}</h3>
                    <p className="bl-card-excerpt">{p.excerpt}</p>
                    <span className="bl-card-date">{formatDate(p.date)}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="bl-cta-sec">
          <div className="bl-w">
            <div className="bl-cta" data-anim>
              <h2 className="bl-cta-h">Ready to hire a verified worker?</h2>
              <p className="bl-cta-p">
                Skip the reading and skip ahead. Book a verified maid, cook, caretaker, driver,
                security guard or event staff member in minutes.
              </p>
              <a href="https://app.switchlocally.com/" className="bl-cta-primary">Book Now →</a>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
