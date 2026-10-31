import { useEffect, useState } from 'react'

/* A different check-in code on every visit, as a real booking would have. The
   server HTML keeps one fixed code so it hydrates cleanly, then this swaps it. */
export default function useFreshOtp() {
  const [otp, setOtp] = useState('4719')
  useEffect(() => {
    const t = setTimeout(() => setOtp(String(1000 + Math.floor(Math.random() * 9000))), 0)
    return () => clearTimeout(t)
  }, [])
  return otp
}
