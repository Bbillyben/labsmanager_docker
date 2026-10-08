import { Search, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from '../i18n/i18n'
import { IconButton } from '../ui/IconButton'
import { SearchResultItem } from './SearchResults'
import { SearchAutocompleteInput } from './SearchAutocompleteInput'
import { groupResults, providerLabel } from './groupResults'
import { useGlobalSearch, useSearchSchema } from './useGlobalSearch'
import styles from './Search.module.css'

function isTypingTarget(target: EventTarget | null) {
  return target instanceof HTMLElement && (target.isContentEditable || Boolean(target.closest('input, textarea, select, [contenteditable="true"], [role="textbox"]')))
}

export function GlobalSearch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const providers = useSearchSchema()
  const [open, setOpen] = useState(false)
  const [preview, setPreview] = useState(false)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(-1)
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const listId = useId()
  const { results, loading, error } = useGlobalSearch(open && !suggestionsOpen ? query : '', { limit: 9, perProvider: 3 })
  const groups = groupResults(results, providers)
  const visible = groups.flatMap(([, items]) => items)
  const searchPath = `/search?q=${encodeURIComponent(query.trim())}`

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !isTypingTarget(event.target)) {
        event.preventDefault()
        setOpen(true)
        setPreview(true)
        requestAnimationFrame(() => input.current?.focus())
      }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  }, [])

  useEffect(() => {
    function outside(event: PointerEvent) {
      if (root.current?.contains(event.target as Node)) return
      setPreview(false)
      if (!query.trim()) setOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [query])

  function close(clearQuery = false) {
    setOpen(false)
    setPreview(false)
    setSelected(-1)
    setSuggestionsOpen(false)
    if (clearQuery) setQuery('')
    root.current?.querySelector('button')?.focus()
  }

  function navigateTo(path: string) {
    navigate(path)
    close(true)
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      if (preview) { setPreview(false); setSelected(-1) } else close()
    } else if (event.key === 'ArrowDown' && preview) {
      event.preventDefault()
      setSelected((current) => current >= visible.length ? 0 : current + 1)
    } else if (event.key === 'ArrowUp' && preview) {
      event.preventDefault()
      setSelected((current) => current <= 0 ? visible.length : current - 1)
    } else if (event.key === 'Enter' && query.trim()) {
      event.preventDefault()
      navigateTo(preview && selected >= 0 && selected < visible.length ? visible[selected].url.slice(4) : searchPath)
    }
  }

  return <div ref={root} className={`${styles.topbarSearch} ${open ? styles.open : ''}`}>
    <IconButton label={t('globalSearch.shortcut')} aria-expanded={open} onClick={() => { if (open) close(); else { setOpen(true); setPreview(true); requestAnimationFrame(() => input.current?.focus()) } }}>
      {open ? <X size={19} aria-hidden="true" /> : <Search size={19} aria-hidden="true" />}
    </IconButton>
    {open && <div className={styles.inputWrap}>
      <SearchAutocompleteInput inputRef={input} value={query} onChange={(value) => { setQuery(value); setSelected(-1); setPreview(true) }}
        active={preview} onFocus={() => setPreview(true)} onSuggestionsVisible={setSuggestionsOpen}
        onFallbackKeyDown={onKeyDown} fallbackListId={listId}
        fallbackExpanded={preview && query.trim().length >= 2}
        fallbackActiveId={preview && selected >= 0 ? `${listId}-${selected}` : undefined} />
      {preview && !suggestionsOpen && query.trim().length >= 2 && <div id={listId} className={styles.preview} role="listbox" aria-label={t('globalSearch.results')}>
        {error ? <p className={styles.message} role="alert">{typeof error === 'string' ? t('globalSearch.error') : error.message}</p> : <>
          {groups.map(([key, items]) => <div key={key} role="group" aria-label={providerLabel(key, providers)}><h3>{providerLabel(key, providers)}</h3>{items.map((item) => {
            const index = visible.indexOf(item)
            return <SearchResultItem key={`${item.provider_key}:${item.object_id}`} result={item} providers={providers} optionId={`${listId}-${index}`} active={selected === index} onClick={() => close(true)} />
          })}</div>)}
          {!loading && !results.length && <p className={styles.message}>{t('globalSearch.empty')}</p>}
          {loading && <p className={styles.message} role="status">{t('common.loading')}</p>}
          <button id={`${listId}-${visible.length}`} role="option" aria-selected={selected === visible.length} className={`${styles.all} ${selected === visible.length ? styles.active : ''}`} onClick={() => navigateTo(searchPath)}>{t('globalSearch.viewAll')}</button>
        </>}
      </div>}
    </div>}
  </div>
}
