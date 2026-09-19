import { Combobox, ComboboxInput, ComboboxContent, ComboboxList, ComboboxItem } from '../components/ui/combobox'
import { Button } from '../ui/Button'
import { useEffect, useState } from 'react'
import type { EntitySearchSource, FilterOption } from './types'
import styles from './Filters.module.css'

type Props = { id: string; label: string; value: string; placeholder?: string; source: EntitySearchSource; onChange: (value: string) => void }

export function EntitySearch({ id, label, value, placeholder, source, onChange }: Props) {
  const [resolved, setResolved] = useState<FilterOption | null>(null)
  const [resolution, setResolution] = useState<'loading' | 'ready' | 'missing' | 'error'>(value ? 'loading' : 'ready')
  const [attempt, setAttempt] = useState(0)
  const [draft, setDraft] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [result, setResult] = useState<{ query: string; options: FilterOption[]; hasMore: boolean; error?: boolean } | null>(null)

  useEffect(() => {
    if (!value) return
    const controller = new AbortController()
    source.resolve(value, controller.signal).then((option) => {
      if (!controller.signal.aborted) { setResolved(option); setResolution(option ? 'ready' : 'missing') }
    }, () => { if (!controller.signal.aborted) setResolution('error') })
    return () => controller.abort()
  }, [value, source, attempt])

  useEffect(() => {
    if (draft === null || !expanded) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      source.search(draft.trim(), controller.signal).then((response) => {
        if (!controller.signal.aborted) setResult({ query: draft, ...response })
      }, () => {
        if (!controller.signal.aborted) setResult({ query: draft, options: [], hasMore: false, error: true })
      })
    }, 300)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [draft, expanded, source, attempt])

  const current = result?.query === draft ? result : null
  const options = current?.options ?? []
  const showResults = expanded && draft !== null
  function choose(option: FilterOption) { setExpanded(false); setDraft(null); onChange(option.value) }
  function cancel() { setExpanded(false); setDraft(null) }

  return <div className={styles.entity}>
    <Combobox items={options} filter={null} value={resolved} inputValue={draft ?? resolved?.label ?? ''}
      isItemEqualToValue={(a, b) => a.value === b.value}
      open={showResults} onOpenChange={(open) => { if (!open) cancel(); else { setExpanded(true); if (draft === null) setDraft('') } }}
      onInputValueChange={(text, details) => { if (details.reason === 'input-change') { setDraft(text); setExpanded(true); setResult(null) } }}
      onValueChange={(option) => { if (option) choose(option) }}>
      <ComboboxInput id={id} aria-label={label} showTrigger={false} placeholder={resolution === 'loading' ? 'Chargement du libellé…' : placeholder ?? 'Rechercher…'} />
      <ComboboxContent>
        {!current && <p role="status" className="p-2 text-xs">Recherche en cours…</p>}
        {current?.error && <div role="alert" className="p-2 text-xs">Recherche indisponible. <Button variant="ghost" onClick={() => { setResult(null); setAttempt((count) => count + 1) }}>Réessayer la recherche</Button></div>}
        {current && !current.error && !options.length && <p role="status" className="p-2 text-xs">Aucun résultat.</p>}
        <ComboboxList aria-label={`Résultats pour ${label.toLocaleLowerCase('fr')}`}>
          {options.map((option) => <ComboboxItem key={option.value} value={option}>{option.label}</ComboboxItem>)}
        </ComboboxList>
        {current?.hasMore && <p className="p-2 text-xs">Affinez la recherche pour voir d’autres résultats.</p>}
      </ComboboxContent>
    </Combobox>
    {value && draft !== null && <small>Valeur appliquée : {resolved?.label ?? `ID ${value}`}</small>}
    {resolution === 'missing' && <small role="status">Valeur indisponible (ID {value}). Choisissez une autre valeur ou supprimez le filtre.</small>}
    {resolution === 'error' && <div role="alert">Libellé indisponible (ID {value}). <Button variant="ghost" onClick={() => { setResolution('loading'); setAttempt((count) => count + 1) }}>Réessayer le libellé</Button></div>}
  </div>
}
