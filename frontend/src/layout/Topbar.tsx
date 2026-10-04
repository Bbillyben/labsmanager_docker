import { ChevronDown, IdCard, LogOut, PanelLeftClose, PanelLeftOpen, Settings, Shield, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { logout } from '../auth/authApi'
import { useAuth } from '../auth/AuthContext'
import type { AuthenticatedUser } from '../auth/types'
import { getDjangoUrl } from '../config/django'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { ThemeMenuItem } from '../ui/ThemeToggle'
import { IconButton } from '../ui/IconButton'
import { getPageContext } from './pageContext'
import { GlobalSearch } from '../search/GlobalSearch'
import styles from './Topbar.module.css'

type TopbarProps = { navigationExpanded: boolean; onToggleNavigation: () => void; user: AuthenticatedUser }

export function Topbar({ navigationExpanded, onToggleNavigation, user }: TopbarProps) {
  const auth = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState(false)
  const userDisplayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username
  const displayName = user.employee?.first_name || userDisplayName
  const pageContext = getPageContext(location.pathname)
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
        <IconButton aria-controls="primary-navigation" aria-expanded={navigationExpanded} label={navigationExpanded ? t('navigation.collapse') : t('navigation.expand')} onClick={onToggleNavigation}>
          <ToggleIcon aria-hidden="true" size={20} strokeWidth={1.8} />
        </IconButton>
        {pageContext && <span className={styles.context}>{t(pageContext.label)}</span>}
      </div>
      <div className={styles.account}>
        <GlobalSearch />
        {logoutError && <span className={styles.logoutError} role="alert">{t('user.logoutError')}</span>}
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`${t('user.menu')} : ${displayName}`}
            render={<Button className={styles.userTrigger} variant="ghost" />}
            title={user.username}
          >
            <UserRound aria-hidden="true" />
            <span className={styles.identity}>{displayName}</span>
            <ChevronDown aria-hidden="true" className={styles.chevron} />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-52">
            <DropdownMenuGroup><DropdownMenuLabel>{userDisplayName}</DropdownMenuLabel></DropdownMenuGroup>
            <DropdownMenuSeparator />
            {user.employee && <DropdownMenuItem render={<Link to={`/employees/${user.employee.id}`} />}>
              <IdCard aria-hidden="true" /> {t('user.profile')}
            </DropdownMenuItem>}
            <DropdownMenuItem render={<Link to="/settings/user" />}><Settings aria-hidden="true" /> {t('userSettings.title')}</DropdownMenuItem>
            {user.can_access_admin && user.admin_url && <DropdownMenuItem render={<a href={getDjangoUrl(user.admin_url)} />}><Shield aria-hidden="true" /> {t('user.admin')}</DropdownMenuItem>}
            <ThemeMenuItem />
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled={loggingOut} onClick={() => void handleLogout()}>
              <LogOut aria-hidden="true" /> {t('user.logout')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
