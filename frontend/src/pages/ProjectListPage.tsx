import { Ellipsis, ExternalLink, Pencil, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Input } from '../components/ui/input'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { LoadingState } from '../components/LoadingState'
import { projectFilters } from '../config/projectFilters'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { FilterBar } from '../filters/FilterBar'
import { filterDefaultsMarker } from '../filters/url'
import type { FilterOption } from '../filters/types'
import { ApiError, normalizeMutationError } from '../api/errors'
import { deleteProject, getProjectCapabilities, getProjectFilterOptions, getProjects, projectQuery, readProjectParams, type ProjectCapabilities, type ProjectFilterOptions, type ProjectItem, type ProjectListParams, type ProjectListResponse, type ProjectSortField } from '../api/projects'
import { useMutation } from '../api/useMutation'
import { Alert } from '../ui/Alert'
import { ActivityStatusBadge } from '../ui/ActivityStatusBadge'
import { Button } from '../ui/Button'
import { EmptyState } from '../ui/EmptyState'
import { PageHeader } from '../ui/PageHeader'
import { ProjectSheet } from './ProjectSheet'
import styles from './EmployeeListPage.module.css'

const projectUrl = (id: number) => `/projects/${id}`
const dateLabel = (value: string | null) => value ? value.split('-').reverse().join('/') : '—'
type UpdateParams = (patch: Partial<ProjectListParams>) => void

function CompactList({ values }: { values: string[] }) {
  if (!values.length) return <>—</>
  const shown = values.slice(0, 2).join(', ')
  return <span title={values.join(', ')} aria-label={values.join(', ')} tabIndex={values.length > 2 ? 0 : undefined}>{shown}{values.length > 2 ? ` +${values.length - 2}` : ''}</span>
}

export function ProjectListPage() {
  const [query, setQuery] = useSearchParams()
  const params = readProjectParams(query)
  const canonicalQuery = projectQuery(params)
  const [retry, setRetry] = useState(0)
  const [capabilities, setCapabilities] = useState<ProjectCapabilities | null>(null)
  const [options, setOptions] = useState<ProjectFilterOptions | null>(null)
  const [auxiliaryError, setAuxiliaryError] = useState(false)
  const [auxiliaryRetry, setAuxiliaryRetry] = useState(0)
  const [creating, setCreating] = useState(false)
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
    <PageHeader title="Projets" />
    <div className={styles.toolbar}>
      <form key={params.search} role="search" className={styles.search} onSubmit={(event) => { event.preventDefault(); update({ search: String(new FormData(event.currentTarget).get('search') ?? '').trim() }) }}>
        <label htmlFor="project-search">Rechercher un projet</label>
        <div className={styles.controls}><Input id="project-search" name="search" type="search" defaultValue={params.search} placeholder="Nom, participant, institution…" /><Button variant="ghost" type="submit">Rechercher</Button></div>
      </form>
      {capabilities?.can_add && <Button onClick={() => setCreating(true)}>Ajouter un projet</Button>}
      {filtered && <Button variant="ghost" onClick={reset}>Réinitialiser la recherche et les filtres</Button>}
    </div>
    {auxiliaryError && <Alert tone="danger">Impossible de charger les droits ou les options de filtre. <Button variant="ghost" onClick={() => { setAuxiliaryError(false); setAuxiliaryRetry((value) => value + 1) }}>Réessayer</Button></Alert>}
    <FilterBar catalogue={projectFilters} sources={employeeFilterSources} choiceOptions={choiceOptions} query={new URLSearchParams(canonicalQuery)} onChange={setQuery} resetParameters={['offset']} />
    {params.search && <p className={styles.summary}>Recherche : « {params.search} »</p>}
    <ProjectResults key={`${projectQuery(params, true)}:${retry}`} params={params} update={update} filtered={filtered} reset={reset} retry={() => setRetry((value) => value + 1)} />
    {creating && <ProjectSheet project={null} onClose={() => setCreating(false)} onSaved={(id) => navigate(projectUrl(id))} />}
  </>
}

