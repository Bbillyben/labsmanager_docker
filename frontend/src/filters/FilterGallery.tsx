import { PopoverContent } from '../components/ui/popover'
import { Button } from '../ui/Button'
import { Input } from '../components/ui/input'
import { X, ChevronRight } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import type { SupportedFilter } from './types'
import styles from './Filters.module.css'

type Props = {
  catalogue: readonly SupportedFilter[]
  query: URLSearchParams
  onAdd: (filter: SupportedFilter) => void
  onClose: () => void
  finalFocus: () => HTMLElement | false | null
  id: string
}

export function FilterGallery({ catalogue, query, onAdd, onClose, finalFocus, id }: Props) {
  const [search, setSearch] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const titleId = useId()
  const normalize = (text: string) => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('fr')
  const available = catalogue.filter((filter) => normalize(filter.label).includes(normalize(search.trim())))
  const categories = [...new Set(available.map((filter) => filter.category))]

  return <PopoverContent id={id} aria-labelledby={titleId} align="start" initialFocus={input} finalFocus={finalFocus} className="w-80 max-w-[calc(100vw-2rem)] max-h-[70vh] overflow-y-auto gap-2 p-3">
    <div className={styles.galleryHeader}><h2 id={titleId}>Ajouter un filtre</h2><Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Fermer la galerie"><X /></Button></div>
    <label className={styles.searchLabel}>Rechercher un filtre<Input ref={input} type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un filtre…" /></label>
    {categories.map((category) => <section key={category} aria-label={category} className={styles.category}>
      <h3>{category}</h3>
      <div className={styles.tiles}>{available.filter((filter) => filter.category === category).map((filter) => {
        const active = query.has(filter.parameter)
        return <Button variant="ghost" key={filter.id} className="h-auto w-full justify-between px-2 py-2 text-left" disabled={active} onClick={() => onAdd(filter)}>
          <span><span className="block text-sm font-medium">{filter.label}</span><span className="block text-xs text-muted-foreground">{active ? 'Déjà ajouté' : filter.description}</span></span><ChevronRight />
        </Button>
      })}</div>
    </section>)}
    {available.length === 0 && <p role="status">Aucun filtre correspondant.</p>}
  </PopoverContent>
}
