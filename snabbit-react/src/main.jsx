import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import App from './App.jsx'
import { preloadRoute } from './routes.jsx'
import RouteAnalytics from './components/RouteAnalytics.jsx'
import WhatsAppTracking from './components/WhatsAppTracking.jsx'

/* Note: routes ship pre-rendered (scripts/prerender.mjs) but the client does a
   fresh render rather than hydrating — several pages produce hydration
   mismatches, and a clean render beats a recovered one. Because that discards
   the DOM the browser scrolled to, HashScroll re-applies any #anchor. */
// Load this URL's page chunk first so the render replaces the prerendered HTML
// with the same page, never with an empty loading state.
// Prerendered head tags (title, meta, canonical, JSON-LD) give way to the ones
// React renders and keeps current as the visitor navigates.
document.head.querySelectorAll('[data-pre]').forEach((el) => el.remove())
preloadRoute(window.location.pathname).finally(() => createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <RouteAnalytics />
        <WhatsAppTracking />
        <App />
      </BrowserRouter>
    </HelmetProvider>
  </StrictMode>,
))
