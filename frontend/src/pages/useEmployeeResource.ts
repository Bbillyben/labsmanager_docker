import { useCallback, useEffect, useRef, useState } from 'react'

export type EmployeeResource<T> = {
  data: T | null; error: unknown; loading: boolean; retry: () => void
  refreshing: boolean; refreshError: unknown; refresh: () => Promise<boolean>
  updateData: (update: (data: T) => T) => void
}
export type EmployeeLoader<T> = (id: string, signal: AbortSignal) => Promise<T>

export function useEmployeeResource<T>(id: string, loader: EmployeeLoader<T>, enabled = true): EmployeeResource<T> {
  const [attempt, setAttempt] = useState(0)
  const key = `${id}:${attempt}`
  const [state, setState] = useState<{ key: string; data: T | null; error: unknown; refreshing: boolean; refreshError: unknown }>({ key, data: null, error: null, refreshing: false, refreshError: null })
  const request = useRef<AbortController | null>(null)

  const read = useCallback(async (retain: boolean) => {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    try {
      const data = await loader(id, controller.signal)
      if (controller.signal.aborted) return false
      setState({ key, data, error: null, refreshing: false, refreshError: null })
      return true
    } catch (error) {
      if (controller.signal.aborted) return false
      setState((previous) => retain && previous.key === key && previous.data !== null
        ? { ...previous, refreshing: false, refreshError: error }
        : { key, data: null, error, refreshing: false, refreshError: null })
      return false
    }
  }, [id, key, loader])

  useEffect(() => {
    if (!enabled) return
    void read(false)
    return () => request.current?.abort()
  }, [enabled, read])

  const refresh = useCallback(() => {
    setState((previous) => previous.key === key ? { ...previous, refreshing: true, refreshError: null } : previous)
    return read(true)
  }, [key, read])
  const updateData = useCallback((update: (data: T) => T) => {
    // A read started before a write must never overwrite its server response.
    request.current?.abort()
    setState((previous) => previous.key === key && previous.data !== null
      ? { ...previous, data: update(previous.data), refreshing: false, refreshError: null } : previous)
  }, [key])
  const current = state.key === key ? state : { data: null, error: null, refreshing: false, refreshError: null }
  return { ...current, loading: enabled && current.data === null && !current.error, retry: () => setAttempt((value) => value + 1), refresh, updateData }
}
