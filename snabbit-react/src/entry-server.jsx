/**
 * SSR / prerender entry point.
 *
 * Used only at build time by scripts/prerender.mjs to turn every route into a
 * fully-rendered static .html file. The browser never loads this module.
 */
import { StrictMode } from 'react'
import { renderToString } from 'react-dom/server'
// React Router v7 consolidated everything into `react-router`;
// `react-router-dom/server` no longer exists.
import { StaticRouter } from 'react-router'
import { HelmetProvider } from 'react-helmet-async'
import App from './App.jsx'

export function render(url) {
  // react-helmet-async collects <head> tags into this context during render.
  const helmetContext = {}

  const html = renderToString(
    <StrictMode>
      <HelmetProvider context={helmetContext}>
        <StaticRouter location={url}>
          <App />
        </StaticRouter>
      </HelmetProvider>
    </StrictMode>
  )

  // react-helmet-async@3 is a no-op passthrough under React 19: it renders its
  // children inline and never populates `context.helmet`. React 19's built-in
  // document-metadata support is what actually handles these tags, and with
  // `renderToString` it emits them inline in the markup instead of hoisting
  // them. So we extract them here and hand them back separately for the
  // prerenderer to place inside <head>.
  const { helmet } = helmetContext
  const helmetHead = helmet
    ? [helmet.title?.toString(), helmet.meta?.toString(), helmet.link?.toString()]
        .filter(Boolean)
        .join('\n    ')
    : ''

  const extracted = extractHeadTags(html)

  return {
    html: extracted.body,
    head: [helmetHead, extracted.head].filter(Boolean).join('\n    '),
  }
}

/**
 * Pull <title>, <meta> and <link> out of the rendered body markup so they can
 * be placed in <head>, where crawlers actually read them. A <title> or
 * <meta name="description"> inside <body> is not reliably honoured by Google.
 *
 * JSON-LD <script> blocks are deliberately LEFT in the body:
 *   - Google reads JSON-LD from anywhere in the document, head or body.
 *   - React 19 does not hoist ld+json scripts, so moving them would create a
 *     hydration mismatch on the client.
 */
const HEAD_TAG_RE = /<title(?:\s[^>]*)?>[\s\S]*?<\/title>|<meta\s[^>]*?\/?>|<link\s[^>]*?\/?>/gi

function extractHeadTags(markup) {
  const tags = []
  const body = markup.replace(HEAD_TAG_RE, (tag) => {
    tags.push(tag)
    return ''
  })

  // Keep only the first <title>, and drop byte-identical duplicates.
  const seen = new Set()
  let hasTitle = false
  const head = []
  for (const tag of tags) {
    const isTitle = /^<title[\s>]/i.test(tag)
    if (isTitle) {
      if (hasTitle) continue
      hasTitle = true
    }
    if (seen.has(tag)) continue
    seen.add(tag)
    head.push(tag)
  }

  return { body, head: head.join('\n    ') }
}
