/* Bottom-corner status strip. Pair it with useToast(). */

export default function Toast({ message }) {
  return (
    <div className={`toast${message ? ' show' : ''}`} role="status" aria-live="polite">
      {message}
    </div>
  )
}
