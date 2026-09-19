import { Popover, PopoverTrigger } from '../components/ui/popover'
import { NativeSelect } from '../components/ui/native-select'
import { Button } from '../ui/Button'
import { Plus, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import type { EntitySources, SupportedFilter } from './types'
import { changeFilter, resetFilters } from './url'
import { FilterGallery } from './FilterGallery'
import { EntitySearch } from './EntitySearch'
import styles from './Filters.module.css'

type Props = {
  catalogue: readonly SupportedFilter[]
  sources: EntitySources
  query: URLSearchParams
  onChange: (query: URLSearchParams) => void
  resetParameters?: readonly string[]
}

export function FilterBar({ catalogue, sources, query, onChange, resetParameters = [] }: Props) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const bar = useRef<HTMLDivElement>(null)
  const pendingFocus = useRef<string | null>(null)
  const focusAfterClose = useRef<string | null>(null)
  const id = useId()
  const active = catalogue.filter((filter) => query.has(filter.parameter))
  useEffect(() => {
    if (pendingFocus.current) {
      const control = document.getElementById(pendingFocus.current)
      if (control && bar.current?.contains(control)) {
        control.focus()
        pendingFocus.current = null
      }
    }
  })
  function close() { setOpen(false) }
  function setValue(filter: SupportedFilter, value: string | null) {
    onChange(changeFilter(query, filter, value, resetParameters))
  }

  return <div ref={bar} className={styles.bar} role="region" aria-label="Filtres du tableau">
    <Popover open={open} onOpenChange={(next) => { if (next) focusAfterClose.current = null; setOpen(next) }}>
      <PopoverTrigger ref={trigger} render={<Button variant="ghost" />}><Plus /> Ajouter un filtre</PopoverTrigger>
      {open && <FilterGallery id={`${id}-gallery`} finalFocus={() => focusAfterClose.current ? false : trigger.current} catalogue={catalogue} query={query} onClose={close} onAdd={(filter) => {
        if (query.has(filter.parameter)) return
        pendingFocus.current = `${id}-${filter.id}`
        focusAfterClose.current = pendingFocus.current
        setValue(filter, '')
        setOpen(false)
      }} />}
    </Popover>
    {active.map((filter) => {
      const controlId = `${id}-${filter.id}`
      const value = query.get(filter.parameter) ?? ''
      return <div key={filter.id} className={styles.active}>
        <label htmlFor={controlId}>{filter.label}</label>
        {filter.type === 'static-choice' ? <NativeSelect size="sm" id={controlId} value={value} onChange={(event) => setValue(filter, event.target.value)}>
          <option value="">Choisir…</option>
          {filter.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </NativeSelect> : sources[filter.source] ? <EntitySearch key={`${filter.id}:${value}`} id={controlId} label={filter.label} value={value} placeholder={filter.placeholder} source={sources[filter.source]} onChange={(next) => { pendingFocus.current = controlId; setValue(filter, next) }} /> : <span role="alert">Source indisponible</span>}
        <Button variant="ghost" size="icon-xs" aria-label={`Supprimer le filtre ${filter.label.toLocaleLowerCase('fr')}`} onClick={() => { setValue(filter, null); trigger.current?.focus() }}><X /></Button>
      </div>
    })}
    {active.length > 0 && <Button variant="ghost" onClick={() => { onChange(resetFilters(query, catalogue, resetParameters)); trigger.current?.focus() }}>Réinitialiser les filtres</Button>}
  </div>
}
