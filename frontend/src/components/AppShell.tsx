import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Sidebar } from '../layout/Sidebar'
import { Topbar } from '../layout/Topbar'
import styles from '../layout/AppShell.module.css'

export function AppShell() {
  const auth = useAuth()
  const isWideViewport = () => typeof window.matchMedia !== 'function' || window.matchMedia('(min-width: 64rem)').matches
  const [wideViewport, setWideViewport] = useState(isWideViewport)
  const [navigationExpanded, setNavigationExpanded] = useState(isWideViewport)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia('(min-width: 64rem)')
    const handleChange = (event: MediaQueryListEvent) => {
      setWideViewport(event.matches)
      setNavigationExpanded(event.matches)
    }
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [])

  if (auth.status !== 'authenticated') return null

  return (
    <div className={styles.shell} data-navigation-expanded={navigationExpanded}>
      <a className="skip-link" href="#main-content">Aller au contenu principal</a>
      <Sidebar expanded={navigationExpanded} interactive={wideViewport || navigationExpanded} user={auth.user} />
      {navigationExpanded && <button className={styles.backdrop} aria-label="Fermer la navigation" onClick={() => setNavigationExpanded(false)} type="button" />}
      <Topbar navigationExpanded={navigationExpanded} onToggleNavigation={() => setNavigationExpanded((expanded) => !expanded)} user={auth.user} />
      <main className={styles.main} id="main-content" tabIndex={-1}>
        <div className={styles.content}><Outlet /></div>
      </main>
    </div>
  )
}