function ProjectResults({ params, update, filtered, reset, retry }: { params: ProjectListParams; update: UpdateParams; filtered: boolean; reset: () => void; retry: () => void }) {
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

  if (error) return <div className={styles.feedback}><Alert tone="danger">{error instanceof ApiError && error.status === 403 ? 'Accès interdit à la liste des projets.' : 'Impossible de charger les projets. Réessayez.'}</Alert><Button variant="ghost" onClick={retry}>Réessayer</Button></div>
  if (!result) return <div className={styles.loading}><LoadingState message="Chargement des projets…" /></div>

  const selected = result.results.find((project) => project.id === selectedId)
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil(result.count / params.limit))
  async function remove() {
    if (!deleting) return
    const result = await deletion.run(() => deleteProject(deleting.id))
    if (result) { setDeleting(null); setResult((current) => current && ({ ...current, count: current.count - 1, results: current.results.filter((item) => item.id !== deleting.id) })); retry() }
  }
  function sortable(label: string, field: ProjectSortField) {
    return <SortableTableHeader label={label} field={field} ordering={params.ordering} onSort={(ordering) => update({ ordering })} />
  }
  const deletionError = deletion.error ? normalizeMutationError(deletion.error) : null

  return <section aria-label="Liste des projets">
    <p className={styles.summary} role="status">{result.count} {result.count === 1 ? 'projet' : 'projets'}{result.results.length > 0 && ` · ${params.offset + 1}–${params.offset + result.results.length}`}</p>
    <p className="sr-only" role="status">{selected ? `Sélection : ${selected.name}` : 'Aucune ligne sélectionnée'}</p>
    {result.results.length > 0 ? <div className={styles.scroll} role="region" aria-label="Tableau des projets, défilement horizontal" tabIndex={0}>
      <table className={styles.table}>
        <caption className={styles.caption}>Cliquez sur une ligne pour afficher son menu ; seul le nom ouvre la fiche du projet.</caption>
        <thead><tr>{sortable('Projet', 'name')}{sortable('Début', 'start_date')}{sortable('Fin', 'end_date')}<th scope="col">Institutions</th><th scope="col">Participants</th><th scope="col">Fonds</th>{sortable('Statut', 'status')}<th scope="col"><span className="sr-only">Menu</span></th></tr></thead>
        <tbody>{result.results.map((project) => <SelectableTableRow key={project.id} id={`project-row-${project.id}`} rowId={project.id} selectedId={selectedId} onSelect={setSelectedId}>
          <th scope="row"><span className={styles.selectionMark} aria-hidden="true">{selectedId === project.id ? '✓' : ''}</span><Link to={projectUrl(project.id)}>{project.name}</Link></th>
          <td className={styles.date}>{dateLabel(project.start_date)}</td><td className={styles.date}>{dateLabel(project.end_date)}</td>
          <td><CompactList values={project.institutions} /></td><td><CompactList values={project.participants} /></td><td><CompactList values={project.funds} /></td>
          <td><ActivityStatusBadge active={project.status} /></td>
          <td className={styles.actions}><DropdownMenu onOpenChange={(open) => { if (open) { returnToRow.current = false; setSelectedId(project.id) } }}>
            <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" className={styles.rowMenu} />} aria-label={`Actions pour ${project.name}`}><Ellipsis /></DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-52" finalFocus={() => returnToRow.current ? document.getElementById(`project-row-${project.id}`) : true}>
              <DropdownMenuItem onClick={() => navigate(projectUrl(project.id))}><ExternalLink /> Ouvrir la fiche</DropdownMenuItem>
              {project.capabilities.can_change && <DropdownMenuItem onClick={() => setEditing(project)}><Pencil /> Modifier</DropdownMenuItem>}
              {project.capabilities.can_delete && <DropdownMenuItem onClick={(event) => { deleteButton.current = event.currentTarget; setDeleting(project) }}><Trash2 /> Supprimer</DropdownMenuItem>}
              <DropdownMenuItem onClick={() => { returnToRow.current = true; setSelectedId(null) }}><X /> Désélectionner</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu></td>
        </SelectableTableRow>)}</tbody>
      </table>
    </div> : params.offset > 0 ? <EmptyState title="Cette page est vide" description="La liste a pu évoluer. Revenez à la première page." /> : <EmptyState title={filtered ? 'Aucun résultat' : 'Aucun projet accessible'} description={filtered ? 'Modifiez la recherche ou réinitialisez les filtres.' : 'Aucun projet n’est disponible dans votre périmètre.'} />}
    {result.results.length === 0 && (params.offset > 0 ? <Button variant="ghost" onClick={() => update({ offset: 0 })}>Première page</Button> : filtered && <Button variant="ghost" onClick={reset}>Effacer les critères</Button>)}
    <nav className={styles.pagination} aria-label="Pagination des projets"><Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: Math.max(0, params.offset - params.limit) })}>Précédent</Button><span>Page {page} sur {pages}</span><Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: params.offset + params.limit })}>Suivant</Button></nav>
    {editing && <ProjectSheet project={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); retry() }} />}
    {deleting && <ConfirmDialog title="Supprimer le projet" description={`Supprimer « ${deleting.name} » et les données liées selon les règles du serveur ?`} pending={deletion.pending} onCancel={() => setDeleting(null)} onConfirm={() => void remove()} returnFocus={deleteButton} error={deletionError && <Alert tone="danger">{deletionError.messages.join(' ') || 'Impossible de supprimer le projet.'}</Alert>} />}
  </section>
}
