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
    serviceType: page.service,
    provider: {
      '@type': 'LocalBusiness',
      // Same @id as the LocalBusiness node in index.html so Google merges these
      // into one business entity rather than treating them as separate orgs.
      '@id': `${BASE_URL}/#business`,
      name: 'Switch',
      url: BASE_URL,
      email: 'hello@switchlocally.com',
      areaServed: { '@type': 'City', name: 'Gurgaon' },
    },
  }

  // Only attach a rating where genuine reviews are actually rendered on the
  // page (landing / reviews / alias / area pages). Stamping a rating on pages
  // that show no reviews is a Google rich-result policy violation.
  if (page.reviews?.length) {
    serviceSchema.aggregateRating = {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      bestRating: '5',
      reviewCount: String(page.reviews.length),
    }
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
      {/* robots + geo.* are emitted globally in index.html. Repeating them here
          would produce duplicate meta tags on every prerendered page. */}
      {page.keywords && <meta name="keywords" content={page.keywords} />}
      <link rel="canonical" href={canonical} />
      <meta property="og:title" content={page.title} />
      <meta property="og:description" content={page.description} />
      <meta property="og:url" content={canonical} />
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content="Switch" />
      <meta property="og:locale" content="en_IN" />
      {page.serviceImg && <meta property="og:image" content={`${BASE_URL}${page.serviceImg}`} />}
      {page.serviceImg && <meta property="og:image:alt" content={`${page.service} in Gurgaon — verified by Switch`} />}
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
