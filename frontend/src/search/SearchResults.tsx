import { createElement } from 'react'
import { Link } from 'react-router-dom'
import type { SearchProviderSchema, SearchResult } from '../api/globalSearch'
import { genericInfoIcon } from '../pages/genericInfoIcons'
import styles from './Search.module.css'

export function SearchResultItem({ result, providers, onClick, active = false, optionId }: {
  result: SearchResult
  providers: SearchProviderSchema[]
  onClick?: () => void
  active?: boolean
  optionId?: string
}) {
  const icon = genericInfoIcon(providers.find((provider) => provider.key === result.provider_key)?.icon ?? result.icon)
  // React Router already owns /app as its basename; the backend URL remains
  // authoritative and only its basename is removed for Router navigation.
  const to = result.url.startsWith('/app/') ? result.url.slice(4) : result.url
  return <Link id={optionId} role={optionId ? 'option' : undefined} aria-selected={optionId ? active : undefined} className={`${styles.result} ${active ? styles.active : ''}`} to={to} onClick={onClick}>
    {createElement(icon, { size: 18, 'aria-hidden': true })}
    <span className={styles.resultCopy}><strong>{result.title}</strong>{result.subtitle && <small>{result.subtitle}</small>}{result.match_reason && <small className={styles.reason}>{result.match_reason}</small>}</span>
  </Link>
}
