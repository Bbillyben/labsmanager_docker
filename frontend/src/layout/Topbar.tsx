import { ExternalLink, LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { logout } from '../auth/authApi'
import { useAuth } from '../auth/AuthContext'
import type { AuthenticatedUser } from '../auth/types'
import { getDjangoUrl } from '../config/django'
import { ThemeToggle } from '../ui/ThemeToggle'
import { IconButton } from '../ui/IconButton'
import styles from './Topbar.module.css'

type TopbarProps = { navigationExpanded: boolean; onToggleNavigation: () => void; user: AuthenticatedUser }

export function Topbar({ navigationExpanded, onToggleNavigation, user }: TopbarProps) {
  const auth = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState(false)
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username
  const ToggleIcon = navigationExpanded ? PanelLeftClose : PanelLeftOpen

  async function handleLogout() {
    setLoggingOut(true)
    setLogoutError(false)
    try {
      await logout()
      auth.markUnauthenticated()
      navigate('/login', { replace: true })
    } catch {
      setLogoutError(true)
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <header className={styles.topbar}>
      <div className={styles.leading}>
        <IconButton aria-controls="primary-navigation" aria-expanded={navigationExpanded} label={navigationExpanded ? 'Réduire la navigation' : 'Ouvrir la navigation'} onClick={onToggleNavigation}>
          <ToggleIcon aria-hidden="true" size={20} strokeWidth={1.8} />
        </IconButton>
        <span className={styles.context}>Espace de travail</span>
      </div>
      <div className={styles.account}>
        {logoutError && <span className={styles.logoutError} role="alert">Déconnexion impossible.</span>}
        <span className={styles.identity} title={user.username}>{displayName}</span>
        <a className={styles.historicalLink} href={getDjangoUrl('/')}>
          <span>Interface historique</span>
          <ExternalLink aria-hidden="true" size={16} strokeWidth={1.8} />
        </a>
        <ThemeToggle />
        <IconButton disabled={loggingOut} label="Se déconnecter" onClick={handleLogout}>
          <LogOut aria-hidden="true" size={18} strokeWidth={1.8} />
        </IconButton>
      </div>
    </header>
  )
}
