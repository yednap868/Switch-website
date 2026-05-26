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

  const GURGAON_AREAS = [
    'DLF Phase 1','DLF Phase 3','DLF Phase 4','Sushant Lok','Palam Vihar',
    'Udyog Vihar','Sohna Road','Cyber City','MG Road','Galleria Market',
    'Sector 14','Sector 17','Sector 23','Sector 31','Sector 40','Sector 47',
    'Sector 49','Chakkarpur','Sikanderpur','Nathupur','Greenwood City',
    'Malibu Towne','Sun City',
  ]
  const PINCODES = ['122001','122002','122006','122009','122010','122017','122018','122022']

  const serviceSchema = {
    '@context': 'https://schema.org',
    '@type': 'Service',
    name: `${page.service} in Gurgaon`,
    description: page.description,
    url: canonical,
    areaServed: [
      { '@type': 'City', name: 'Gurgaon', sameAs: 'https://en.wikipedia.org/wiki/Gurugram' },
      ...GURGAON_AREAS.map(n => ({ '@type': 'Place', name: `${n}, Gurgaon` })),
      ...PINCODES.map(p => ({ '@type': 'PostalAddress', postalCode: p, addressLocality: 'Gurgaon', addressRegion: 'Haryana', addressCountry: 'IN' })),
    ],
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      bestRating: '5',
      reviewCount: '500',
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
      <meta name="geo.position" content="28.4595;77.0266" />
      <meta name="ICBM" content="28.4595, 77.0266" />
      {page.keywords && <meta name="keywords" content={page.keywords} />}
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
