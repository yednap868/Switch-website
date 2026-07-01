#!/usr/bin/env node
/**
 * Generate public/sitemap.xml from the actual page data so it never drifts.
 * Run: node scripts/gen-sitemap.mjs   (also wired into the build via package.json)
 */
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { SEO_PAGES } from '../src/data/seoData.js'
import { BLOG_POSTS } from '../src/data/blogData.js'

const BASE = 'https://switchlocally.com'
const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT = join(__dirname, '..', 'public', 'sitemap.xml')

// changefreq/priority heuristics: primary landing + near-me + same-day = hot.
function rank(slug) {
  if (slug === '') return { c: 'weekly', p: '1.0' }
  if (/(near-me|same-day)-|-near-me-/.test(slug)) return { c: 'weekly', p: '0.9' }
  if (/(cost|reviews)/.test(slug)) return { c: 'monthly', p: '0.7' }
  return { c: 'weekly', p: '0.8' }
}

const urls = []
const seen = new Set()
const add = (path, c, p) => {
  const loc = `${BASE}/${path}`.replace(/\/$/, path === '' ? '/' : '')
  if (seen.has(loc)) return
  seen.add(loc)
  urls.push(`  <url><loc>${loc}</loc><changefreq>${c}</changefreq><priority>${p}</priority></url>`)
}

// static routes
add('', 'weekly', '1.0')
add('app', 'monthly', '0.9')
add('about', 'monthly', '0.7')
add('partner', 'monthly', '0.7')
add('blog', 'weekly', '0.7')

// blog posts
for (const post of BLOG_POSTS) add(`blog/${post.slug}`, 'monthly', '0.6')

// all programmatic SEO pages (services × intents + aliases + hyperlocal)
for (const page of SEO_PAGES) {
  const { c, p } = rank(page.slug)
  add(page.slug, c, p)
}

const xml =
  `<?xml version="1.0" encoding="UTF-8"?>\n` +
  `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  urls.join('\n') +
  `\n</urlset>\n`

writeFileSync(OUT, xml)
console.log(`Wrote ${OUT} — ${urls.length} URLs`)
