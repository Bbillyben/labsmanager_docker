import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { useAuth } from './AuthContext'

export function RequireAuth() {
  const auth = useAuth()
  const location = useLocation()
  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message="Chargement de la session…" /></main>
  if (auth.status === 'error') return <ErrorState />
  if (auth.status === 'unauthenticated') {
    const from = `${location.pathname}${location.search}${location.hash}`
    return <Navigate replace state={{ from }} to="/login" />
  }
  return <Outlet />
}
