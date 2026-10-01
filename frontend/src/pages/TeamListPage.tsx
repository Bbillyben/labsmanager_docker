import { Download, Plus } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getTeams, readTeamParams, teamQuery, type TeamListParams, type TeamListResponse, type TeamOrdering } from '../api/teams'
import { ApiError } from '../api/errors'
import { ListExportDialog } from '../components/ListExportDialog'
import { LoadingState } from '../components/LoadingState'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { FilterBar } from '../filters/FilterBar'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { teamFilters } from '../config/teamFilters'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { TeamFormSheet } from './TeamFormSheet'
import styles from './EmployeeListPage.module.css'

export function TeamListPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useSearchParams()
  const params = readTeamParams(query)
  const canonical = teamQuery(params)
  const [result, setResult] = useState<TeamListResponse | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [retry, setRetry] = useState(0)
  const [exportOpen, setExportOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const exportTrigger = useRef<HTMLButtonElement | null>(null)
  const createTrigger = useRef<HTMLButtonElement | null>(null)
  useEffect(() => { if (query.toString() !== canonical) setQuery(canonical, { replace: true }) }, [query, canonical, setQuery])
  const update = useCallback((patch: Partial<TeamListParams>) => setQuery(teamQuery({ ...params, offset: 0, ...patch })), [params, setQuery])
  useEffect(() => {
    const controller = new AbortController()
    getTeams(readTeamParams(new URLSearchParams(canonical)), controller.signal).then(
      (data) => { if (!controller.signal.aborted) { setResult(data); setError(null) } },
      (cause: unknown) => { if (!controller.signal.aborted) setError(cause) },
    )
    return () => controller.abort()
  }, [canonical, retry])
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil((result?.count ?? 0) / params.limit))
  const sort = (field: 'name' | 'leader__last_name') => <SortableTableHeader label={t(field === 'name' ? 'team.name' : 'team.leader')} field={field} ordering={params.ordering} onSort={(ordering) => update({ ordering: ordering as TeamOrdering })} />
  return <>
    <PageHeader title={t('navigation.teams')} />
    <div className="flex justify-end gap-2"><Button ref={exportTrigger} variant="secondary" onClick={() => setExportOpen(true)}><Download aria-hidden="true" />{t('listExport.title')}</Button>{result?.capabilities.can_add && <Button ref={createTrigger} onClick={() => setCreateOpen(true)}><Plus aria-hidden="true" />{t('team.addTeam')}</Button>}</div>
    <FilterBar catalogue={teamFilters(t)} sources={employeeFilterSources} query={new URLSearchParams(canonical)} onChange={setQuery} resetParameters={['offset']} />
    {error && <Alert tone="danger">{error instanceof ApiError && error.status === 403 ? t('team.forbidden') : t('team.loadError')} <Button onClick={() => setRetry((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {!error && !result && <LoadingState message={t('team.loading')} />}
    {!error && result && <section aria-label={t('navigation.teams')}>
      <p className={styles.summary} role="status">{t('team.count', { count: result.count })}</p>
      <div className={styles.scroll} role="region" aria-label={t('navigation.teams')} tabIndex={0}>
        <table className={styles.table}><thead><tr>{sort('name')}{sort('leader__last_name')}<th scope="col">{t('team.members')}</th></tr></thead>
          <tbody>{result.results.map((team) => <tr key={team.id}><th scope="row"><Link to={`/teams/${team.id}`} state={{ teamListSearch: canonical }}>{team.name}</Link></th><td>{team.leader.name}</td><td>{team.mates.length}</td></tr>)}</tbody>
        </table>
      </div>
      {!result.count && <p>{t('team.empty')}</p>}
      <nav className={styles.pagination} aria-label={t('team.pagination')}>
        <Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: Math.max(0, params.offset - params.limit) })}>{t('common.previous')}</Button>
        <span>{t('common.pageOf', { page, pages })}</span>
        <Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: params.offset + params.limit })}>{t('common.next')}</Button>
      </nav>
    </section>}
    {exportOpen && <ListExportDialog entity="teams" listQuery={canonical} returnFocus={exportTrigger} onClose={() => setExportOpen(false)} />}
    {createOpen && result && <TeamFormSheet team={null} createCapabilities={result.capabilities} onClose={() => setCreateOpen(false)} onSaved={() => { setCreateOpen(false); setRetry((value) => value + 1) }} returnFocus={createTrigger} />}
  </>
}
