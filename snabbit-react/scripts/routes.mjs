/**
 * Single source of truth for every URL the site exposes.
 *
 * Both the sitemap generator and the prerenderer read from here, so the
 * sitemap can never advertise a URL that wasn't actually built (and vice versa).
 */
import { SEO_PAGES } from '../src/data/seoData.js'
import { BLOG_POSTS } from '../src/data/blogData.js'

export const BASE = 'https://switchlocally.com'

// changefreq/priority heuristics: primary landing + near-me + same-day = hot.
function rank(slug) {
  if (slug === '') return { changefreq: 'weekly', priority: '1.0' }
  if (/(near-me|same-day)-|-near-me-/.test(slug)) return { changefreq: 'weekly', priority: '0.9' }
  if (/(cost|reviews)/.test(slug)) return { changefreq: 'monthly', priority: '0.7' }
  return { changefreq: 'weekly', priority: '0.8' }
}

export function getRoutes() {
  const routes = []
  const seen = new Set()

  const add = (slug, changefreq, priority) => {
    if (seen.has(slug)) return
    seen.add(slug)
    routes.push({ slug, changefreq, priority })
  }

  // Static routes
  add('', 'weekly', '1.0')
  add('app', 'monthly', '0.9')
  add('about', 'monthly', '0.7')
  add('partner', 'monthly', '0.7')
  add('blog', 'weekly', '0.7')

  // Legal / trust pages
  // Slugs must match the routes declared in App.jsx.
  add('terms', 'yearly', '0.3')
  add('privacy', 'yearly', '0.3')
  add('cancellation', 'yearly', '0.3')

  // Blog posts
  for (const post of BLOG_POSTS) add(`blog/${post.slug}`, 'monthly', '0.6')

  // All programmatic SEO pages (services x intents + aliases + hyperlocal)
  for (const page of SEO_PAGES) {
    const { changefreq, priority } = rank(page.slug)
    add(page.slug, changefreq, priority)
  }

  return routes
}
