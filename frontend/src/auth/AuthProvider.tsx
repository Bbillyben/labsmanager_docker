import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { subscribeToUnauthorized } from '../api/client'
import { getCurrentUser } from './authApi'
import { AuthContext, type AuthState } from './AuthContext'
import { updateUserSetting } from '../api/userSettings'
import { ApiError } from '../api/errors'

function applyTheme(theme: 'light' | 'dark') {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })

  const refresh = useCallback(async () => {
    const user = await getCurrentUser()
    applyTheme(user.is_authenticated ? user.theme : 'light')
    setState(user.is_authenticated ? { status: 'authenticated', user } : { status: 'unauthenticated' })
  }, [])

  const markUnauthenticated = useCallback(() => { applyTheme('light'); setState({ status: 'unauthenticated' }) }, [])

  const changeTheme = useCallback(async (theme: 'light' | 'dark') => {
    const previous = state.status === 'authenticated' ? state.user.theme : 'light'
    setState((current) => current.status === 'authenticated' ? { ...current, user: { ...current.user, theme } } : current)
    applyTheme(theme)
    try {
      const saved = await updateUserSetting('interface', 'LAB_THEME', theme)
      return saved
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        applyTheme('light')
        throw error
      }
      applyTheme(previous)
      setState((current) => current.status === 'authenticated' ? { ...current, user: { ...current.user, theme: previous } } : current)
      throw error
    }
  }, [state])

  useEffect(() => {
    const controller = new AbortController()
    const unsubscribe = subscribeToUnauthorized(markUnauthenticated)
    getCurrentUser(controller.signal)
      .then((user) => { applyTheme(user.is_authenticated ? user.theme : 'light'); setState(user.is_authenticated ? { status: 'authenticated', user } : { status: 'unauthenticated' }) })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setState({ status: 'error', error: error instanceof Error ? error : new Error('Unknown error') })
      })

    return () => { controller.abort(); unsubscribe() }
  }, [markUnauthenticated])

  const value = useMemo(() => ({ ...state, refresh, markUnauthenticated, changeTheme }), [changeTheme, markUnauthenticated, refresh, state])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
