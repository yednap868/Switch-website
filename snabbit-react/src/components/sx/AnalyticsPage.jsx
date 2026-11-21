/* /analytics — website traffic, search and AI visibility for switchlocally.com.
   Data is a snapshot from Vercel Observability (scripts/gen-analytics.mjs →
   src/data/analytics.json), built into the page. Counts only: no IPs or
   user agents. noindex, not linked from the site. */
import { useState } from 'react'
import { Helmet } from 'react-helmet-async'
import Header from '../chrome/Header.jsx'
import Footer from '../chrome/Footer.jsx'
import DATA from '../../data/analytics.json'
import './sx.css'

const fmt = (n) => Number(n || 0).toLocaleString('en-IN')
const COUNTRY = { IN: 'India', US: 'United States', NL: 'Netherlands', SG: 'Singapore', DE: 'Germany', BR: 'Brazil', GB: 'United Kingdom', CA: 'Canada', CN: 'China', IE: 'Ireland', FI: 'Finland', HK: 'Hong Kong', AU: 'Australia', FR: 'France', JP: 'Japan', AE: 'UAE' }
const CAT = {
  people: 'People (pages, images, files)', unknown: 'Unidentified bots', advertising: 'Ad crawlers', search_engine_crawler: 'Search engines',
  search_engine_optimization: 'SEO tools', preview: 'Link previews (WhatsApp etc.)', ai_crawler: 'AI crawlers',
  ai_assistant: 'AI assistants', agent: 'AI agents', monitor: 'Uptime monitors', other: 'Other',
  accessibility: 'Accessibility tools', verification: 'Site verification',
}
const dayLabel = (d) => new Date(d + 'T00:00:00Z').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' })

/* Single-series daily line with a crosshair tooltip. */
function DailyChart({ series, label }) {
  const [hover, setHover] = useState(null)
  const W = 720
  const H = 220
  const P = { l: 40, r: 12, t: 14, b: 26 }
  const max = Math.max(1, ...series.map((d) => d.n))
  const nice = Math.ceil(max / 100) * 100 || 10
  const x = (i) => P.l + (i * (W - P.l - P.r)) / Math.max(1, series.length - 1)
  const y = (v) => P.t + (H - P.t - P.b) * (1 - v / nice)
  const line = series.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(d.n).toFixed(1)}`).join(' ')
  const area = `${line} L${x(series.length - 1)},${y(0)} L${x(0)},${y(0)} Z`
  const ticks = [0, nice / 2, nice]
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    const i = Math.round(((px - P.l) / (W - P.l - P.r)) * (series.length - 1))
    setHover(Math.max(0, Math.min(series.length - 1, i)))
  }
  const h = hover != null ? series[hover] : null
  return (
    <div className="an-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label} per day`} onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={P.l} x2={W - P.r} y1={y(t)} y2={y(t)} className="an-grid" />
            <text x={P.l - 8} y={y(t) + 4} className="an-axis" textAnchor="end">
              {fmt(t)}
            </text>
          </g>
        ))}
        {series.map((d, i) =>
          i % Math.ceil(series.length / 6) === 0 || i === series.length - 1 ? (
            <text key={d.date} x={x(i)} y={H - 6} className="an-axis" textAnchor={i === series.length - 1 ? 'end' : i === 0 ? 'start' : 'middle'}>
              {dayLabel(d.date)}
            </text>
          ) : null,
        )}
        <path d={area} className="an-area" />
        <path d={line} className="an-line" />
        {h && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={P.t} y2={y(0)} className="an-cross" />
            <circle cx={x(hover)} cy={y(h.n)} r="5" className="an-dot" />
          </g>
        )}
      </svg>
      {h && (
        <div className="an-tip" style={{ left: `${(x(hover) / W) * 100}%` }}>
          <b>{fmt(h.n)}</b> {label.toLowerCase()}
          <small>{dayLabel(h.date)}</small>
        </div>
      )}
    </div>
  )
}

/* Ranked horizontal bars, one series, value labelled at the end. */
function Bars({ rows, labelOf = (r) => r.key, empty = 'No data yet' }) {
  if (!rows?.length) return <p className="an-empty">{empty}</p>
  const max = Math.max(...rows.map((r) => r.n))
  return (
    <ol className="an-bars">
      {rows.map((r) => (
        <li key={r.key} title={`${labelOf(r)}: ${fmt(r.n)}`}>
          <span className="an-bl">{labelOf(r)}</span>
          <span className="an-bt">
            <span style={{ width: `${Math.max(2, (r.n / max) * 100)}%` }} />
          </span>
          <b>{fmt(r.n)}</b>
        </li>
      ))}
    </ol>
  )
}

