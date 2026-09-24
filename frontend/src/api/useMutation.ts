import { useCallback, useEffect, useRef, useState } from 'react'

/** Serialize submissions. A successful write is independent of later reads. */
export function useMutation() {
  const busy = useRef(false)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const run = useCallback(async <T,>(write: () => Promise<T>): Promise<{ data: T } | undefined> => {
    if (busy.current || !mounted.current) return undefined
    busy.current = true
    setPending(true)
    setError(null)
    try {
      const data = await write()
      // Navigation does not undo a write; its old form must not refresh another context.
      return mounted.current ? { data } : undefined
    } catch (reason) {
      if (mounted.current) setError(reason)
      return undefined
    } finally {
      busy.current = false
      if (mounted.current) setPending(false)
    }
  }, [])
  return { pending, error, run }
}
