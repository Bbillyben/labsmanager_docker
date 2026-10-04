import { Download, Ellipsis, ExternalLink, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Input } from '../components/ui/input'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu'
import { DropdownMenuSeparator } from '../components/ui/dropdown-menu'
import { AdminObjectAction } from '../components/AdminObjectAction'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { LoadingState } from '../components/LoadingState'
import { projectFilters } from '../config/projectFilters'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { FilterBar } from '../filters/FilterBar'
import { filterDefaultsMarker } from '../filters/url'
import type { FilterOption } from '../filters/types'
import { ApiError, normalizeMutationError } from '../api/errors'
import { deleteProject, getProjectCapabilities, getProjectFilterOptions, getProjects, projectQuery, readProjectParams, type ProjectCapabilities, type ProjectFilterOptions, type ProjectItem, type ProjectListParams, type ProjectListResponse } from '../api/projects'
import { useMutation } from '../api/useMutation'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { EmptyState } from '../ui/EmptyState'
import { PageHeader } from '../ui/PageHeader'
import { ProjectSheet } from './ProjectSheet'
import { ProjectListTable } from './ProjectListTable'
import { ListExportDialog } from '../components/ListExportDialog'
import styles from './EmployeeListPage.module.css'
import { useTranslation } from '../i18n/i18n'

const projectUrl = (id: number) => `/projects/${id}`
type UpdateParams = (patch: Partial<ProjectListParams>) => void

export function ProjectListPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useSearchParams()
  const params = readProjectParams(query)
  const canonicalQuery = projectQuery(params)
  const [retry, setRetry] = useState(0)
  const [capabilities, setCapabilities] = useState<ProjectCapabilities | null>(null)
  const [options, setOptions] = useState<ProjectFilterOptions | null>(null)
  const [auxiliaryError, setAuxiliaryError] = useState(false)
  const [auxiliaryRetry, setAuxiliaryRetry] = useState(0)
  const [creating, setCreating] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const exportButton = useRef<HTMLButtonElement | null>(null)
  const navigate = useNavigate()

  useEffect(() => { if (query.toString() !== canonicalQuery) setQuery(canonicalQuery, { replace: true }) }, [query, canonicalQuery, setQuery])
  useEffect(() => {
    const controller = new AbortController()
    getProjectCapabilities(controller.signal).then((value) => { if (!controller.signal.aborted) setCapabilities(value) }, () => { if (!controller.signal.aborted) setAuxiliaryError(true) })
    getProjectFilterOptions(controller.signal).then((value) => { if (!controller.signal.aborted) setOptions(value) }, () => { if (!controller.signal.aborted) setAuxiliaryError(true) })
    return () => controller.abort()
  }, [auxiliaryRetry])

  const update: UpdateParams = (patch) => setQuery(projectQuery({ ...params, offset: 0, ...patch }))
  const reset = () => update({ search: '', filters: new URLSearchParams() })
  const filtered = Boolean(params.search || [...params.filters.values()].some(Boolean))
  const choiceOptions: Record<string, FilterOption[]> = options ? {
    funders: options.funders.map((value) => ({ value: String(value.id), label: value.short_name })),
    institutions: options.institutions.map((value) => ({ value: String(value.id), label: value.short_name })),
    teams: options.teams.map((value) => ({ value: String(value.id), label: value.name })),
  } : {}

  return <>
    <PageHeader title={t('navigation.projects')} />
    <div className={styles.toolbar}>
      <form key={params.search} role="search" className={styles.search} onSubmit={(event) => { event.preventDefault(); update({ search: String(new FormData(event.currentTarget).get('search') ?? '').trim() }) }}>
        <label htmlFor="project-search">{t('project.listSearch')}</label>
        <div className={styles.controls}><Input id="project-search" name="search" type="search" defaultValue={params.search} placeholder={t('project.searchPlaceholder')} /><Button variant="ghost" type="submit">{t('common.search')}</Button></div>
      </form>
      <Button ref={exportButton} variant="secondary" onClick={() => setExportOpen(true)}><Download aria-hidden="true" />{t('listExport.title')}</Button>
      {capabilities?.can_add && <Button onClick={() => setCreating(true)}><Plus aria-hidden="true" />{t('project.add')}</Button>}
      {filtered && <Button variant="ghost" onClick={reset}>{t('list.searchReset')}</Button>}
    </div>
    {auxiliaryError && <Alert tone="danger">{t('project.auxiliaryError')} <Button variant="ghost" onClick={() => { setAuxiliaryError(false); setAuxiliaryRetry((value) => value + 1) }}>{t('common.retry')}</Button></Alert>}
    <FilterBar catalogue={projectFilters(t)} sources={employeeFilterSources} choiceOptions={choiceOptions} query={new URLSearchParams(canonicalQuery)} onChange={setQuery} resetParameters={['offset']} />
    {params.search && <p className={styles.summary}>{t('list.searchSummary', { query: params.search })}</p>}
    <ProjectResults key={`${projectQuery(params, true)}:${retry}`} params={params} update={update} filtered={filtered} reset={reset} retry={() => setRetry((value) => value + 1)} />
    {creating && <ProjectSheet project={null} onClose={() => setCreating(false)} onSaved={(id) => navigate(projectUrl(id), { state: { projectListSearch: projectQuery(params) } })} />}
    {exportOpen && <ListExportDialog entity="projects" listQuery={canonicalQuery} returnFocus={exportButton} onClose={() => setExportOpen(false)} />}
  </>
}

