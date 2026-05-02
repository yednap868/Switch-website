import { Helmet } from 'react-helmet-async'

const BASE_URL = 'https://switchlocally.com'

export default function SeoHead({ page }) {
  const canonical = `${BASE_URL}/${page.slug}`

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
    provider: {
      '@type': 'LocalBusiness',
      name: 'Switch',
      url: BASE_URL,
      email: 'hello@switchlocally.com',
      areaServed: { '@type': 'City', name: 'Gurgaon' },
    },
    serviceType: page.service,
    description: page.description,
    url: canonical,
  }

  return (
    <Helmet>
      <title>{page.title}</title>
      <meta name="description" content={page.description} />
      <link rel="canonical" href={canonical} />
      <meta property="og:title" content={page.title} />
      <meta property="og:description" content={page.description} />
      <meta property="og:url" content={canonical} />
      <meta property="og:type" content="website" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={page.title} />
      <meta name="twitter:description" content={page.description} />
      <script type="application/ld+json">{JSON.stringify(serviceSchema)}</script>
      {faqSchema && (
        <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
      )}
    </Helmet>
  )
}
