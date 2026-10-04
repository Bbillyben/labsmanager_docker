import { useEffect, useId, useState, type KeyboardEvent, type RefObject } from 'react'
import { getSearchAutocomplete, type SearchAutocomplete } from '../api/globalSearch'
import { useTranslation } from '../i18n/i18n'
import styles from './Search.module.css'

type Props = {
  value: string
  onChange: (value: string) => void
  inputRef: RefObject<HTMLInputElement | null>
  provider?: string
  active?: boolean
  name?: string
  className?: string
  wrapClassName?: string
  onFallbackKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void
  onFocus?: () => void
  onSuggestionsVisible?: (visible: boolean) => void
  fallbackListId?: string
  fallbackActiveId?: string
  fallbackExpanded?: boolean
}

const suggestionLabels = {
  provider: 'globalSearch.suggestion.provider',
  field: 'globalSearch.suggestion.field',
  operator: 'globalSearch.suggestion.operator',
  generic_info_type: 'globalSearch.suggestion.genericInfo',
  value: 'globalSearch.suggestion.value',
} as const

export function SearchAutocompleteInput({ value, onChange, inputRef, provider, active = true, name,
  className, wrapClassName, onFallbackKeyDown, onFocus, onSuggestionsVisible,
  fallbackListId, fallbackActiveId, fallbackExpanded }: Props) {
  const { t } = useTranslation()
  const listId = useId()
  const [focused, setFocused] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [cursor, setCursor] = useState(value.length)
  const [selected, setSelected] = useState(-1)
  const [response, setResponse] = useState<{ key: string; data: SearchAutocomplete } | null>(null)
  const key = `${provider ?? ''}\u0000${value}\u0000${cursor}`
  const enabled = active && focused && !dismissed && value.length > 0 && Array.from(value).length <= 200
  const data = enabled && response?.key === key ? response.data : null
  const suggestions = data?.suggestions ?? []
  const showing = Boolean(data && (suggestions.length || data.incomplete))

  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void getSearchAutocomplete(value, cursor, { provider, signal: controller.signal })
        .then((data) => { if (!controller.signal.aborted) { setResponse({ key, data }); setSelected(-1) } })
        .catch(() => { if (!controller.signal.aborted) setResponse(null) })
    }, 180)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [enabled, value, cursor, provider, key])

  useEffect(() => { onSuggestionsVisible?.(showing) }, [showing, onSuggestionsVisible])

  function updateCursor() {
    setCursor(inputRef.current?.selectionStart ?? value.length)
    setDismissed(false)
  }

  function apply(index: number) {
    const suggestion = suggestions[index]
    if (!suggestion || !data) return
    const next = value.slice(0, data.replace_start) + suggestion.insert_text + value.slice(data.replace_end)
    const nextCursor = data.replace_start + suggestion.insert_text.length
    onChange(next)
    setCursor(nextCursor)
    setSelected(-1)
    setResponse(null)
    setDismissed(false)
    requestAnimationFrame(() => {
      inputRef.current?.focus()
      inputRef.current?.setSelectionRange(nextCursor, nextCursor)
    })
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (showing && suggestions.length) {
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setSelected((current) => (current + 1) % suggestions.length)
        return
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setSelected((current) => current <= 0 ? suggestions.length - 1 : current - 1)
        return
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        event.preventDefault()
        apply(selected >= 0 ? selected : 0)
        return
      }
    }
    if (showing && event.key === 'Escape') {
      event.preventDefault()
      setDismissed(true)
      return
    }
    onFallbackKeyDown?.(event)
  }

  return <div className={wrapClassName ?? styles.autocompleteWrap}>
    <input ref={inputRef} name={name} role="combobox" aria-label={t('globalSearch.search')}
      aria-autocomplete="list" aria-expanded={showing || Boolean(fallbackExpanded)}
      aria-controls={showing ? listId : fallbackExpanded ? fallbackListId : undefined}
      aria-activedescendant={showing ? selected >= 0 ? `${listId}-${selected}` : undefined : fallbackActiveId}
      className={`${styles.input} ${className ?? ''}`} placeholder={t('globalSearch.placeholder')}
      value={value} onChange={(event) => { onChange(event.target.value); setCursor(event.target.selectionStart ?? event.target.value.length); setDismissed(false) }}
      onClick={updateCursor} onSelect={updateCursor} onKeyUp={(event) => {
        if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) updateCursor()
      }} onFocus={() => { setFocused(true); onFocus?.() }} onBlur={() => setFocused(false)} onKeyDown={onKeyDown} />
    {showing && <div id={listId} role="listbox" aria-label={t('globalSearch.suggestions')} className={styles.preview}>
      {suggestions.map((suggestion, index) => <button key={`${suggestion.kind}:${suggestion.label}`} id={`${listId}-${index}`}
        type="button" role="option" aria-selected={selected === index}
        className={`${styles.suggestion} ${selected === index ? styles.active : ''}`}
        onMouseDown={(event) => event.preventDefault()} onClick={() => apply(index)}>
        <span>{suggestion.label}{suggestion.kind === 'provider' || suggestion.kind === 'field' || suggestion.label === 'info' ? ':' : ''}</span>
        <small>{suggestion.detail || t(suggestionLabels[suggestion.kind])}</small>
      </button>)}
      {!suggestions.length && <p className={styles.message}>{t('globalSearch.noSuggestions')}</p>}
    </div>}
  </div>
}