function Tile({ v, l, s }) {
  return (
    <div className="an-tile">
      <b>{v}</b>
      <span>{l}</span>
      {s && <small>{s}</small>}
    </div>
  )
}

function Card({ title, sub, children, wide }) {
  return (
    <section className={`an-card${wide ? ' wide' : ''}`}>
      <header>
        <h2>{title}</h2>
        {sub && <p>{sub}</p>}
      </header>
      {children}
    </section>
  )
}

export default function AnalyticsPage() {
  const d = DATA
  const t = d.totals
  const lh = d.site.lighthouse
  const gen = new Date(d.generatedAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' })
  const people = d.botCategories.find((c) => c.key === 'people')?.n || 0
  const botShare = t.requests ? Math.round(((t.requests - people) / t.requests) * 100) : 0
  return (
    <>
      <Helmet>
        <title>Website analytics | Switch</title>
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <Header />
      <main className="sx an" id="page-main">
        <div className="sx-wrap">
          <div className="an-head">
            <div>
              <p className="sx-eyebrow">switchlocally.com · last {d.days} days</p>
              <h1 className="sx-h2">
                Website analytics<span className="sx-dot">.</span>
              </h1>
            </div>
            <p className="an-gen">Updated {gen} IST · source: Vercel</p>
          </div>

          <div className="an-tiles">
            <Tile v={fmt(t.pageViews)} l="Page views" s="People only, bots excluded" />
            <Tile v={fmt(t.googleReferrals)} l="Visits from Google" s="Search clicks to the site" />
            <Tile v={fmt(t.aiAssistantVisits)} l="AI assistant visits" s="ChatGPT, Claude, Perplexity reading pages" />
            <Tile v={fmt(t.searchCrawlerVisits)} l="Search-engine crawls" s="Google, Bing and others" />
          </div>

          <div className="an-grid2">
            <Card title="Page views per day" sub="People opening a page on switchlocally.com." wide>
              <DailyChart series={d.pageViewsDaily} label="Page views" />
            </Card>

            <Card title="Top pages" sub="Most-viewed pages by people.">
              <Bars rows={d.topPages} />
            </Card>
            <Card title="Where visitors come from" sub="Other sites that sent people here.">
              <Bars rows={d.referrers} empty="Most visitors typed the address or used an app." />
            </Card>

            <Card title="AI visibility" sub="AI assistants that fetched Switch pages to answer someone’s question." wide>
              <div className="an-split">
                <Bars rows={d.aiAssistants} labelOf={(r) => r.label} />
                <DailyChart series={d.aiDaily} label="AI assistant visits" />
              </div>
            </Card>

            <Card title="Search engines crawling" sub="How often search engines re-read the site.">
              <Bars rows={d.searchBots} labelOf={(r) => r.label} />
            </Card>
            <Card title="AI crawlers" sub="Crawlers that train or index for AI products.">
              <Bars rows={d.aiCrawlers} labelOf={(r) => r.label} />
            </Card>

            <Card title="Visitors by country" sub="People only.">
              <Bars rows={d.countries} labelOf={(r) => COUNTRY[r.key] || r.key} />
            </Card>
            <Card title="Who loads the site" sub={`Every request — pages, images and files. ${botShare}% come from bots.`}>
              <Bars rows={d.botCategories} labelOf={(r) => CAT[r.key] || r.key} />
            </Card>

            <Card title="Site health" sub="Lighthouse (mobile) on the homepage and the indexable page count.">
              <div className="an-health">
                {lh &&
                  Object.entries(lh.scores).map(([k, v]) => (
                    <div key={k} className={v >= 90 ? 'ok' : v >= 50 ? 'mid' : 'bad'}>
                      <b>{v}</b>
                      <span>{{ performance: 'Speed', accessibility: 'Accessibility', 'best-practices': 'Best practices', seo: 'SEO' }[k] || k}</span>
                    </div>
                  ))}
              </div>
              {lh && (
                <p className="an-note">
                  First paint {lh.fcp} · Largest paint {lh.lcp} · Layout shift {lh.cls} · Blocking {lh.tbt}
                </p>
              )}
              <p className="an-note">{d.site.sitemapUrls} pages in the sitemap for Google.</p>
            </Card>
            <Card title="Broken links people hit" sub="Pages that returned 404.">
              <Bars rows={d.notFound} empty="None — no visitor hit a broken page." />
            </Card>
          </div>

          <p className="an-foot">
            Google rankings (positions and search keywords) come from Google Search Console and aren’t included yet.
          </p>
        </div>
      </main>
      <Footer cta={false} />
    </>
  )
}
