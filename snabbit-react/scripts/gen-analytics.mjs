#!/usr/bin/env node
/**
 * Snapshot of website analytics for /analytics, written to
 * src/data/analytics.json (built into the page). Pulls aggregates from Vercel Observability
 * (`vercel metrics`, needs a logged-in Vercel CLI) plus site facts from the
 * built pages. No IPs, user agents or other personal data are stored —
 * only counts by day, page, referrer site, country and bot.
 *
 *   node scripts/gen-analytics.mjs            # last 30 days
 *   DAYS=7 node scripts/gen-analytics.mjs
 */
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const DAYS = Number(process.env.DAYS || 30)
const PROJECT = process.env.VERCEL_PROJECT || 'switch-website'
const SCOPE = process.env.VERCEL_SCOPE || 'yednap868s-projects'
const HTML = 'contentType:"text/html; charset=utf-8"'
const HUMAN = 'botCategory:""'

function metrics(metric, { group, filters = [], limit = 10, gran } = {}) {
  const args = ['metrics', metric, '-p', PROJECT, '--scope', SCOPE, '-s', `${DAYS}d`, '--json', '-l', String(limit)]
  if (group) args.push('--group-by', group)
  if (gran) args.push('-g', gran)
  for (const f of filters) args.push('-f', f)
  const out = execFileSync('vercel', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], cwd: ROOT, maxBuffer: 256 * 1024 * 1024 })
  return JSON.parse(out)
}
const valKey = (row) => Object.keys(row).find((k) => k.endsWith('_count'))
const rows = (res, dim) => (res.summary || []).map((r) => ({ key: r[dim], n: r[valKey(r)] }))
function daily(res) {
  const by = {}
  for (const r of res.data || []) {
    const d = r.timestamp.slice(0, 10)
    by[d] = (by[d] || 0) + r[valKey(r)]
  }
  return Object.entries(by).sort().map(([date, n]) => ({ date, n }))
}

const IGNORE_PATH = /^\/(assets|av|img|brand|logos|reviews)\/|\.(png|jpe?g|webp|svg|ico|js|css|txt|xml|json|mp4|woff2?)$/i
const BOT_LABEL = {
  'oai-searchbot': 'ChatGPT Search', 'chatgpt-user': 'ChatGPT (user)', 'gpt-actions': 'ChatGPT actions',
  'gptbot': 'OpenAI GPTBot', 'claude-user': 'Claude (user)', 'claudebot': 'Anthropic ClaudeBot',
  'claude-searchbot': 'Claude Search', 'perplexitybot': 'Perplexity', 'perplexity-user': 'Perplexity (user)',
  'duckassistbot': 'DuckDuckGo Assist', 'exauser': 'Exa', 'googlebot': 'Google', 'bingbot': 'Bing',
  'googleother': 'Google (other)', 'yandexbot': 'Yandex', 'duckduckbot': 'DuckDuckGo', 'baiduspider': 'Baidu',
  'petalbot': 'Huawei Petal', 'exasearchbot': 'Exa Search', 'applebot': 'Apple', 'meta-externalagent': 'Meta AI',
  'bytespider': 'ByteDance', 'ccbot': 'Common Crawl', 'amazonbot': 'Amazon',
}
const label = (b) => BOT_LABEL[b] || b

console.log(`Collecting last ${DAYS} days for ${PROJECT}…`)
const pageViewsDaily = daily(metrics('vercel.request.count', { filters: [HTML, HUMAN], gran: '1d' }))
const requestsDaily = daily(metrics('vercel.request.count', { gran: '1d' }))
const topPages = rows(metrics('vercel.request.count', { group: 'requestPath', filters: [HTML, HUMAN], limit: 40 }), 'requestPath')
  .filter((r) => r.key && !IGNORE_PATH.test(r.key))
  .slice(0, 15)
const referrers = rows(metrics('vercel.request.count', { group: 'referrerHostname', filters: [HTML, HUMAN], limit: 25 }), 'referrerHostname')
  .filter((r) => r.key && !/switchlocally\.com$|vercel\.app$/.test(r.key))
  .slice(0, 10)
const countries = rows(metrics('vercel.request.count', { group: 'clientIpCountry', filters: [HTML, HUMAN], limit: 8 }), 'clientIpCountry')
const botCategories = rows(metrics('vercel.request.count', { group: 'botCategory', limit: 12 }), 'botCategory').map((r) => ({
  key: r.key || 'people',
  n: r.n,
}))
const searchBots = rows(metrics('vercel.request.count', { group: 'botName', filters: ['botCategory:"search_engine_crawler"'], limit: 8 }), 'botName').map((r) => ({ ...r, label: label(r.key) }))
const aiAssistants = rows(metrics('vercel.ai_traffic.assistant.count', { group: 'botName', limit: 10 }), 'botName').map((r) => ({ ...r, label: label(r.key) }))
const aiAssistantPages = rows(metrics('vercel.ai_traffic.assistant.count', { group: 'requestPath', limit: 25 }), 'requestPath')
  .filter((r) => r.key && !IGNORE_PATH.test(r.key))
  .slice(0, 10)
const aiCrawlers = rows(metrics('vercel.ai_traffic.crawler.count', { group: 'botName', limit: 10 }), 'botName').map((r) => ({ ...r, label: label(r.key) }))
const aiDaily = daily(metrics('vercel.ai_traffic.assistant.count', { gran: '1d' }))
const notFound = rows(metrics('vercel.request.count', { group: 'requestPath', filters: ['httpStatus:404', HUMAN], limit: 30 }), 'requestPath')
  .filter((r) => r.key && !IGNORE_PATH.test(r.key))
  .slice(0, 10)

// Site facts from the build
let sitemapUrls = 0
const sm = join(ROOT, 'public', 'sitemap.xml')
if (existsSync(sm)) sitemapUrls = (readFileSync(sm, 'utf8').match(/<loc>/g) || []).length
let lighthouse = null
const lhFile = process.env.LIGHTHOUSE_JSON
if (lhFile && existsSync(lhFile)) {
  const d = JSON.parse(readFileSync(lhFile, 'utf8'))
  const a = d.audits
  lighthouse = {
    scores: Object.fromEntries(Object.entries(d.categories).map(([k, v]) => [k, Math.round(v.score * 100)])),
    fcp: a['first-contentful-paint'].displayValue,
    lcp: a['largest-contentful-paint'].displayValue,
    cls: a['cumulative-layout-shift'].displayValue,
    tbt: a['total-blocking-time'].displayValue,
  }
}

const sum = (xs) => xs.reduce((s, x) => s + x.n, 0)
const out = {
  generatedAt: new Date().toISOString(),
  days: DAYS,
  totals: {
    pageViews: sum(pageViewsDaily),
    requests: sum(requestsDaily),
    aiAssistantVisits: sum(aiAssistants),
    aiCrawlerVisits: sum(aiCrawlers),
    searchCrawlerVisits: sum(searchBots),
    googleReferrals: (referrers.find((r) => /google\./.test(r.key)) || { n: 0 }).n,
  },
  pageViewsDaily,
  requestsDaily,
  aiDaily,
  topPages,
  referrers,
  countries,
  botCategories,
  searchBots,
  aiAssistants,
  aiAssistantPages,
  aiCrawlers,
  notFound,
  site: { sitemapUrls, lighthouse },
}
writeFileSync(join(ROOT, 'src', 'data', 'analytics.json'), JSON.stringify(out, null, 2) + '\n')
console.log(`Wrote src/data/analytics.json — ${out.totals.pageViews} page views, ${out.totals.aiAssistantVisits} AI assistant visits`)