function ProjectResults({ params, update, filtered, reset, retry }: { params: ProjectListParams; update: UpdateParams; filtered: boolean; reset: () => void; retry: () => void }) {
  const { t } = useTranslation()
  const [result, setResult] = useState<ProjectListResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState<ProjectItem | null>(null)
  const [deleting, setDeleting] = useState<ProjectItem | null>(null)
  const returnToRow = useRef(false)
  const deleteButton = useRef<HTMLElement | null>(null)
  const deletion = useMutation()
  const navigate = useNavigate()
  const query = projectQuery(params, true)
  const requestParams = useMemo(() => {
    const activeQuery = new URLSearchParams(query)
    activeQuery.set(filterDefaultsMarker, '1')
    return readProjectParams(activeQuery)
  }, [query])

  useEffect(() => {
    const controller = new AbortController()
    getProjects(requestParams, controller.signal).then(
      (data) => { if (!controller.signal.aborted) setResult(data) },
      (reason: unknown) => { if (!controller.signal.aborted) setError(reason) },
    )
    return () => controller.abort()
  }, [requestParams])

  if (error) return <div className={styles.feedback}><Alert tone="danger">{error instanceof ApiError && error.status === 403 ? t('project.listForbidden') : t('project.listLoadError')}</Alert><Button variant="ghost" onClick={retry}>{t('common.retry')}</Button></div>
  if (!result) return <div className={styles.loading}><LoadingState message={t('project.listLoading')} /></div>

  const selected = result.results.find((project) => project.id === selectedId)
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil(result.count / params.limit))
  async function remove() {
    if (!deleting) return
    const result = await deletion.run(() => deleteProject(deleting.id))
    if (result) { setDeleting(null); setResult((current) => current && ({ ...current, count: current.count - 1, results: current.results.filter((item) => item.id !== deleting.id) })); retry() }
  }
  const deletionError = deletion.error ? normalizeMutationError(deletion.error) : null

  return <section aria-label={t('project.listLabel')}>
    <p className={styles.summary} role="status">{t(result.count === 1 ? 'project.countOne' : 'project.countMany', { count: result.count })}{result.results.length > 0 && ` · ${params.offset + 1}–${params.offset + result.results.length}`}</p>
    <p className="sr-only" role="status">{selected ? t('list.selected', { name: selected.name }) : t('list.noneSelected')}</p>
    {result.results.length > 0 ? <ProjectListTable projects={result.results} selectedId={selectedId} onSelect={setSelectedId} ordering={params.ordering} onSort={(ordering) => update({ ordering })} linkState={{ projectListSearch: projectQuery(params) }} renderActions={(project) => <DropdownMenu onOpenChange={(open) => { if (open) { returnToRow.current = false; setSelectedId(project.id) } }}>
            <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" className={styles.rowMenu} />} aria-label={t('common.actionsFor', { name: project.name })}><Ellipsis /></DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-52" finalFocus={() => returnToRow.current ? document.getElementById(`project-row-${project.id}`) : true}>
              <DropdownMenuItem onClick={() => navigate(projectUrl(project.id), { state: { projectListSearch: projectQuery(params) } })}><ExternalLink /> {t('list.openProfile')}</DropdownMenuItem>
              {project.capabilities.can_change && <DropdownMenuItem onClick={() => setEditing(project)}><Pencil aria-hidden="true" /> {t('common.edit')}</DropdownMenuItem>}
              {project.capabilities.can_delete && <DropdownMenuItem onClick={(event) => { deleteButton.current = event.currentTarget; setDeleting(project) }}><Trash2 aria-hidden="true" /> {t('common.delete')}</DropdownMenuItem>}
              <DropdownMenuItem onClick={() => { returnToRow.current = true; setSelectedId(null) }}><X /> {t('list.deselect')}</DropdownMenuItem>
              {project.admin_url && <><DropdownMenuSeparator /><AdminObjectAction adminUrl={project.admin_url} /></>}
            </DropdownMenuContent>
          </DropdownMenu>} /> : params.offset > 0 ? <EmptyState title={t('list.emptyPage')} description={t('list.emptyPageDescription')} /> : <EmptyState title={filtered ? t('list.noResults') : t('project.noAccessible')} description={filtered ? t('list.adjustFilters') : t('project.noneInScope')} />}
    {result.results.length === 0 && (params.offset > 0 ? <Button variant="ghost" onClick={() => update({ offset: 0 })}>{t('list.firstPage')}</Button> : filtered && <Button variant="ghost" onClick={reset}>{t('list.clearCriteria')}</Button>)}
    <nav className={styles.pagination} aria-label={t('project.pagination')}><Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: Math.max(0, params.offset - params.limit) })}>{t('common.previous')}</Button><span>{t('common.pageOf', { page, pages })}</span><Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: params.offset + params.limit })}>{t('common.next')}</Button></nav>
    {editing && <ProjectSheet project={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); retry() }} />}
    {deleting && <ConfirmDialog title={t('project.delete')} description={t('project.deleteDescription', { name: deleting.name })} pending={deletion.pending} onCancel={() => setDeleting(null)} onConfirm={() => void remove()} returnFocus={deleteButton} error={deletionError && <Alert tone="danger">{deletionError.messages.join(' ') || t('project.deleteError')}</Alert>} />}
  </section>
}
