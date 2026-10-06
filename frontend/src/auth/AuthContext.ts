import { createContext, useContext } from 'react'
import type { AuthenticatedUser } from './types'
import type { UserSettingData } from '../api/userSettings'

export type AuthState =
  | { status: 'loading' }
  | { status: 'authenticated'; user: AuthenticatedUser }
  | { status: 'unauthenticated' }
  | { status: 'error'; error: Error }

export type AuthContextValue = AuthState & {
  refresh: () => Promise<void>
  markUnauthenticated: () => void
  changeTheme: (theme: 'light' | 'dark') => Promise<UserSettingData>
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function useAuth() {
  const state = useContext(AuthContext)
  if (!state) throw new Error('useAuth must be used within AuthProvider')
  return state
}
