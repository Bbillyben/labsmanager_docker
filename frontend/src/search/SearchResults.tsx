import { createElement } from 'react'
import { Link } from 'react-router-dom'
import type { SearchProviderSchema, SearchResult } from '../api/globalSearch'
import { useTranslation } from '../i18n/i18n'
import { genericInfoIcon } from '../pages/genericInfoIcons'
import styles from './Search.module.css'

export function SearchResultItem({ result, providers, onClick, active = false, optionId }: {
  result: SearchResult
  providers: SearchProviderSchema[]
  onClick?: () => void
  active?: boolean
  optionId?: string
}) {
  const { t } = useTranslation()
  const icon = genericInfoIcon(providers.find((provider) => provider.key === result.provider_key)?.icon ?? result.icon)
  // React Router already owns /app as its basename; the backend URL remains
  // authoritative and only its basename is removed for Router navigation.
  const to = result.url.startsWith('/app/') ? result.url.slice(4) : result.url
  const subtitle = result.provider_key === 'organization' && result.metadata?.role === 'institution'
    ? t('globalSearch.organizationRole.institution')
    : result.provider_key === 'organization' && result.metadata?.role === 'funder'
      ? t('globalSearch.organizationRole.funder') : result.subtitle
  return <Link id={optionId} role={optionId ? 'option' : undefined} aria-selected={optionId ? active : undefined} className={`${styles.result} ${active ? styles.active : ''}`} to={to} onClick={onClick}>
    {createElement(icon, { size: 18, 'aria-hidden': true })}
    <span className={styles.resultCopy}><strong>{result.title}</strong>{subtitle && <small>{subtitle}</small>}{result.match_reason && <small className={styles.reason}>{result.match_reason}</small>}</span>
  </Link>
}
