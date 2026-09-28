import { useEffect } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import Header from '../components/chrome/Header.jsx'
import Footer from '../components/chrome/Footer.jsx'
import Icon from '../components/ui/Icon.jsx'
import { Crumbs, CtaFeature } from '../components/ui/Blocks.jsx'
import { PostCard } from './BlogIndex.jsx'
import { BLOG_POSTS, getBlogPost } from '../data/blogData.js'
import './Blog.css'

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
}

function Block({ b }) {
  switch (b.type) {
    case 'h2':      return <h2>{b.content}</h2>
    case 'h3':      return <h3>{b.content}</h3>
    case 'p':       return <p>{b.content}</p>
    case 'ul':      return <ul>{b.content.map((it, i) => <li key={i}>{it}</li>)}</ul>
    case 'ol':      return <ol>{b.content.map((it, i) => <li key={i}>{it}</li>)}</ol>
    case 'callout': return <aside className="bp-callout">{b.content}</aside>
    default:        return null
  }
}

export default function BlogPost() {
  const { slug } = useParams()
  const post = getBlogPost(slug)

  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0)
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
        <title>{`${post.title} | Switch`}</title>
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
      <a className="skip-link" href="#page-main">
        Skip to main content
      </a>
      <Header />
      <main id="page-main" className="sw-wrap bp-root">
        <Crumbs items={[['Blog', '/blog'], [post.category]]} />

        <article className="bp-article">
          <header className="bp-header">
            <div className="bl-tags">
              <span className="sw-pill">{post.category}</span>
              <span className="sw-tag">{post.readMins} min read</span>
            </div>
            <h1 className="bp-h1">{post.title}</h1>
            <p className="bp-meta">
              By Switch · <time dateTime={post.date}>{formatDate(post.date)}</time>
            </p>
            <p className="bp-excerpt">{post.excerpt}</p>
          </header>

          {post.hero && (
            <div className="bp-hero">
              <img src={post.hero} alt={post.title} fetchPriority="high" />
            </div>
          )}

          <div className="bp-prose">
            {post.blocks.map((b, i) => <Block key={i} b={b} />)}
          </div>

          {/* Inline CTA */}
          <div className="sw-card bp-inline-cta">
            <div>
              <h2 className="sw-h3">Need help right now?</h2>
              <p className="sw-muted">
                Book a verified Switch Player in Gurgaon in minutes. Aadhaar-verified,
                background-checked, transparent rates.
              </p>
            </div>
            <a href="https://app.switchlocally.com/" className="sw-btn">
              Book on Switch <Icon name="arrow" />
            </a>
          </div>
        </article>

        {/* Related */}
        <section className="sw-sec">
          <div className="sw-row-head">
            <div className="sw-head" style={{ marginBottom: 0 }}>
              <p className="sw-eyebrow">Keep reading</p>
              <h2 className="sw-h2">
                More guides from <em>Switch</em>
              </h2>
            </div>
            <Link className="sw-link" to="/blog">
              All guides <Icon name="arrow" />
            </Link>
          </div>
          <div className="sw-grid sw-g3 bl-grid">
            {related.map((p) => (
              <PostCard p={p} key={p.slug} />
            ))}
          </div>
        </section>

        <CtaFeature />
      </main>
      <Footer />
    </>
  )
}
