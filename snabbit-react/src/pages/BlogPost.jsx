import { useEffect } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import { BLOG_POSTS, getBlogPost } from '../data/blogData.js'
import './Blog.css'

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
}

function Block({ b }) {
  switch (b.type) {
    case 'h2':      return <h2 className="bp-h2">{b.content}</h2>
    case 'h3':      return <h3 className="bp-h3">{b.content}</h3>
    case 'p':       return <p className="bp-p">{b.content}</p>
    case 'ul':      return <ul className="bp-list">{b.content.map((it,i) => <li key={i}>{it}</li>)}</ul>
    case 'ol':      return <ol className="bp-list bp-list--ord">{b.content.map((it,i) => <li key={i}>{it}</li>)}</ol>
    case 'callout': return <div className="bp-callout">{b.content}</div>
    default:        return null
  }
}

export default function BlogPost() {
  const { slug } = useParams()
  const post = getBlogPost(slug)

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
  }, [slug])

  if (!post) return <Navigate to="/blog" replace />

  const canonical = `https://switchlocally.com/blog/${post.slug}`
  const related = BLOG_POSTS.filter(p => p.slug !== post.slug).slice(0, 3)

  const articleSchema = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description: post.description,
    image: `https://switchlocally.com${post.hero}`,
    datePublished: post.date,
    dateModified: post.date,
    author: { '@type': 'Organization', name: 'Switch', url: 'https://switchlocally.com' },
    publisher: {
      '@type': 'Organization',
      name: 'Switch',
      logo: { '@type': 'ImageObject', url: 'https://switchlocally.com/hero-workers.jpg' },
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': canonical },
    keywords: post.keywords,
  }

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://switchlocally.com/' },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: 'https://switchlocally.com/blog' },
      { '@type': 'ListItem', position: 3, name: post.title, item: canonical },
    ],
  }

  return (
    <>
      <Helmet>
        <title>{post.title} | Switch</title>
        <meta name="description" content={post.description} />
        <meta name="keywords" content={post.keywords} />
        <link rel="canonical" href={canonical} />
        <meta property="og:title" content={post.title} />
        <meta property="og:description" content={post.description} />
        <meta property="og:url" content={canonical} />
        <meta property="og:type" content="article" />
        <meta property="og:image" content={`https://switchlocally.com${post.hero}`} />
        <meta property="article:published_time" content={post.date} />
        <meta property="article:section" content={post.category} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={post.title} />
        <meta name="twitter:description" content={post.description} />
        <meta name="twitter:image" content={`https://switchlocally.com${post.hero}`} />
        <script type="application/ld+json">{JSON.stringify(articleSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumb)}</script>
      </Helmet>
      <Nav />
      <main className="bp-root">
        {/* Breadcrumb */}
        <div className="bp-crumb-bar">
          <div className="bp-w">
            <nav className="bp-crumb">
              <Link to="/">Home</Link>
              <span>›</span>
              <Link to="/blog">Blog</Link>
              <span>›</span>
              <span className="bp-crumb-current">{post.category}</span>
            </nav>
          </div>
        </div>

        {/* Hero */}
        <article className="bp-article">
          <div className="bp-w bp-w--narrow">
            <header className="bp-header" data-anim>
              <span className="bl-chip">{post.category}</span>
              <h1 className="bp-h1">{post.title}</h1>
              <div className="bp-meta">
                <span>{formatDate(post.date)}</span>
                <span className="bl-meta-sep">·</span>
                <span>{post.readMins} min read</span>
              </div>
              <p className="bp-excerpt">{post.excerpt}</p>
            </header>
            <div className="bp-hero" data-anim style={{'--delay':'80ms'}}>
              <img src={post.hero} alt={post.title} />
            </div>
            <div className="bp-body" data-anim style={{'--delay':'120ms'}}>
              {post.blocks.map((b, i) => <Block key={i} b={b} />)}
            </div>

            {/* Inline CTA */}
            <div className="bp-inline-cta" data-anim>
              <h3 className="bp-inline-h">Need help right now?</h3>
              <p>Book a verified worker in Gurgaon in minutes. Aadhaar-verified, background-checked, pay after work is done.</p>
              <a href="https://app.switchlocally.com/" className="bp-cta-primary">Book on Switch →</a>
            </div>
          </div>
        </article>

        {/* Related */}
        <section className="bl-sec">
          <div className="bl-w">
            <div className="bl-sec-hd" data-anim>
              <span className="bl-tag">Keep reading</span>
              <h2 className="bl-h2">More guides from Switch</h2>
            </div>
            <div className="bl-grid">
              {related.map((p, i) => (
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
      </main>
      <Footer />
    </>
  )
}
