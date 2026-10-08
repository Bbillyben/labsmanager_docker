import { Input } from '../components/ui/input'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '../components/ui/dropdown-menu'
import { DropdownMenuSeparator } from '../components/ui/dropdown-menu'
import { AdminObjectAction } from '../components/AdminObjectAction'
import { Download, Ellipsis, ExternalLink, Pencil, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { employeeQuery, getEmployee, getEmployeeFilterOptions, getEmployees, readEmployeeParams, type EmployeeDetail, type EmployeeFilterOptions, type EmployeeIdentity, type EmployeeListParams, type EmployeeListResponse, type EmployeeSortField } from '../api/employees'
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
import { projectFilterSources } from '../config/projectFilterSources'
import { ListExportDialog } from '../components/ListExportDialog'
import { filterDefaultsMarker } from '../filters/url'
import { useTranslation } from '../i18n/i18n'
import { EmployeeSheet } from './EmployeeSheet'

const fullName = (employee: EmployeeIdentity) => `${employee.first_name} ${employee.last_name}`
const employeeUrl = (id: number) => `/employees/${id}`
const filterSources = { ...employeeFilterSources, ...projectFilterSources }
function dateLabel(value: string | null, language: string) {
  return value ? new Intl.DateTimeFormat(language, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : '—'
}

type UpdateParams = (patch: Partial<EmployeeListParams>) => void

export function EmployeeListPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useSearchParams()
  const params = readEmployeeParams(query)
  const canonicalQuery = employeeQuery(params)
  const [retry, setRetry] = useState(0)
  const [options, setOptions] = useState<EmployeeFilterOptions | null>(null)
  const [optionsError, setOptionsError] = useState(false)
  const [optionsRetry, setOptionsRetry] = useState(0)
  const [exportOpen, setExportOpen] = useState(false)
  const exportButton = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    getEmployeeFilterOptions(controller.signal).then((value) => { if (!controller.signal.aborted) setOptions(value) }, () => { if (!controller.signal.aborted) setOptionsError(true) })
    return () => controller.abort()
  }, [optionsRetry])

  // Keep shared URLs consistent with the parameters actually sent to v1.
  useEffect(() => {
    if (query.toString() !== canonicalQuery) setQuery(canonicalQuery, { replace: true })
  }, [query, canonicalQuery, setQuery])

  const update: UpdateParams = (patch) => setQuery(employeeQuery({ ...params, offset: 0, ...patch }))
  const reset = () => update({ search: '', filters: new URLSearchParams() })
  const filtered = Boolean(params.search || [...params.filters.values()].some(Boolean))

  return <>
    <PageHeader title={t('page.employees')} />
    <div className={styles.toolbar}>
      <form key={params.search} role="search" className={styles.search} onSubmit={(event) => {
        event.preventDefault()
        const search = String(new FormData(event.currentTarget).get('search') ?? '').trim()
        update({ search })
      }}>
        <label htmlFor="employee-search">{t('employee.listSearch')}</label>
        <div className={styles.controls}>
          <Input id="employee-search" name="search" type="search" defaultValue={params.search} placeholder={t('employee.searchPlaceholder')} />
          <Button variant="ghost" type="submit">{t('common.search')}</Button>
        </div>
      </form>
      <Button ref={exportButton} variant="secondary" onClick={() => setExportOpen(true)}><Download aria-hidden="true" />{t('listExport.title')}</Button>
      {filtered && <Button variant="ghost" onClick={reset}>{t('list.searchReset')}</Button>}
    </div>
    {optionsError && <Alert tone="danger">{t('employee.filterOptionsError')} <Button variant="ghost" onClick={() => { setOptionsError(false); setOptionsRetry((value) => value + 1) }}>{t('common.retry')}</Button></Alert>}
    <FilterBar catalogue={employeeFilters(t)} sources={filterSources} choiceOptions={{
      statuses: options?.statuses.map((item) => ({ value: String(item.id), label: item.name })) ?? [],
      teams: options?.teams.map((item) => ({ value: String(item.id), label: item.name })) ?? [],
    }} query={new URLSearchParams(canonicalQuery)} onChange={setQuery} resetParameters={['offset']} />
    {params.search && <p className={styles.summary}>{t('list.searchSummary', { query: params.search })}</p>}
    <EmployeeResults key={`${employeeQuery(params, true)}:${retry}`} params={params} update={update} filtered={filtered} reset={reset} retry={() => setRetry((value) => value + 1)} />
    {exportOpen && <ListExportDialog entity="employees" listQuery={canonicalQuery} returnFocus={exportButton} onClose={() => setExportOpen(false)} />}
  </>
}

