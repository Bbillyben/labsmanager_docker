import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { Button } from '../ui/Button'
import { useTranslation } from '../i18n/i18n'

export function SortableTableHeader<T extends string>({ label, field, ordering, onSort }: {
  label: string
  field: T
  ordering: string
  onSort: (next: T | `-${T}`) => void
}) {
  const { t } = useTranslation()
  const ascending = ordering === field
  const descending = ordering === `-${field}`
  return <th scope="col" aria-sort={ascending ? 'ascending' : descending ? 'descending' : 'none'}><Button variant="ghost" size="sm" className="-ml-2" onClick={() => onSort(ascending ? `-${field}` : field)} aria-label={t('common.sortBy', { label: label.toLocaleLowerCase(), direction: t(ascending ? 'common.descending' : 'common.ascending') })}>{label} {ascending ? <ArrowUp /> : descending ? <ArrowDown /> : <ArrowUpDown />}</Button></th>
}
