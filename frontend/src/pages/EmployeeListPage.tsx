import { Input } from '../components/ui/input'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '../components/ui/dropdown-menu'
import { Ellipsis, ExternalLink, X, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { employeeQuery, getEmployees, readEmployeeParams, type EmployeeIdentity, type EmployeeListParams, type EmployeeListResponse, type EmployeeSortField } from '../api/employees'
import { ApiError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { getDjangoUrl } from '../config/django'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { EmptyState } from '../ui/EmptyState'
import { PageHeader } from '../ui/PageHeader'
import { StatusBadge } from '../ui/StatusBadge'
import styles from './EmployeeListPage.module.css'
import { FilterBar } from '../filters/FilterBar'
import { employeeFilters } from '../config/employeeFilters'
import { employeeFilterSources } from '../config/employeeFilterSources'

const fullName = (employee: EmployeeIdentity) => `${employee.first_name} ${employee.last_name}`
const employeeUrl = (id: number) => getDjangoUrl(`/staff/employee/${id}`)
function dateLabel(value: string | null) {
  if (!value) return '—'
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

type UpdateParams = (patch: Partial<EmployeeListParams>) => void

export function EmployeeListPage() {
  const [query, setQuery] = useSearchParams()
  const params = readEmployeeParams(query)
  const canonicalQuery = employeeQuery(params)
  const [retry, setRetry] = useState(0)

  // Keep shared URLs consistent with the parameters actually sent to v1.
  useEffect(() => {
    if (query.toString() !== canonicalQuery) setQuery(canonicalQuery, { replace: true })
  }, [query, canonicalQuery, setQuery])

  const update: UpdateParams = (patch) => setQuery(employeeQuery({ ...params, offset: 0, ...patch }))
  const reset = () => update({ search: '', filters: new URLSearchParams() })
  const filtered = Boolean(params.search || [...params.filters.values()].some(Boolean))

  return <>
    <PageHeader title="Employés" />
    <div className={styles.toolbar}>
      <form key={params.search} role="search" className={styles.search} onSubmit={(event) => {
        event.preventDefault()
        const search = String(new FormData(event.currentTarget).get('search') ?? '').trim()
        update({ search })
      }}>
        <label htmlFor="employee-search">Rechercher un employé</label>
        <div className={styles.controls}>
          <Input id="employee-search" name="search" type="search" defaultValue={params.search} placeholder="Prénom ou nom" />
          <Button variant="ghost" type="submit">Rechercher</Button>
        </div>
      </form>
      {filtered && <Button variant="ghost" onClick={reset}>Réinitialiser la recherche et les filtres</Button>}
    </div>
    <FilterBar catalogue={employeeFilters} sources={employeeFilterSources} query={query} onChange={setQuery} resetParameters={['offset']} />
    {params.search && <p className={styles.summary}>Recherche : « {params.search} »</p>}
    <EmployeeResults key={`${employeeQuery(params, true)}:${retry}`} params={params} update={update} filtered={filtered} reset={reset} retry={() => setRetry((value) => value + 1)} />
  </>
}

function EmployeeResults({ params, update, filtered, reset, retry }: { params: EmployeeListParams; update: UpdateParams; filtered: boolean; reset: () => void; retry: () => void }) {
  const [result, setResult] = useState<EmployeeListResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const returnToRow = useRef(false)
  const query = employeeQuery(params, true)

  useEffect(() => {
    const controller = new AbortController()
    getEmployees(readEmployeeParams(new URLSearchParams(query)), controller.signal).then(
      (data) => { if (!controller.signal.aborted) setResult(data) },
      (reason: unknown) => { if (!controller.signal.aborted) setError(reason) },
    )
    return () => controller.abort()
  }, [query])

  if (error) return <div className={styles.feedback}><Alert tone="danger">{error instanceof ApiError && error.status === 403 ? 'Accès interdit à la liste des employés.' : 'Impossible de charger les employés. Réessayez.'}</Alert><Button variant="ghost" onClick={retry}>Réessayer</Button></div>
  if (!result) return <div className={styles.loading}><LoadingState message="Chargement des employés…" /></div>

  const selected = result.results.find((employee) => employee.id === selectedId)
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil(result.count / params.limit))
  const ordering = params.ordering || 'first_name'
  function sortable(label: string, field: EmployeeSortField) {
    const ascending = ordering === field
    const descending = ordering === `-${field}`
    return <th scope="col" aria-sort={ascending ? 'ascending' : descending ? 'descending' : 'none'}><Button variant="ghost" size="sm" className="-ml-2" onClick={() => update({ ordering: ascending ? `-${field}` : field })} aria-label={`Trier par ${label.toLowerCase()}, ordre ${ascending ? 'décroissant' : 'croissant'}`}>{label} {ascending ? <ArrowUp /> : descending ? <ArrowDown /> : <ArrowUpDown />}</Button></th>
  }

  return <section aria-label="Liste des employés">
    <p className={styles.summary} role="status">{result.count} {result.count === 1 ? 'employé' : 'employés'}{result.results.length > 0 && ` · ${params.offset + 1}–${params.offset + result.results.length}`}</p>
    <p className="sr-only" role="status">{selected ? `Sélection : ${fullName(selected)}` : 'Aucune ligne sélectionnée'}</p>
    {result.results.length > 0 ? <div className={styles.scroll} role="region" aria-label="Tableau des employés, défilement horizontal" tabIndex={0}>
      <table className={styles.table}>
        <caption className={styles.caption}>Cliquez sur une ligne pour la sélectionner ; au clavier, utilisez Entrée ou Espace. Le nom ouvre la fiche Django.</caption>
        <thead><tr>{sortable('Employé', 'first_name')}<th scope="col">Statuts actuels</th><th scope="col">Supérieurs</th>{sortable('Entrée', 'entry_date')}{sortable('Sortie', 'exit_date')}{sortable('Activité', 'is_active')}<th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
        <tbody>{result.results.map((employee) => <tr key={employee.id} id={`employee-row-${employee.id}`} tabIndex={0} aria-selected={selectedId === employee.id} data-selected={selectedId === employee.id}
          onClick={(event) => {
            if (!event.currentTarget.contains(event.target as Node) || (event.target as HTMLElement).closest('a, button, input, select, textarea')) return
            if (window.getSelection()?.toString()) return
            event.currentTarget.focus()
            setSelectedId(selectedId === employee.id ? null : employee.id)
          }}
          onKeyDown={(event) => {
            if (event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return
            event.preventDefault()
            setSelectedId(selectedId === employee.id ? null : employee.id)
          }}>
          <th scope="row"><span className={styles.selectionMark} aria-hidden="true">{selectedId === employee.id ? '✓' : ''}</span><a href={employeeUrl(employee.id)}>{fullName(employee)}</a></th>
          <td><div className={styles.statuses}>{employee.current_statuses.length ? employee.current_statuses.map((status, index) => <StatusBadge key={`${status.id}-${index}`}>{status.name || status.code}</StatusBadge>) : '—'}</div></td>
          <td>{employee.superiors.length ? employee.superiors.map(fullName).join(', ') : '—'}</td>
          <td className={styles.date}>{dateLabel(employee.entry_date)}</td><td className={styles.date}>{dateLabel(employee.exit_date)}</td>
          <td><StatusBadge tone={employee.is_active ? 'success' : 'neutral'}>{employee.is_active ? 'Actif' : 'Inactif'}</StatusBadge></td>
          <td className={styles.actions}>
            <DropdownMenu onOpenChange={(open) => { if (open) { returnToRow.current = false; setSelectedId(employee.id) } }}>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" className={styles.rowMenu} />} aria-label={`Actions pour ${fullName(employee)}`}><Ellipsis /></DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-52" finalFocus={() => returnToRow.current ? document.getElementById(`employee-row-${employee.id}`) : true}>
                <DropdownMenuItem render={<a href={employeeUrl(employee.id)} />}><ExternalLink /> Ouvrir la fiche (Django)</DropdownMenuItem>
                <DropdownMenuItem onClick={() => { returnToRow.current = true; setSelectedId(null) }}><X /> Désélectionner</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </td>
        </tr>)}</tbody>
      </table>
    </div> : params.offset > 0 ? <EmptyState title="Cette page est vide" description="La liste a pu évoluer. Revenez à la première page." /> : <EmptyState title={filtered ? 'Aucun résultat' : 'Aucun employé accessible'} description={filtered ? 'Modifiez la recherche ou réinitialisez les filtres.' : 'Aucun employé n’est disponible dans votre périmètre.'} />}
    {result.results.length === 0 && (params.offset > 0 ? <Button variant="ghost" onClick={() => update({ offset: 0 })}>Première page</Button> : filtered && <Button variant="ghost" onClick={reset}>Effacer les critères</Button>)}
    <nav className={styles.pagination} aria-label="Pagination des employés">
      <Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: Math.max(0, params.offset - params.limit) })}>Précédent</Button>
      <span>Page {page} sur {pages}</span>
      <Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: params.offset + params.limit })}>Suivant</Button>
    </nav>
  </section>
}
