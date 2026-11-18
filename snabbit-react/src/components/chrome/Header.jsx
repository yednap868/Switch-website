/* Site header for every inner page — the same Switch header as the homepage
   (components/sx/SxChrome), so the whole site reads as one product. */
import { SxHeader } from '../sx/SxChrome.jsx'
import '../sx/sx.css'

const LINKS = [
  ['/#how', 'How it works'],
  ['/#pricing', 'Pricing'],
  ['/staffing-gurgaon', 'Services'],
  ['/work', 'Find work'],
]

export default function Header() {
  return <SxHeader className="sx-tok" links={LINKS} />
}
