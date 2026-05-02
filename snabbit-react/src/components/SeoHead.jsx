import { Helmet } from 'react-helmet-async'

const BASE_URL = 'https://switchlocally.com'

export default function SeoHead({ page }) {
  const canonical = `${BASE_URL}/${page.slug}`

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: BASE_URL },
      { '@type': 'ListItem', position: 2, name: page.service, item: `${BASE_URL}/${page.serviceId}-gurgaon` },
      { '@type': 'ListItem', position: 3, name: page.h1, item: canonical },
    ],
  }

  const faqSchema = page.faqs?.length ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: page.faqs.map(f => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  } : null

  const serviceSchema = {
    '@context': 'https://schema.org',
    '@type': 'Service',
    name: `${page.service} in Gurgaon`,
    description: page.description,
    url: canonical,
    areaServed: { '@type': 'City', name: 'Gurgaon' },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      bestRating: '5',
      reviewCount: '1000',
    },
    provider: {
      '@type': 'LocalBusiness',
      name: 'Switch',
      url: BASE_URL,
      email: 'hello@switchlocally.com',
      areaServed: { '@type': 'City', name: 'Gurgaon' },
    },
  }

  const webPageSchema = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: page.title,
    description: page.description,
    url: canonical,
    inLanguage: 'en-IN',
    dateModified: new Date().toISOString().split('T')[0],
    breadcrumb: breadcrumbSchema,
  }

  return (
    <Helmet>
      <title>{page.title}</title>
      <meta name="description" content={page.description} />
      <meta name="robots" content="index, follow" />
      <meta name="geo.region" content="IN-HR" />
      <meta name="geo.placename" content="Gurgaon" />
      <link rel="canonical" href={canonical} />
      <meta property="og:title" content={page.title} />
      <meta property="og:description" content={page.description} />
      <meta property="og:url" content={canonical} />
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="Switch" />
      {page.serviceImg && <meta property="og:image" content={`${BASE_URL}${page.serviceImg}`} />}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={page.title} />
      <meta name="twitter:description" content={page.description} />
      {page.serviceImg && <meta name="twitter:image" content={`${BASE_URL}${page.serviceImg}`} />}
      <script type="application/ld+json">{JSON.stringify(webPageSchema)}</script>
      <script type="application/ld+json">{JSON.stringify(serviceSchema)}</script>
      {faqSchema && <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>}
    </Helmet>
  )
}
