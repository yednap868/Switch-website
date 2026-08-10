#!/usr/bin/env node
/**
 * Generate public/sitemap.xml from the shared route manifest so it can never
 * drift from what is actually built.
 * Run: node scripts/gen-sitemap.mjs   (also wired into the build via package.json)
 */
import { writeFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { getRoutes, BASE } from './routes.mjs'
import { BLOG_POSTS } from '../src/data/blogData.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const OUT = join(ROOT, 'public', 'sitemap.xml')

const isoDate = (d) => new Date(d).toISOString().split('T')[0]

/** Last-modified of a source file, so <lastmod> reflects real content changes
 *  instead of "everything changed" on every deploy. */
const mtime = (rel) => {
  try { return isoDate(statSync(join(ROOT, rel)).mtime) }
  catch { return isoDate(Date.now()) }
}

const SEO_DATA_MTIME = mtime('src/data/seoData.js')
const BLOG_INDEX_MTIME = mtime('src/data/blogData.js')
const blogDates = new Map(BLOG_POSTS.map(p => [`blog/${p.slug}`, isoDate(p.updated || p.date)]))

const staticMtimes = {
  '': mtime('src/App.jsx'),
  app: mtime('src/pages/AppPage.jsx'),
  about: mtime('src/pages/AboutPage.jsx'),
  partner: mtime('src/pages/PartnerPage.jsx'),
  blog: BLOG_INDEX_MTIME,
  terms: mtime('src/pages/LegalPage.jsx'),
  privacy: mtime('src/pages/LegalPage.jsx'),
  cancellation: mtime('src/pages/LegalPage.jsx'),
}

function lastmodFor(slug) {
  if (blogDates.has(slug)) return blogDates.get(slug)
  if (slug in staticMtimes) return staticMtimes[slug]
  return SEO_DATA_MTIME
}

const routes = getRoutes()

const urls = routes.map(({ slug, changefreq, priority }) => {
  const loc = slug === '' ? `${BASE}/` : `${BASE}/${slug}`
  return [
    '  <url>',
    `    <loc>${loc}</loc>`,
    `    <lastmod>${lastmodFor(slug)}</lastmod>`,
    `    <changefreq>${changefreq}</changefreq>`,
    `    <priority>${priority}</priority>`,
    '  </url>',
  ].join('\n')
})

const xml =
  '<?xml version="1.0" encoding="UTF-8"?>\n' +
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
  urls.join('\n') +
  '\n</urlset>\n'

writeFileSync(OUT, xml)
console.log(`Wrote ${OUT} - ${urls.length} URLs`)
