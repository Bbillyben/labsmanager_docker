import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { subscribeToUnauthorized } from '../api/client'
import { getCurrentUser } from './authApi'
import { AuthContext, type AuthState } from './AuthContext'

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })

  const refresh = useCallback(async () => {
    const user = await getCurrentUser()
    setState(user.is_authenticated ? { status: 'authenticated', user } : { status: 'unauthenticated' })
  }, [])

  const markUnauthenticated = useCallback(() => setState({ status: 'unauthenticated' }), [])

  useEffect(() => {
    const controller = new AbortController()
    const unsubscribe = subscribeToUnauthorized(markUnauthenticated)
    getCurrentUser(controller.signal)
      .then((user) => setState(user.is_authenticated ? { status: 'authenticated', user } : { status: 'unauthenticated' }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({ status: 'error', error: error instanceof Error ? error : new Error('Unknown error') })
      })

    return () => { controller.abort(); unsubscribe() }
  }, [markUnauthenticated])

  const value = useMemo(() => ({ ...state, refresh, markUnauthenticated }), [markUnauthenticated, refresh, state])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
