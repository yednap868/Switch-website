import { APPLE_URL, PLAY_URL } from '../../data/site.js'

const BENEFITS = [
  {
    n: '01',
    title: 'Find verified people',
    copy: 'Profiles, roles and availability in one place.',
  },
  { n: '02', title: 'Book in minutes', copy: 'Share your shift details without a call.' },
  { n: '03', title: 'Stay in control', copy: 'Track bookings and support from the app.' },
]

export default function AppSection() {
  return (
    <section className="dark-section app-section" id="app-section">
      <div className="shell app-story">
        <div className="app-story-copy">
          <div className="eyebrow">07 / THE SWITCH APP</div>
          <h2>Staffing, without the back-and-forth.</h2>
          <p>
            Browse verified staff, book in a few taps and keep the day moving. The Switch app is
            built for the moments you need help now.
          </p>
          <div className="app-benefits">
            {BENEFITS.map((b) => (
              <span key={b.n}>
                <b>{b.n}</b>
                <strong>{b.title}</strong>
                <small>{b.copy}</small>
              </span>
            ))}
          </div>
          <div className="hero-actions app-actions">
            <a className="btn primary" href={PLAY_URL} target="_blank" rel="noreferrer">
              Google Play ↗
            </a>
            <a className="btn ghost" href={APPLE_URL} target="_blank" rel="noreferrer">
              App Store ↗
            </a>
          </div>
          <span className="app-download-note">Free to download · Built for busy teams</span>
        </div>

        <div className="phones" aria-label="Preview of the Switch employer app">
          <div className="phone-orbit phone-orbit-one" />
          <div className="phone-orbit phone-orbit-two" />
          <span className="app-stage-label mono">EMPLOYER APP / LIVE</span>
          <span className="app-stage-status">
            <i /> Ready to book
          </span>
          <img src="/screen-home.png" alt="Switch app home screen" loading="lazy" />
          <img src="/screen-2.png" alt="Switch app booking screen" loading="lazy" />
          <img className="phone-back" src="/screen-3.png" alt="Switch app staff screen" loading="lazy" />
          <span className="app-stage-caption">
            One clear view
            <br />
            <em>of every shift.</em>
          </span>
        </div>
      </div>
    </section>
  )
}
