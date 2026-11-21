/* "What will one shift cost?" — for one worker: you pick hours and the
   hourly rate you'd set; it splits the total into what goes to the worker
   (directly, after the work) and Switch's ₹99 booking fee. The rate here is
   an example the visitor chooses, not a Switch price. */
import { useState } from 'react'

const fmt = (n) => '₹' + Math.round(n).toLocaleString('en-IN')

export default function CostCalc() {
  const [hours, setHours] = useState(4)
  const [rate, setRate] = useState(150)
  const fare = hours * rate
  const total = fare + 99
  const workerPct = Math.round((fare / total) * 100)
  return (
    <div className="cc sx-card">
      <div className="cc-head">
        <b>What one shift costs</b>
        <small>Example for 1 worker — you choose the rate</small>
      </div>
      <label className="cc-row">
        <span>
          Hours <b>{hours}</b>
        </span>
        <input type="range" min="2" max="12" step="1" value={hours} onChange={(e) => setHours(+e.target.value)} />
      </label>
      <label className="cc-row">
        <span>
          Your hourly rate <b>{fmt(rate)}</b>
        </span>
        <input type="range" min="100" max="400" step="10" value={rate} onChange={(e) => setRate(+e.target.value)} />
      </label>
      <div className="cc-bar" aria-hidden="true">
        <span className="w" style={{ width: `${workerPct}%` }} />
        <span className="s" />
      </div>
      <dl className="cc-out">
        <div>
          <dt>
            <i className="w" /> To the worker, directly
          </dt>
          <dd>{fmt(fare)}</dd>
        </div>
        <div>
          <dt>
            <i className="s" /> Switch booking fee
          </dt>
          <dd>₹99</dd>
        </div>
        <div className="tot">
          <dt>Total for this shift</dt>
          <dd>{fmt(total)}</dd>
        </div>
      </dl>
      <p className="cc-note">
        {workerPct}% goes to the worker. Each role has a fixed minimum rate — the app shows it when you book.
      </p>
    </div>
  )
}
