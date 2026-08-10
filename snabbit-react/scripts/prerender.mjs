#!/usr/bin/env node
/**
 * Static-site generation (SSG) step.
 *
 * WHY THIS EXISTS
 * ---------------
 * This app was a pure client-rendered SPA: every one of its 200+ URLs shipped
 * an empty `<div id="root"></div>`, and all content plus every react-helmet tag
 * (title, description, canonical, JSON-LD) only appeared after JS executed.
 * Googlebot can render JS but defers it; Bing and the AI crawlers the
 * robots.txt explicitly invites (GPTBot, PerplexityBot, ClaudeBot, ...) do not
 * execute JS at all and saw a blank page.
 *
 * This script renders every route with react-dom/server at build time and
 * writes a real HTML file per URL, so crawlers get complete markup with zero
 * JS required. The client then hydrates that markup (see src/main.jsx).
 *
 * Run automatically as part of `npm run build`.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'
import { getRoutes } from './routes.mjs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const DIST = join(ROOT, 'dist')
const SSR_ENTRY = join(ROOT, 'dist-ssr', 'entry-server.js')

if (!existsSync(SSR_ENTRY)) {
  console.error(`\n[prerender] Missing SSR bundle at ${SSR_ENTRY}`)
  console.error('[prerender] Run `vite build --ssr src/entry-server.jsx --outDir dist-ssr` first.\n')
  process.exit(1)
}

const template = readFileSync(join(DIST, 'index.html'), 'utf8')

if (!template.includes('<!--app-html-->') || !template.includes('<!--app-head-->')) {
  console.error('\n[prerender] index.html is missing the <!--app-head--> / <!--app-html--> placeholders.\n')
  process.exit(1)
}

const { render } = await import(pathToFileURL(SSR_ENTRY).href)

/**
 * index.html carries a global `robots` directive so every page gets a sane
 * default. If a page emits its OWN robots tag via Helmet (e.g. the 404 page
 * sets `noindex`), we must drop the template default — two conflicting robots
 * meta tags on one page is ambiguous and easy to get wrong.
 */
const DEFAULT_ROBOTS_RE = /^\s*<meta name="robots"[^>]*>\s*$/m

function buildPage(head, html) {
  let tpl = template
  if (/<meta[^>]+name="robots"/i.test(head)) {
    tpl = tpl.replace(DEFAULT_ROBOTS_RE, '')
  }
  return tpl
    .replace('<!--app-head-->', head)
    .replace('<!--app-html-->', html)
}

const routes = getRoutes()
let ok = 0
const failures = []

for (const { slug } of routes) {
  const url = slug === '' ? '/' : `/${slug}`
  try {
    const { html, head } = render(url)
    const page = buildPage(head, html)

    // Write as `<slug>/index.html` so the URL works on any static host
    // without relying on host-specific "clean URL" rewriting.
    const outDir = slug === '' ? DIST : join(DIST, slug)
    mkdirSync(outDir, { recursive: true })
    writeFileSync(join(outDir, 'index.html'), page)
    ok++
  } catch (err) {
    failures.push({ url, message: err?.message || String(err) })
  }
}

// Dedicated 404 document. Netlify/Vercel serve dist/404.html with a real
// HTTP 404 status, which is what stops junk URLs becoming soft 404s.
try {
  const { html, head } = render('/__not_found__')
  writeFileSync(join(DIST, '404.html'), buildPage(head, html))
  console.log('[prerender] wrote 404.html')
} catch (err) {
  failures.push({ url: '404.html', message: err?.message || String(err) })
}

console.log(`[prerender] rendered ${ok}/${routes.length} routes to static HTML`)

if (failures.length) {
  console.error(`\n[prerender] ${failures.length} route(s) failed:`)
  for (const f of failures.slice(0, 20)) console.error(`  ${f.url} — ${f.message}`)
  process.exit(1)
}
