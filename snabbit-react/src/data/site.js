/* Single source of truth for the contact + store links that used to be
   re-declared at the top of App.jsx and each page file. */

export const APP_URL = 'https://app.switchlocally.com'
export const EMPLOYER_LOGIN = 'https://app.switchlocally.com/employer/login'
export const PLAY_URL = 'https://play.google.com/store/apps/details?id=com.switchlocally.employer'
export const APPLE_URL = 'https://apps.apple.com/in/app/switch-hire-verified-staff/id6798368902'

export const PHONE = '+919205617375'
export const PHONE_DISPLAY = '+91 92056 17375'
export const CALL_URL = `tel:${PHONE}`
export const EMAIL = 'hello@switchlocally.com'
export const CAREERS_EMAIL = 'careers@switchlocally.com'

export const waLink = (msg) =>
  `https://wa.me/${PHONE.replace('+', '')}${msg ? `?text=${encodeURIComponent(msg)}` : ''}`

export const WHATSAPP_URL = waLink("Hi Switch — I'd like to hire staff for my business in Gurgaon.")

export const MAPS_URL =
  'https://www.google.com/maps/search/?api=1&query=WeWork%20Cyber%20Hub%20Gurgaon'

export const SOCIALS = [
  { label: 'in', href: 'https://www.linkedin.com/company/switchlocal', name: 'LinkedIn' },
  { label: 'ig', href: 'https://www.instagram.com/switchlocally/', name: 'Instagram' },
  { label: 'fb', href: 'https://www.facebook.com/switchlocally', name: 'Facebook' },
]

export const ADDRESS = ['5th Floor, WeWork, Cyber Hub', 'Gurgaon, Haryana 122002']

export const REGISTERED_OFFICE =
  'Registered office: Shop No R-02/06, Tower A3, M3M Woodshire, Sector 107, Gurugram – 122006, Haryana, India'
