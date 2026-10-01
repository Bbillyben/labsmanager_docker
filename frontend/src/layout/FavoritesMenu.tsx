import { Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { favoritesChangedEvent, getFavorites, type FavoriteItem } from '../api/preferences'
import { getDjangoUrl } from '../config/django'
import { useTranslation } from '../i18n/i18n'
import styles from './Sidebar.module.css'

const groups = ['projects', 'employees', 'teams', 'institutions'] as const

export function FavoritesMenu({ expanded = true, onRequestExpand }: { expanded?: boolean; onRequestExpand?: () => void }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<FavoriteItem[] | null>(null)
  const [error, setError] = useState(false)
  const [version, setVersion] = useState(0)
  useEffect(() => {
    const refresh = () => setVersion((value) => value + 1)
    window.addEventListener(favoritesChangedEvent, refresh)
    return () => window.removeEventListener(favoritesChangedEvent, refresh)
  }, [])
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    getFavorites(controller.signal).then(
      (result) => { if (!controller.signal.aborted) { setItems(result); setError(false) } },
      () => { if (!controller.signal.aborted) { setItems(null); setError(true) } },
    )
    return () => controller.abort()
  }, [open, version])
  return <div className={styles.favorites}>
    <button className={styles.link} type="button" aria-expanded={open && expanded} aria-controls="sidebar-favorites" onClick={() => { if (!expanded) onRequestExpand?.(); setOpen((value) => !value) }} title={t('preferences.favorites')}>
      <Star aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('preferences.favorites')}</span>
    </button>
    {open && expanded && <div id="sidebar-favorites" className={styles.favoriteList}>
      {!items && !error && <p role="status">{t('common.loading')}</p>}
      {error && <p role="alert">{t('preferences.loadError')}</p>}
      {items && !items.length && <p>{t('preferences.empty')}</p>}
      {items && groups.map((group) => {
        const entries = items.filter((item) => item.group === group)
        return entries.length ? <div key={group} className={styles.favoriteGroup}><p>{t(`preferences.${group}`)}</p><ul>{entries.map((item) => <li key={`${item.type}:${item.id}`}>{item.legacy ? <a href={getDjangoUrl(item.url)}>{item.label}</a> : <Link to={item.url}>{item.label}</Link>}</li>)}</ul></div> : null
      })}
    </div>}
  </div>
}
