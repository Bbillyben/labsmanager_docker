import { FormEvent, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from '../i18n/i18n'
import { PageHeader } from '../ui/PageHeader'
import { SearchResultItem } from './SearchResults'
import { SearchAutocompleteInput } from './SearchAutocompleteInput'
import { groupResults, providerLabel } from './groupResults'
import { useGlobalSearch, useSearchSchema } from './useGlobalSearch'
import styles from './Search.module.css'

function pageUrl(query: string, provider?: string) {
  const params = new URLSearchParams({ q: query })
  if (provider) params.set('provider', provider)
  return `/search?${params}`
}

export function SearchPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const query = params.get('q') ?? ''
  const [draft, setDraft] = useState(query)
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => { setDraft(query) }, [query])
  const requestedProvider = params.get('provider') ?? ''
  const providers = useSearchSchema()
  const provider = providers.some((item) => item.key === requestedProvider) ? requestedProvider : undefined
  const { results, counts, loading, error } = useGlobalSearch(query, { provider, limit: provider ? 25 : 100, perProvider: provider ? 25 : 10, delay: 0 })
  const groups = groupResults(results, providers)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    navigate(pageUrl(draft.trim(), provider))
  }

  return <div className={styles.page}>
    <PageHeader title={query ? t('globalSearch.resultsFor', { query }) : t('globalSearch.results')} />
    <form onSubmit={submit}><SearchAutocompleteInput inputRef={inputRef} value={draft} onChange={setDraft}
      provider={provider} name="q" className={styles.pageSearch} wrapClassName={styles.pageAutocomplete} /></form>
    <nav className={styles.tabs} aria-label={t('globalSearch.providers')}>
      <Link to={pageUrl(query)} aria-current={!provider ? 'page' : undefined}>{t('globalSearch.all')}</Link>
      {providers.map((item) => <Link key={item.key} to={pageUrl(query, item.key)} aria-current={provider === item.key ? 'page' : undefined}>{item.label}{counts[item.key] !== undefined && ` (${counts[item.key]})`}</Link>)}
    </nav>
    {query.trim().length < 2 ? <p className="muted-text">{t('globalSearch.prompt')}</p> : error ? <p role="alert">{typeof error === 'string' ? t('globalSearch.error') : t('globalSearch.syntaxError', { message: error.message })}</p> : <>
      {loading && <p className="muted-text" role="status">{t('common.loading')}</p>}
      {!loading && !results.length && <p>{t('globalSearch.emptyFor', { query })}</p>}
      {groups.map(([key, items]) => <section key={key} className={styles.group} aria-label={providerLabel(key, providers)}><div className={styles.groupHeader}><h2>{providerLabel(key, providers)}</h2>{!provider && items.length >= 10 && <Link to={pageUrl(query, key)}>{t('globalSearch.viewProvider')}</Link>}</div>{items.map((item) => <SearchResultItem key={`${item.provider_key}:${item.object_id}`} result={item} providers={providers} />)}</section>)}
    </>}
  </div>
}
