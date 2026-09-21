import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import App from './App.jsx'
import RouteAnalytics from './components/RouteAnalytics.jsx'

/* Note: routes ship pre-rendered (scripts/prerender.mjs) but the client does a
   fresh render rather than hydrating — several pages produce hydration
   mismatches, and a clean render beats a recovered one. Because that discards
   the DOM the browser scrolled to, HashScroll re-applies any #anchor. */
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <RouteAnalytics />
        <App />
      </BrowserRouter>
    </HelmetProvider>
  </StrictMode>,
)
