/* /work — the worker side of Switch, Hindi-first, in the same look as the
   homepage. Facts from the new-app brief: tell Jyoti you're free, she marks
   you available, jobs ring like a ride app, 100% of the fare is yours, paid
   by the employer directly; full-time jobs with salary/food/stay. */
import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import Icon from '../ui/Icon.jsx'
import WorkerChat from './WorkerChat.jsx'
import { SxFooter, SxHeader } from './SxChrome.jsx'
import { LANG_LINES, WORKER_APP_URL } from '../../data/switchHome.js'
import { PHONE, waLink } from '../../data/site.js'
import './sx.css'

const STEPS = [
  { n: '01', t: 'Jyoti को बोलिए', d: '“आज फ्री हूँ, काम चाहिए” — बोलकर या लिखकर। हिंदी, Hinglish, English या తెలుగు।' },
  { n: '02', t: 'Available हो जाइए', d: 'Jyoti पूछेगी आप कौन सा काम करते हैं, कब तक फ्री हैं और कितनी दूर जा सकते हैं।' },
  { n: '03', t: 'फ़ोन बजेगा', d: 'पास में नया काम आते ही ride app की तरह फ़ोन बजेगा। एक टैप में Accept।' },
  { n: '04', t: 'काम कीजिए, पैसा सीधे आपको', d: 'पहुँचकर OTP से काम शुरू। काम के बाद मालिक पूरा किराया सीधे आपको देंगे — cash या UPI।' },
]

const PERKS = [
  { i: 'wallet', t: 'पूरा 100% किराया आपका', d: 'Switch आपके किराए में से कुछ नहीं काटता। मालिक काम के बाद सीधे आपको देंगे।' },
  { i: 'pin', t: 'घर के पास काम', d: 'जितनी दूर आप जाना चाहें, उतनी दूर तक का ही काम।' },
  { i: 'timer', t: 'अपने समय पर', d: 'जब फ्री हों तब बताइए। आज 2 घंटे या पूरा दिन — आपकी मर्ज़ी।' },
  { i: 'building', t: 'Full-time नौकरी भी', d: 'Salary, खाना और रहने की सुविधा वाली नौकरियाँ। Interview Jyoti बुक करेगी।' },
  { i: 'shield', t: 'OTP से काम शुरू', d: 'पहुँचकर OTP से काम शुरू, timer चलता है — सब साफ़-साफ़।' },
  { i: 'star', t: 'Rating से आगे बढ़िए', d: 'अच्छे काम पर अच्छी rating — और ज़्यादा काम।' },
]

const ROLES_HI = ['कुक', 'किचन हेल्पर', 'हाउसकीपिंग', 'वेटर', 'यूटिलिटी स्टाफ़', 'पिकर-पैकर']

const FAQS = [
  { q: 'क्या Switch मेरे किराए में से पैसे काटता है?', a: 'नहीं। पूरा 100% किराया आपका है। काम के बाद मालिक सीधे आपको देंगे — cash या UPI/QR।' },
  { q: 'पैसा कब और कैसे मिलेगा?', a: 'काम पूरा होने के बाद, मालिक से सीधे — cash या UPI/QR से।' },
  { q: 'कौन से काम मिलते हैं?', a: 'कुक, किचन हेल्पर, हाउसकीपिंग, वेटर, यूटिलिटी स्टाफ़ और पिकर-पैकर — गुरुग्राम की दुकानों, रेस्टोरेंट, PG, होटल और घरों में।' },
  { q: 'कितनी दूर का काम मिलेगा?', a: 'जितनी दूर आप Jyoti को बताएँगे — 2 km, 5 km या ज़्यादा। उससे दूर का काम नहीं भेजा जाएगा।' },
  { q: 'Full-time नौकरी कैसे मिलेगी?', a: 'Jyoti को बताइए कि आप full-time काम चाहते हैं। Salary, खाना और रहने वाली नौकरियाँ दिखेंगी, और interview Jyoti बुक करेगी।' },
  { q: 'किस भाषा में बात कर सकते हैं?', a: 'हिंदी, Hinglish, English या తెలుగు — जिस भाषा में आप बोलेंगे, app उसी में बात करेगा।' },
]

