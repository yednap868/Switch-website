import { useState } from 'react'

/* Mono eyebrow whose letters lift one after another on hover — each letter
   carries its index as --i, which the CSS turns into a transition-delay. */

export default function CascadeLabel({ text, className = '' }) {
  const [running, setRunning] = useState(false)

  return (
    <div
      className={`eyebrow cascade-label${running ? ' cascade-run' : ''} ${className}`.trim()}
      data-cascade={text}
      onPointerEnter={() => setRunning(true)}
      onPointerLeave={() => setRunning(false)}
    >
      {[...text].map((char, i) => (
        <span key={`${char}-${i}`} style={{ '--i': i }}>
          {char === ' ' ? ' ' : char}
        </span>
      ))}
    </div>
  )
}
