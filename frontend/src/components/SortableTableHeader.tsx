import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { Button } from '../ui/Button'

export function SortableTableHeader<T extends string>({ label, field, ordering, onSort }: {
  label: string
  field: T
  ordering: string
  onSort: (next: T | `-${T}`) => void
}) {
  const ascending = ordering === field
  const descending = ordering === `-${field}`
  return <th scope="col" aria-sort={ascending ? 'ascending' : descending ? 'descending' : 'none'}><Button variant="ghost" size="sm" className="-ml-2" onClick={() => onSort(ascending ? `-${field}` : field)} aria-label={`Trier par ${label.toLowerCase()}, ordre ${ascending ? 'décroissant' : 'croissant'}`}>{label} {ascending ? <ArrowUp /> : descending ? <ArrowDown /> : <ArrowUpDown />}</Button></th>
}