function EmployeeResults({ params, update, filtered, reset, retry }: { params: EmployeeListParams; update: UpdateParams; filtered: boolean; reset: () => void; retry: () => void }) {
  const { t, language } = useTranslation()
  const [result, setResult] = useState<EmployeeListResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState<EmployeeDetail | null>(null)
  const [editError, setEditError] = useState(false)
  const [loadingEditId, setLoadingEditId] = useState<number | null>(null)
  const [refreshVersion, setRefreshVersion] = useState(0)
  const editTrigger = useRef<HTMLElement | null>(null)
  const openingEditor = useRef(false)
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
  }, [requestParams, refreshVersion])

  if (error) return <div className={styles.feedback}><Alert tone="danger">{error instanceof ApiError && error.status === 403 ? t('employee.listForbidden') : t('employee.listLoadError')}</Alert><Button variant="ghost" onClick={retry}>{t('common.retry')}</Button></div>
  if (!result) return <div className={styles.loading}><LoadingState message={t('employee.listLoading')} /></div>

  const selected = result.results.find((employee) => employee.id === selectedId)
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil(result.count / params.limit))
  function sortable(label: string, field: EmployeeSortField) {
    return <SortableTableHeader label={label} field={field} ordering={params.ordering || 'first_name'} onSort={(ordering) => update({ ordering })} />
  }

  async function openEditor(id: number) {
    openingEditor.current = true
    setLoadingEditId(id)
    setEditError(false)
    let opened = false
    try {
      const detail = await getEmployee(String(id), new AbortController().signal)
      if (detail.capabilities?.can_change) { opened = true; setEditing(detail) }
      else setEditError(true)
    } catch {
      setEditError(true)
    } finally {
      setLoadingEditId(null)
      openingEditor.current = false
      if (!opened) editTrigger.current?.focus()
    }
  }

  return <section aria-label={t('employee.listLabel')}>
    {editError && <Alert tone="danger">{t('employee.loadError')}</Alert>}
    <p className={styles.summary} role="status">{t(result.count === 1 ? 'employee.countOne' : 'employee.countMany', { count: result.count })}{result.results.length > 0 && ` · ${params.offset + 1}–${params.offset + result.results.length}`}</p>
    <p className="sr-only" role="status">{selected ? t('list.selected', { name: fullName(selected) }) : t('list.noneSelected')}</p>
    {result.results.length > 0 ? <div className={styles.scroll} role="region" aria-label={t('employee.tableScroll')} tabIndex={0}>
      <table className={styles.table}>
        <caption className={styles.caption}>{t('employee.tableHelp')}</caption>
        <thead><tr>{sortable(t('employee.columnEmployee'), 'first_name')}<th scope="col">{t('employee.currentStatuses')}</th><th scope="col">{t('employee.superiors')}</th>{sortable(t('employee.columnEntry'), 'entry_date')}{sortable(t('employee.columnExit'), 'exit_date')}{sortable(t('employee.activity'), 'is_active')}<th scope="col"><span className="sr-only">{t('list.actions')}</span></th></tr></thead>
        <tbody>{result.results.map((employee) => <SelectableTableRow key={employee.id} id={`employee-row-${employee.id}`} rowId={employee.id} selectedId={selectedId} onSelect={setSelectedId}>
          <th scope="row"><span className={styles.selectionMark} aria-hidden="true">{selectedId === employee.id ? '✓' : ''}</span><Link to={employeeUrl(employee.id)} state={{ employeeListSearch: employeeQuery(params) }}>{fullName(employee)}</Link></th>
          <td><div className={styles.statuses}>{employee.current_statuses.length ? employee.current_statuses.map((status, index) => <StatusBadge key={`${status.id}-${index}`}>{status.name || status.code}</StatusBadge>) : '—'}</div></td>
          <td>{employee.superiors.length ? employee.superiors.map(fullName).join(', ') : '—'}</td>
          <td className={styles.date}>{dateLabel(employee.entry_date, language)}</td><td className={styles.date}>{dateLabel(employee.exit_date, language)}</td>
          <td><ActivityStatusBadge active={employee.is_active} /></td>
          <td className={styles.actions}>
            <DropdownMenu onOpenChange={(open) => { if (open) { returnToRow.current = false; setSelectedId(employee.id) } }}>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" className={styles.rowMenu} />} aria-label={t('common.actionsFor', { name: fullName(employee) })} onClick={(event) => { editTrigger.current = event.currentTarget }}><Ellipsis /></DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-52" finalFocus={() => openingEditor.current || editing ? false : returnToRow.current ? document.getElementById(`employee-row-${employee.id}`) : true}>
                <DropdownMenuItem render={<Link to={employeeUrl(employee.id)} state={{ employeeListSearch: employeeQuery(params) }} />}><ExternalLink /> {t('list.openProfile')}</DropdownMenuItem>
                {employee.capabilities?.can_change && <DropdownMenuItem disabled={loadingEditId === employee.id} onClick={() => { void openEditor(employee.id) }}><Pencil /> {t('employee.edit')}</DropdownMenuItem>}
                <DropdownMenuItem onClick={() => { returnToRow.current = true; setSelectedId(null) }}><X /> {t('list.deselect')}</DropdownMenuItem>
                {employee.admin_url && <><DropdownMenuSeparator /><AdminObjectAction adminUrl={employee.admin_url} /></>}
              </DropdownMenuContent>
            </DropdownMenu>
          </td>
        </SelectableTableRow>)}</tbody>
      </table>
    </div> : params.offset > 0 ? <EmptyState title={t('list.emptyPage')} description={t('list.emptyPageDescription')} /> : <EmptyState title={filtered ? t('list.noResults') : t('employee.noAccessible')} description={filtered ? t('list.adjustFilters') : t('employee.noneInScope')} />}
    {result.results.length === 0 && (params.offset > 0 ? <Button variant="ghost" onClick={() => update({ offset: 0 })}>{t('list.firstPage')}</Button> : filtered && <Button variant="ghost" onClick={reset}>{t('list.clearCriteria')}</Button>)}
    <nav className={styles.pagination} aria-label={t('employee.pagination')}>
      <Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: Math.max(0, params.offset - params.limit) })}>{t('common.previous')}</Button>
      <span>{t('common.pageOf', { page, pages })}</span>
      <Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: params.offset + params.limit })}>{t('common.next')}</Button>
    </nav>
    {editing && <EmployeeSheet employee={editing} returnFocus={editTrigger} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); setRefreshVersion((value) => value + 1) }} />}
  </section>
}
