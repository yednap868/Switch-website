/* The Switch employer app, drawn in HTML: three screens of the current app
   (home, the 3-hour trial payment page, and a confirmed shift with its OTP).
   Built as markup rather than screenshots so they stay sharp at any size and
   match the app's real look. Each screen is laid out at 280×606 and scaled
   by the device size. Styles: .sw-dev-* in src/styles/switch.css. */
import Icon from './Icon.jsx'

function StatusBar() {
  return (
    <div className="sd-status" aria-hidden="true">
      <b>9:41</b>
      <span className="sd-island" />
      <span className="sd-sig">
        <i />
        <i />
        <i />
        <em />
      </span>
    </div>
  )
}

function HomeScreen() {
  return (
    <div className="sd-screen">
      <StatusBar />
      <div className="sd-top">
        <div>
          <img src="/brand/switch-wordmark-white.png" alt="" className="sd-wm" />
          <span className="sd-loc">
            <Icon name="pin" /> DLF Phase 3
          </span>
        </div>
        <span className="sd-wallet">₹1,240</span>
      </div>
      <p className="sd-eyebrow">BUSINESS STAFFING</p>
      <p className="sd-h">
        Switch <b>to</b> the right <b>staff.</b>
      </p>
      <div className="sd-seg">
        <span className="on">
          <Icon name="sparkles" /> Instant
        </span>
        <span>Scheduled</span>
        <span>Monthly</span>
      </div>
      <div className="sd-tiles">
        <span className="t-lav">
          <Icon name="sparkles" />
          Cleaning
        </span>
        <span className="t-peach">
          <Icon name="chef" />
          Kitchen
        </span>
        <span className="t-sky">
          <Icon name="shield" />
          Security
        </span>
        <span className="t-mint">
          <Icon name="package" />
          Helper
        </span>
      </div>
      <div className="sd-trial">
        <div>
          <span className="sd-eyebrow" style={{ color: 'rgba(255,255,255,.7)' }}>
            3-HOUR TRIAL
          </span>
          <p className="sd-trial-h">
            Switch &amp; try
            <br />
            from <b>₹149</b>
          </p>
          <span className="sd-timer">
            <Icon name="timer" /> Ends in 07:12:40
          </span>
          <span className="sd-white">Switch now →</span>
        </div>
        <div className="sd-trial-art">
          <span className="sd-blob" />
          <img src="/sw-maid.jpg" alt="" />
        </div>
      </div>
      <div className="sd-nav">
        <span className="on">
          <Icon name="building" />
        </span>
        <span>
          <Icon name="cal" />
        </span>
        <span className="sd-sw">
          <Icon name="sparkles" />
        </span>
        <span>
          <Icon name="wallet" />
        </span>
        <span>
          <Icon name="heart" />
        </span>
      </div>
    </div>
  )
}

function TrialPayScreen() {
  return (
    <div className="sd-screen">
      <StatusBar />
      <div className="sd-bar">
        <span className="sd-back">←</span>
        <b>Pay for your trial</b>
      </div>
      <div className="sd-hero">
        <img src="/sw-maid.jpg" alt="" />
        <div>
          <span className="sd-eyebrow" style={{ color: 'rgba(255,255,255,.7)' }}>
            3-HOUR TRIAL
          </span>
          <b className="sd-role">Housekeeping</b>
          <span className="sd-price">
            ₹149 <small>· 1 worker · 3 hrs</small>
          </span>
        </div>
      </div>
      <div className="sd-card">
        <div className="sd-row">
          <b>When</b>
          <small className="sd-ok">11:00 AM – 2:00 PM</small>
        </div>
        <div className="sd-chips">
          <span className="on">Today</span>
          <span>Tomorrow</span>
          <span>Wed 30</span>
        </div>
        <div className="sd-chips">
          <span>10:30</span>
          <span className="on p">11:00</span>
          <span>11:30</span>
          <span>12:00</span>
        </div>
      </div>
      <div className="sd-card sd-addr">
        <span className="sd-sq">
          <Icon name="pin" />
        </span>
        <div>
          <b>Café · DLF Phase 3</b>
          <small>Shop 12, Cyber Hub, Gurgaon</small>
        </div>
      </div>
      <div className="sd-bill">
        <div>
          <span>Housekeeping · 3 hrs</span>
          <b>₹149</b>
        </div>
        <div className="sd-total">
          <span>To pay</span>
          <b>₹149</b>
        </div>
      </div>
      <div className="sd-pay">
        <span>
          <Icon name="sparkles" /> Pay ₹149 →
        </span>
        <small>Today, 11:00 AM · UPI or card</small>
      </div>
    </div>
  )
}

function ShiftScreen() {
  return (
    <div className="sd-screen">
      <StatusBar />
      <div className="sd-bar">
        <span className="sd-back">←</span>
        <b>Your shift</b>
      </div>
      <div className="sd-confirm">
        <span className="sd-check">
          <Icon name="check" />
        </span>
        <b>Shift confirmed</b>
        <small>Security Guard · Today, 8:00 PM</small>
      </div>
      <div className="sd-card sd-worker">
        <img src="/sw-security-guard.jpg" alt="" />
        <div>
          <b>Ramesh K.</b>
          <small>Aadhaar verified · 4.8 ★</small>
          <span className="sd-live">On the way · 12 min</span>
        </div>
      </div>
      <div className="sd-card sd-otp">
        <small>Share this code with the worker</small>
        <div className="sd-otp-code">
          {['4', '7', '1', '9'].map((d) => (
            <span key={d}>{d}</span>
          ))}
        </div>
      </div>
      <div className="sd-steps">
        {[
          ['Booked', true],
          ['Worker assigned', true],
          ['On the way', true],
          ['Checked in with OTP', false],
        ].map(([t, done]) => (
          <span key={t} className={done ? 'done' : ''}>
            <i />
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}

function Device({ size, children, label }) {
  return (
    <div className={`sw-dev ${size}`} role="img" aria-label={label}>
      <div className="sw-dev-in">{children}</div>
    </div>
  )
}

export default function AppScreens() {
  return (
    <div className="sw-devs">
      <Device size="side" label="Switch app: pay ₹149 for a 3-hour Housekeeping trial">
        <TrialPayScreen />
      </Device>
      <Device
        size="mid"
        label="Switch app home: hire instantly, scheduled or monthly, trial from ₹149"
      >
        <HomeScreen />
      </Device>
      <Device size="side" label="Switch app: shift confirmed, worker on the way, OTP 4719">
        <ShiftScreen />
      </Device>
    </div>
  )
}
