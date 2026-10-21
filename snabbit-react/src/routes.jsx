import { lazy } from 'react'
import { INDUSTRY_LINKS } from './data/siteIndex.js'

/* Every page except home is split into its own chunk, so the home page doesn't
   download the content of ~200 other pages. A page whose chunk has already
   loaded renders synchronously; one that hasn't falls back to React.lazy.
   main.jsx preloads the chunk for the URL being opened before the first render,
   and the prerender script preloads them all, so neither ever shows a blank
   Suspense fallback in place of the prerendered page. */
function page(loader) {
  let Loaded = null
  const load = () =>
    loader().then((m) => {
      Loaded = m.default
    })
  const Lazy = lazy(loader)
  function Page(props) {
    return Loaded ? <Loaded {...props} /> : <Lazy {...props} />
  }
  Page.load = load
  return Page
}

export const SeoPage = page(() => import('./pages/SeoPage.jsx'))
export const PartnerPage = page(() => import('./pages/PartnerPage.jsx'))
export const AboutPage = page(() => import('./pages/AboutPage.jsx'))
export const BlogIndex = page(() => import('./pages/BlogIndex.jsx'))
export const BlogPost = page(() => import('./pages/BlogPost.jsx'))
export const AppPage = page(() => import('./pages/AppPage.jsx'))
export const LegalPage = page(() => import('./pages/LegalPage.jsx'))
export const StaffingPage = page(() => import('./pages/StaffingPage.jsx'))
export const VerifyPage = page(() => import('./pages/VerifyPage.jsx'))
export const IndustryPage = page(() => import('./pages/IndustryPage.jsx'))

const ALL = [SeoPage, PartnerPage, AboutPage, BlogIndex, BlogPost, AppPage, LegalPage, StaffingPage, VerifyPage, IndustryPage]
const INDUSTRY_PATHS = new Set(INDUSTRY_LINKS.map((p) => `/${p.slug}`))

/* Mirror of the <Routes> table in App.jsx: which page chunk serves a path. */
function pageFor(pathname) {
  const path = pathname.replace(/\/+$/, '') || '/'
  if (path === '/') return null
  if (path === '/partner') return PartnerPage
  if (path === '/about') return AboutPage
  if (path === '/blog') return BlogIndex
  if (path.startsWith('/blog/')) return BlogPost
  if (path === '/app') return AppPage
  if (path === '/terms' || path === '/privacy' || path === '/cancellation') return LegalPage
  if (path === '/staffing-gurgaon') return StaffingPage
  if (INDUSTRY_PATHS.has(path)) return IndustryPage
  if (path === '/verify') return VerifyPage
  return SeoPage
}

export function preloadRoute(pathname) {
  const p = pageFor(pathname)
  return p ? p.load() : Promise.resolve()
}

export function preloadAll() {
  return Promise.all(ALL.map((p) => p.load()))
}
