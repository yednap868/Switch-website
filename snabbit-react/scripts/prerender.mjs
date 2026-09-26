#!/usr/bin/env node
/**
 * Prerender every route to a static HTML file so each URL ships fully-formed,
 * unique HTML (title, meta, schema, body) with no JS required. This is what
 * lets Google index all ~200 pages instead of only the handful it bothers to
 * render client-side.
 *
 * Runs after `vite build` (client) and `vite build --ssr` (server bundle).
 *   1. Load the compiled SSR `render(url)` from dist-ssr/entry-server.js
 *   2. For every route, render body + Helmet head
 *   3. Strip the shell's default SEO head tags, inject the per-route ones
 *   4. Write dist/<route>/index.html
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'
import { SEO_PAGES } from '../src/data/seoData.js'
import { BLOG_POSTS } from '../src/data/blogData.js'
import { INDUSTRY_PAGES } from '../src/data/industryPages.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const DIST = join(ROOT, 'dist')
const SSR_ENTRY = pathToFileURL(join(ROOT, 'dist-ssr', 'entry-server.js')).href

const { render } = await import(SSR_ENTRY)

// ── Build the full route list (mirror of gen-sitemap.mjs) ──
const routes = [
  '/',
  '/staffing-gurgaon',
  '/app',
  '/about',
  '/partner',
  '/blog',
  '/terms',
  '/privacy',
  '/cancellation',
  '/verify',
  ...INDUSTRY_PAGES.map(p => `/${p.slug}`),
  ...BLOG_POSTS.map(p => `/blog/${p.slug}`),
  ...SEO_PAGES.map(p => `/${p.slug}`),
]
const uniqueRoutes = [...new Set(routes)]

// ── Prepare the shell template ──
let template = readFileSync(join(DIST, 'index.html'), 'utf-8')

// Strip the default SEO head tags from the shell so the per-route Helmet tags
// are the single source of truth (prevents duplicate <title>, og:*, schema…).
function stripDefaultSeo(html) {
  return html
    .replace(/<title>[\s\S]*?<\/title>/i, '')
    .replace(/<meta\s+name="description"[^>]*>/gi, '')
    .replace(/<meta\s+name="keywords"[^>]*>/gi, '')
    .replace(/<meta\s+name="author"[^>]*>/gi, '')
    .replace(/<link\s+rel="canonical"[^>]*>/gi, '')
    .replace(/<meta\s+property="og:[^"]*"[^>]*>/gi, '')
    .replace(/<meta\s+name="twitter:[^"]*"[^>]*>/gi, '')
    .replace(/<script\s+type="application\/ld\+json"[^>]*>[\s\S]*?<\/script>/gi, '')
}
template = stripDefaultSeo(template)

if (!template.includes('<div id="root"></div>')) {
  throw new Error('prerender: could not find <div id="root"></div> in dist/index.html')
}

function outPathFor(route) {
  if (route === '/') return join(DIST, 'index.html')
  return join(DIST, route.replace(/^\//, ''), 'index.html')
}

let ok = 0
let failed = 0
for (const route of uniqueRoutes) {
  try {
    const { html, head } = render(route)
    const page = template
      .replace('</head>', `    ${head}\n  </head>`)
      .replace('<div id="root"></div>', `<div id="root">${html}</div>`)
    const out = outPathFor(route)
    mkdirSync(dirname(out), { recursive: true })
    writeFileSync(out, page)
    ok++
  } catch (err) {
    failed++
    console.error(`✗ prerender failed for ${route}: ${err.message}`)
  }
}

console.log(`Prerendered ${ok}/${uniqueRoutes.length} routes${failed ? ` (${failed} failed)` : ''}`)
if (failed) process.exit(1)
