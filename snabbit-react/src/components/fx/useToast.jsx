import { useCallback, useEffect, useRef, useState } from 'react'
import Toast from './Toast.jsx'

/* Returns [toastElement, show]. Render the element anywhere in the tree and
   call show('…') to flash a message. */
export default function useToast(duration = 3500) {
  const [message, setMessage] = useState('')
  const timer = useRef(0)

  const show = useCallback(
    (text) => {
      setMessage(text)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setMessage(''), duration)
    },
    [duration],
  )

  useEffect(() => () => window.clearTimeout(timer.current), [])

  return [<Toast key="toast" message={message} />, show]
}
