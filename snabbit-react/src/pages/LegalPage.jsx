import { useEffect } from 'react'
import { Helmet } from 'react-helmet-async'
import { Nav, Footer } from '../App.jsx'
import './LegalPage.css'

const CONTACT_EMAIL = 'hello@switchlocally.com'
const PHONE_DISPLAY = '+91 83688 28660'
const LAST_UPDATED = '24 July 2026'

/* ─── POLICY CONTENT ──────────────────────────────────
   Plain-language policies that reflect how Switch actually
   operates. Have these reviewed by a lawyer before relying
   on them for anything contentious. */
const POLICIES = {
  terms: {
    slug: 'terms',
    title: 'Terms & Conditions',
    intro: 'These terms govern your use of Switch and the staffing services we provide to businesses and individuals across Gurgaon. By booking staff through our app, website or WhatsApp, you agree to them.',
    sections: [
      { h: '1. Who we are', p: 'Switch ("Switch", "we", "us") is a staffing platform operating in Gurgaon, Haryana. We connect businesses and individuals ("you", "the customer") with verified workers ("Switch Players") for shifts ranging from a few hours to multi-day blocks.' },
      { h: '2. Bookings', p: 'A booking is confirmed once we acknowledge it in the app, on WhatsApp or by phone. You are responsible for giving accurate details — role, number of Switch Players, location, timing and any site-specific requirements — so we can match the right people.' },
      { h: '3. Verification', p: 'Every Switch Player is Aadhaar-verified, document-checked and interviewed before being approved on the platform. On arrival, OTP verification confirms the assigned person reached your site. You should not ask a Switch Player to work under a different identity or off-platform.' },
      { h: '4. Payment', p: 'No advance is required — you pay on arrival or on completion, as agreed for your booking. Accepted methods include UPI, cards and bank transfer. Rates depend on role and booking length and are confirmed before the shift. GST and invoices are available for business accounts on request.' },
      { h: '5. Replacement guarantee', p: 'If a Switch Player does not show up or is not the right fit, tell us promptly and we will dispatch a replacement — usually within 24 hours. The guarantee applies when the issue is raised during or immediately after the shift, not retroactively for completed work you accepted.' },
      { h: '6. Your responsibilities', p: 'You agree to provide a safe working environment, lawful working conditions and any required safety equipment, and to treat Switch Players with respect. You must not engage a Switch Player directly outside the platform for the duration of, and 90 days after, an assignment introduced by Switch.' },
      { h: '7. Liability', p: 'Switch facilitates staffing and screens Switch Players in good faith, but does not accept liability for indirect or consequential losses. Our total liability for any booking is limited to the fees paid for that booking.' },
      { h: '8. Changes', p: 'We may update these terms from time to time. The current version always lives on this page, with the "last updated" date below.' },
    ],
  },
  privacy: {
    slug: 'privacy',
    title: 'Privacy Policy',
    intro: 'This policy explains what information Switch collects, why, and how we handle it when you use our app, website or WhatsApp to hire staff.',
    sections: [
      { h: '1. Information we collect', p: 'Contact and business details you provide (name, phone number, business name, service address), booking details (roles, quantities, timing), and payment references. When you message us on WhatsApp, we receive the phone number and message content you send.' },
      { h: '2. How we use it', p: 'To match you with the right Switch Players, confirm and coordinate bookings, process payments, provide support, send booking-related updates, and improve our service. We do not sell your personal data.' },
      { h: '3. Sharing', p: 'We share only what is necessary to fulfil a booking — for example, a service address and contact number with the assigned Switch Player, and payment references with our payment providers. We may disclose information where required by law.' },
      { h: '4. Retention', p: 'We keep booking and account records for as long as needed to provide the service, meet tax and legal obligations, and resolve disputes. You can ask us to delete data we are not required to retain.' },
      { h: '5. Security', p: 'We apply reasonable technical and organisational measures to protect your information. No system is perfectly secure, but we work to keep your data safe and limit access to those who need it.' },
      { h: '6. Your rights', p: `You can ask to access, correct or delete your personal information, or opt out of non-essential messages, by contacting us at ${CONTACT_EMAIL}.` },
      { h: '7. Cookies', p: 'Our website uses minimal cookies and similar technologies to keep the site working and understand aggregate usage. You can control cookies through your browser settings.' },
    ],
  },
  cancellation: {
    slug: 'cancellation',
    title: 'Cancellation & Refund Policy',
    intro: 'We know business needs change. This policy explains how to cancel or reschedule a booking and how refunds work.',
    sections: [
      { h: '1. Cancelling a booking', p: 'You can cancel through the app or by messaging us on WhatsApp. Because there is no advance payment on most bookings, cancelling before a Switch Player is dispatched costs you nothing.' },
      { h: '2. Late cancellations', p: 'If you cancel after a Switch Player has already started travelling to your site, or once a shift has begun, a partial charge may apply to cover the time and travel committed. We will always tell you the amount before charging.' },
      { h: '3. Rescheduling', p: 'Need a different day or time? Let us know as early as you can and we will do our best to move the booking at no extra cost, subject to availability.' },
      { h: '4. Replacement instead of refund', p: 'If a Switch Player is a no-show or not the right fit, our first remedy is a fast replacement — usually within 24 hours — so your business stays covered. Raise the issue during or right after the shift.' },
      { h: '5. Refunds', p: 'Where a refund is due — for example, a shift we could not staff after taking payment — we process it to the original payment method, typically within 5–7 business days.' },
      { h: '6. Questions', p: `For anything to do with a cancellation, reschedule or refund, contact us at ${CONTACT_EMAIL} or ${PHONE_DISPLAY}.` },
    ],
  },
}

export default function LegalPage({ policy }) {
  const data = POLICIES[policy]
  useEffect(() => { window.scrollTo(0, 0) }, [policy])
  if (!data) return null
  const url = `https://switchlocally.com/${data.slug}`
  return (
    <>
      <Helmet>
        <title>{data.title} | Switch</title>
        <meta name="description" content={data.intro} />
        <link rel="canonical" href={url} />
        <meta property="og:title" content={`${data.title} | Switch`} />
        <meta property="og:description" content={data.intro} />
        <meta property="og:url" content={url} />
      </Helmet>
      <Nav />
      <main className="legal">
        <div className="legal-wrap">
          <p className="legal-eyebrow">Legal</p>
          <h1 className="legal-title">{data.title}</h1>
          <p className="legal-intro">{data.intro}</p>
          {data.sections.map((s, i) => (
            <section className="legal-sec" key={i}>
              <h2 className="legal-h">{s.h}</h2>
              <p className="legal-p">{s.p}</p>
            </section>
          ))}
          <p className="legal-updated">
            Last updated: {LAST_UPDATED}. Questions? Email{' '}
            <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
          </p>
        </div>
      </main>
      <Footer />
    </>
  )
}
