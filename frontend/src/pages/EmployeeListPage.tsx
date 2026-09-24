import { Input } from '../components/ui/input'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '../components/ui/dropdown-menu'
import { Ellipsis, ExternalLink, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { employeeQuery, getEmployees, readEmployeeParams, type EmployeeIdentity, type EmployeeListParams, type EmployeeListResponse, type EmployeeSortField } from '../api/employees'
import { ApiError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { EmptyState } from '../ui/EmptyState'
import { PageHeader } from '../ui/PageHeader'
import { StatusBadge } from '../ui/StatusBadge'
import { ActivityStatusBadge } from '../ui/ActivityStatusBadge'
import styles from './EmployeeListPage.module.css'
import { FilterBar } from '../filters/FilterBar'
import { employeeFilters } from '../config/employeeFilters'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { filterDefaultsMarker } from '../filters/url'

const fullName = (employee: EmployeeIdentity) => `${employee.first_name} ${employee.last_name}`
const employeeUrl = (id: number) => `/employees/${id}`
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
    <FilterBar catalogue={employeeFilters} sources={employeeFilterSources} query={new URLSearchParams(canonicalQuery)} onChange={setQuery} resetParameters={['offset']} />
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
  const requestParams = useMemo(() => {
    const activeQuery = new URLSearchParams(query)
    activeQuery.set(filterDefaultsMarker, '1')
    return readEmployeeParams(activeQuery)
  }, [query])

  useEffect(() => {
    const controller = new AbortController()
    getEmployees(requestParams, controller.signal).then(
      (data) => { if (!controller.signal.aborted) setResult(data) },
      (reason: unknown) => { if (!controller.signal.aborted) setError(reason) },
    )
    return () => controller.abort()
  }, [requestParams])

  if (error) return <div className={styles.feedback}><Alert tone="danger">{error instanceof ApiError && error.status === 403 ? 'Accès interdit à la liste des employés.' : 'Impossible de charger les employés. Réessayez.'}</Alert><Button variant="ghost" onClick={retry}>Réessayer</Button></div>
  if (!result) return <div className={styles.loading}><LoadingState message="Chargement des employés…" /></div>

  const selected = result.results.find((employee) => employee.id === selectedId)
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil(result.count / params.limit))
  function sortable(label: string, field: EmployeeSortField) {
    return <SortableTableHeader label={label} field={field} ordering={params.ordering || 'first_name'} onSort={(ordering) => update({ ordering })} />
  }

  return <section aria-label="Liste des employés">
    <p className={styles.summary} role="status">{result.count} {result.count === 1 ? 'employé' : 'employés'}{result.results.length > 0 && ` · ${params.offset + 1}–${params.offset + result.results.length}`}</p>
    <p className="sr-only" role="status">{selected ? `Sélection : ${fullName(selected)}` : 'Aucune ligne sélectionnée'}</p>
    {result.results.length > 0 ? <div className={styles.scroll} role="region" aria-label="Tableau des employés, défilement horizontal" tabIndex={0}>
      <table className={styles.table}>
        <caption className={styles.caption}>Cliquez sur une ligne pour la sélectionner ; au clavier, utilisez Entrée ou Espace. Le nom ouvre la fiche Employee.</caption>
        <thead><tr>{sortable('Employé', 'first_name')}<th scope="col">Statuts actuels</th><th scope="col">Supérieurs</th>{sortable('Entrée', 'entry_date')}{sortable('Sortie', 'exit_date')}{sortable('Activité', 'is_active')}<th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
        <tbody>{result.results.map((employee) => <SelectableTableRow key={employee.id} id={`employee-row-${employee.id}`} rowId={employee.id} selectedId={selectedId} onSelect={setSelectedId}>
          <th scope="row"><span className={styles.selectionMark} aria-hidden="true">{selectedId === employee.id ? '✓' : ''}</span><Link to={employeeUrl(employee.id)}>{fullName(employee)}</Link></th>
          <td><div className={styles.statuses}>{employee.current_statuses.length ? employee.current_statuses.map((status, index) => <StatusBadge key={`${status.id}-${index}`}>{status.name || status.code}</StatusBadge>) : '—'}</div></td>
          <td>{employee.superiors.length ? employee.superiors.map(fullName).join(', ') : '—'}</td>
          <td className={styles.date}>{dateLabel(employee.entry_date)}</td><td className={styles.date}>{dateLabel(employee.exit_date)}</td>
          <td><ActivityStatusBadge active={employee.is_active} /></td>
          <td className={styles.actions}>
            <DropdownMenu onOpenChange={(open) => { if (open) { returnToRow.current = false; setSelectedId(employee.id) } }}>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" className={styles.rowMenu} />} aria-label={`Actions pour ${fullName(employee)}`}><Ellipsis /></DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-52" finalFocus={() => returnToRow.current ? document.getElementById(`employee-row-${employee.id}`) : true}>
                <DropdownMenuItem render={<Link to={employeeUrl(employee.id)} />}><ExternalLink /> Ouvrir la fiche</DropdownMenuItem>
                <DropdownMenuItem onClick={() => { returnToRow.current = true; setSelectedId(null) }}><X /> Désélectionner</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </td>
        </SelectableTableRow>)}</tbody>
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
