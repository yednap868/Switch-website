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

const { render, preloadAll } = await import(SSR_ENTRY)
// Page chunks are code-split; load them all so renderToString never suspends.
await preloadAll()

// ── Build the full route list (mirror of gen-sitemap.mjs) ──
const routes = [
  '/',
  '/staffing-gurgaon',
  '/retail-staffing-gurgaon',
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

// React 19 renders <title>, <meta>, <link> and JSON-LD where the component
// sits, so in the server markup they land inside <div id="root">. Crawlers
// ignore a canonical (and may ignore other tags) outside <head>, so move them
// there. Tags are marked data-pre so main.jsx can drop them before React adds
// its own on the client (otherwise the title would go stale on navigation).
const HEAD_TAG = /<title>[\s\S]*?<\/title>|<meta\b[^>]*>|<link\b[^>]*>|<script type="application\/ld\+json">[\s\S]*?<\/script>/g
function liftHeadTags(body) {
  const tags = []
  const html = body.replace(HEAD_TAG, (tag) => {
    tags.push(/^<link\b[^>]*rel="preload"/.test(tag) ? tag : tag.replace(/^<(\w+)/, '<$1 data-pre=""'))
    return ''
  })
  return { html, tags: tags.join('\n    ') }
}

function outPathFor(route) {
  if (route === '/') return join(DIST, 'index.html')
  return join(DIST, route.replace(/^\//, ''), 'index.html')
}

let ok = 0
let failed = 0
for (const route of uniqueRoutes) {
  try {
    const { html: body, head } = render(route)
    const { html, tags } = liftHeadTags(body)
    // A page that sets its own robots tag (e.g. noindex) replaces the shell's.
    const shell = /<meta[^>]*name="robots"/i.test(tags)
      ? template.replace(/<meta\s+name="robots"[^>]*>\s*/i, '')
      : template
    const page = shell
      .replace('</head>', `    ${[head, tags].filter(Boolean).join('\n    ')}\n  </head>`)
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