export default function WorkerPage() {
  return (
    <div className="sx" lang="hi">
      <Helmet>
        <title>काम चाहिए? Find Work in Gurugram — Just Tell Jyoti | Switch</title>
        <meta
          name="description"
          content="आज फ्री हो? Jyoti को बोलो — गुरुग्राम में पास का काम: कुक, किचन हेल्पर, हाउसकीपिंग, वेटर, यूटिलिटी, पिकर-पैकर। नया काम आते ही फ़ोन बजेगा, एक टैप में accept। पूरा किराया आपका।"
        />
        <link rel="canonical" href="https://switchlocally.com/work" />
        <meta property="og:title" content="काम चाहिए? Jyoti को बोलो | Switch" />
        <meta property="og:description" content="गुरुग्राम में पास का काम — फ़ोन बजेगा, एक टैप में accept, पूरा किराया आपका।" />
        <meta property="og:url" content="https://switchlocally.com/work" />
        <meta property="og:image" content="https://switchlocally.com/og-switch.png" />
      </Helmet>
      <a className="skip-link" href="#sx-main">
        Skip to main content
      </a>
      <SxHeader
        links={[
          ['#kaise', 'कैसे काम करता है'],
          ['#fayde', 'फ़ायदे'],
          ['#faq', 'सवाल'],
          ['/', 'Staff चाहिए?'],
        ]}
        cta={{ href: WORKER_APP_URL, label: 'Download app' }}
      />
      <main id="sx-main">
        <section className="sx-hero" id="top">
          <div className="sx-wrap sx-hero-in">
            <div className="sx-hero-copy">
              <p className="sx-kicker">
                <span className="sx-live-dot" aria-hidden="true" /> गुरुग्राम · काम ढूँढने वालों के लिए
              </p>
              <h1 className="sx-h1 deva">
                आज फ्री हो? काम मिलेगा<span className="sx-dot">।</span>
              </h1>
              <p className="sx-lead">
                Jyoti को बोलिए “आज फ्री हूँ, काम चाहिए”। वो आपके पास का काम ढूँढेगी, और नया काम आते ही आपका फ़ोन
                बजेगा। पूरा किराया आपका।
              </p>
              <div className="sx-btns" lang="en">
                <a className="sx-btn" href={WORKER_APP_URL} target="_blank" rel="noreferrer">
                  Download app <Icon name="arrow" />
                </a>
                <a className="sx-btn ghost" href="#kaise">
                  कैसे काम करता है
                </a>
              </div>
              <ul className="sx-hero-facts">
                <li>
                  <b>100%</b> किराया आपका
                </li>
                <li>
                  <b>1 टैप</b> में accept
                </li>
                <li>
                  <b>पास का</b> काम
                </li>
              </ul>
            </div>
            <div className="sx-hero-phone">
              <WorkerChat />
              <p className="sx-cap">छूकर देखिए — Switch app की झलक।</p>
            </div>
          </div>
        </section>

        <section className="sx-sec" id="kaise" aria-labelledby="w-how">
          <div className="sx-wrap">
            <p className="sx-eyebrow">कैसे काम करता है</p>
            <h2 id="w-how" className="sx-h2 deva">
              चार कदम। बस बोलना है<span className="sx-dot">।</span>
            </h2>
            <ol className="sx-steps">
              {STEPS.map((s) => (
                <li key={s.n} className="sx-card">
                  <span className="sx-n">{s.n}</span>
                  <h3>{s.t}</h3>
                  <p>{s.d}</p>
                </li>
              ))}
            </ol>
            <div className="sx-rolechips" aria-label="काम">
              {ROLES_HI.map((r) => (
                <span key={r}>{r}</span>
              ))}
            </div>
          </div>
        </section>

        <section className="sx-sec sx-net" id="fayde" aria-labelledby="w-perks">
          <div className="sx-wrap">
            <p className="sx-eyebrow">फ़ायदे</p>
            <h2 id="w-perks" className="sx-h2 deva">
              आपकी मेहनत, आपका पैसा<span className="sx-dot">।</span>
            </h2>
            <div className="sx-trust">
              {PERKS.map((x) => (
                <div key={x.t} className="sx-card sx-trust-i">
                  <span className="sx-ti" aria-hidden="true">
                    <Icon name={x.i} />
                  </span>
                  <h3>{x.t}</h3>
                  <p>{x.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="sx-langs" aria-labelledby="w-langs">
          <div className="sx-wrap">
            <h2 id="w-langs" className="sx-langs-h">
              <span>हिंदी</span> · <span lang="en">Hinglish</span> · <span lang="en">English</span> ·{' '}
              <span lang="te">తెలుగు</span>
            </h2>
            <p className="sx-langs-sub">कोई language चुनने की ज़रूरत नहीं — जिस भाषा में बोलेंगे, Jyoti उसी में जवाब देगी।</p>
          </div>
          <div className="sx-marquee" aria-hidden="true">
            <div className="sx-track">
              {[...LANG_LINES, ...LANG_LINES].map((x, i) => (
                <span key={i} className={`sx-chip l-${x.l}`}>
                  {x.t}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="sx-sec" id="faq" aria-labelledby="w-faq">
          <div className="sx-wrap sx-faq-in">
            <div>
              <p className="sx-eyebrow">सवाल-जवाब</p>
              <h2 id="w-faq" className="sx-h2 deva">
                आपके सवाल<span className="sx-dot">।</span>
              </h2>
              <p className="sx-lead">
                और कुछ पूछना है?{' '}
                <a className="sx-link" href={waLink('Namaste Switch — mujhe kaam chahiye.')} target="_blank" rel="noreferrer">
                  WhatsApp कीजिए
                </a>{' '}
                या कॉल करें <a className="sx-link" href={`tel:${PHONE}`}>87968 94500</a>।
              </p>
            </div>
            <div className="sx-faq">
              {FAQS.map((f) => (
                <details key={f.q}>
                  <summary>
                    {f.q}
                    <span aria-hidden="true" />
                  </summary>
                  <p>{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>
      <SxFooter
        title={
          <>
            आज फ्री हो? Jyoti को बोलो<span className="sx-dot">।</span>
          </>
        }
        primary={
          <a className="sx-btn" href={WORKER_APP_URL} target="_blank" rel="noreferrer" lang="en">
            Download app <Icon name="arrow" />
          </a>
        }
        secondary={
          <Link className="sx-btn ghost" to="/">
            Staff चाहिए?
          </Link>
        }
      />
    </div>
  )
}
