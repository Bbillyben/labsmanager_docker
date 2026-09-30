import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  getEmployeeCalendar,
  getEmployeeCalendarFilters,
  getEmployeeLeaves,
  getLeaveCapabilities,
  updateEmployeeLeave,
  type CalendarEvent,
  type EmployeeLeave,
  type EmployeeLeaveFilters,
  type EmployeeLeaveType,
  type LeaveWrite,
} from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { CalendarPluginFilters, effectiveCalendarFilterValues, type CalendarFilterValues } from '../calendar/CalendarPluginFilters'
import { halfDayLabel } from '../calendar/halfDayPresentation'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { useEmployeeDetail } from './employeeDetailContext'
import { EmployeeCalendar } from './EmployeeCalendar'
import { EmployeeLeaveSheet } from './EmployeeLeaveSheet'
import { leaveFromEvent, rangeLabel, typeFromEvent, uniqueTypes } from './leaveCalendarPresentation'
import { projectCalendarRange, projectCalendarScopeOrder, projectCalendarScopes, shiftProjectCalendarAnchor, type ProjectCalendarScope } from './projectCalendarScopes'
import styles from './EmployeeLeaves.module.css'

type DisplayMode = 'calendar' | 'table'
type Resource<T> = { data: T | null; error: unknown; loading: boolean; retry: () => void }
const modeKey = 'labsmanager:employee:leaves-display'
const viewKey = 'labsmanager:employee:leaves-calendar-view'

export function EmployeeLeaves() {
  const { employeeId } = useEmployeeDetail()
  const { language, t } = useTranslation()
  const [mode, setModeState] = useState<DisplayMode>(() => localStorage.getItem(modeKey) === 'table' ? 'table' : 'calendar')
  const [scope, setScopeState] = useState<ProjectCalendarScope>(() => {
    const stored = localStorage.getItem(viewKey)
    return projectCalendarScopeOrder.find((item) => item === stored) ?? 'month'
  })
  const [anchor, setAnchor] = useState(() => new Date())
  const [filters, setFilters] = useState<EmployeeLeaveFilters>({})
  const [calendarFilterValues, setCalendarFilterValues] = useState<CalendarFilterValues>({})
  const [knownTypes, setKnownTypes] = useState<EmployeeLeaveType[]>([])
  const [selected, setSelected] = useState<EmployeeLeave | null>(null)
  const [creating, setCreating] = useState<{ start_date: string; end_date: string } | null>(null)
  const [calendarMutationError, setCalendarMutationError] = useState<unknown>(null)
  const pendingLeaveMutation = useRef(false)
  const capabilityLoader = useCallback((signal: AbortSignal) => getLeaveCapabilities(employeeId, signal), [employeeId])
  const capabilities = useAsyncResource(capabilityLoader, `leave-capabilities:${employeeId}`)
  const range = useMemo(() => projectCalendarRange(scope, anchor), [scope, anchor])
  const calendarBounds = useMemo(() => ({
    from: filters.from && filters.from > range.from ? filters.from : range.from,
    to: filters.to && filters.to < range.to ? filters.to : range.to,
  }), [filters.from, filters.to, range])
  const calendarFilterLoader = useCallback((signal: AbortSignal) => getEmployeeCalendarFilters(employeeId, signal), [employeeId])
  const calendarFilterResource = useAsyncResource(calendarFilterLoader, `calendar-filters:${employeeId}`)
  const effectiveCalendarFilters = useMemo(() => effectiveCalendarFilterValues(calendarFilterResource.data ?? [], calendarFilterValues), [calendarFilterResource.data, calendarFilterValues])
  const serializedCalendarFilters = JSON.stringify(effectiveCalendarFilters)
  const calendarLoader = useCallback((signal: AbortSignal) => getEmployeeCalendar(employeeId, calendarBounds, filters.type ?? '', effectiveCalendarFilters, signal), [calendarBounds, effectiveCalendarFilters, employeeId, filters.type])
  const tableLoader = useCallback((signal: AbortSignal) => getEmployeeLeaves(employeeId, filters, signal), [employeeId, filters])
  const activeLoader = useCallback(async (signal: AbortSignal): Promise<CalendarEvent[] | EmployeeLeave[]> => mode === 'calendar' ? calendarLoader(signal) : tableLoader(signal), [calendarLoader, mode, tableLoader])
  const rememberTypes = useCallback((data: CalendarEvent[] | EmployeeLeave[]) => {
    const types = data.length > 0 && 'kind' in data[0]
      ? (data as CalendarEvent[]).filter((event) => event.kind === 'leave').map(typeFromEvent).filter((type): type is EmployeeLeaveType => type !== null)
      : (data as EmployeeLeave[]).map((leave) => leave.type)
    if (types.length) setKnownTypes((current) => uniqueTypes([...current, ...types]))
  }, [])
  const resourceKey = `${mode}:${employeeId}:${mode === 'calendar' ? `${calendarBounds.from}:${calendarBounds.to}:${filters.type ?? ''}:${serializedCalendarFilters}` : `${filters.from ?? ''}:${filters.to ?? ''}:${filters.type ?? ''}`}`
  const resource = useAsyncResource(activeLoader, resourceKey, rememberTypes)

  const setMode = (next: DisplayMode) => { localStorage.setItem(modeKey, next); setModeState(next) }
  const setScope = (next: ProjectCalendarScope) => { localStorage.setItem(viewKey, next); setScopeState(next) }
  const move = (direction: number) => setAnchor((current) => shiftProjectCalendarAnchor(current, scope, direction))
  const openEvent = (event: CalendarEvent) => {
    if (event.kind === 'leave') { setCreating(null); setSelected(leaveFromEvent(event)) }
  }
  const openCreate = (dates?: { start_date: string; end_date: string }) => { setSelected(null); setCreating(dates ?? { start_date: '', end_date: '' }) }
  const changed = (leave: EmployeeLeave) => { setSelected(leave); setCreating(null); resource.retry() }
  const deleted = () => { setSelected(null); setCreating(null); resource.retry() }
  const changeCalendarDates = async (event: CalendarEvent, write: LeaveWrite) => {
    if (pendingLeaveMutation.current) throw new Error('A Leave mutation is already pending')
    pendingLeaveMutation.current = true
    setCalendarMutationError(null)
    try {
      await updateEmployeeLeave(employeeId, Number(event.metadata.leave_id), write)
    } catch (error) {
      setCalendarMutationError(error)
      throw error
    } finally {
      pendingLeaveMutation.current = false
    }
    resource.retry()
  }
  const normalizedCalendarError = calendarMutationError ? normalizeMutationError(calendarMutationError) : null
  const calendarErrorText = normalizedCalendarError && (normalizedCalendarError.messages.join(' ') || Object.values(normalizedCalendarError.fields).flat().join(' ') || t(`genericInfo.error.${normalizedCalendarError.kind}`))

  return <section className={styles.root}>
    <div className={styles.toolbar}>
      <div aria-label={t('employee.navLeaves')} className={styles.segmented} role="group">
        <Button aria-pressed={mode === 'calendar'} onClick={() => setMode('calendar')} size="sm" variant={mode === 'calendar' ? 'default' : 'ghost'}>{t('leaves.calendar')}</Button>
        <Button aria-pressed={mode === 'table'} onClick={() => setMode('table')} size="sm" variant={mode === 'table' ? 'default' : 'ghost'}>{t('leaves.table')}</Button>
      </div>
      <LeaveFilters filters={filters} onChange={setFilters} types={knownTypes} />
      {capabilities.data?.can_add && <Button onClick={() => openCreate()} size="sm"><Plus aria-hidden="true" />{t('leaves.add')}</Button>}
      {Boolean(capabilities.error) && <div className={styles.error} role="alert">{t('leaves.capabilitiesError')} <Button onClick={capabilities.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    </div>

    {mode === 'calendar' && <>
      <div className={styles.calendarToolbar}>
        <div className={styles.navigation}>
          <Button aria-label={t('leaves.previous')} onClick={() => move(-1)} size="icon-sm" variant="ghost"><ChevronLeft aria-hidden="true" /></Button>
          <Button onClick={() => setAnchor(new Date())} size="sm" variant="ghost">{t('leaves.today')}</Button>
          <Button aria-label={t('leaves.next')} onClick={() => move(1)} size="icon-sm" variant="ghost"><ChevronRight aria-hidden="true" /></Button>
          <strong>{rangeLabel(range, language)}</strong>
        </div>
        <div aria-label={t('leaves.calendarLabel')} className={styles.segmented} role="group">
          {projectCalendarScopeOrder.map((item) => <Button aria-pressed={scope === item} key={item} onClick={() => setScope(item)} size="sm" variant={scope === item ? 'secondary' : 'ghost'}>{t(projectCalendarScopes[item].label)}</Button>)}
        </div>
      </div>
      {calendarFilterResource.error && <div className={styles.error} role="alert"><span>{t('leaves.pluginFiltersError')}</span><Button onClick={calendarFilterResource.retry} size="sm" variant="ghost">{t('common.retry')}</Button></div>}
      {calendarErrorText && <div className={styles.error} role="alert">{calendarErrorText}</div>}
      <CalendarPluginFilters definitions={calendarFilterResource.data ?? []} onChange={setCalendarFilterValues} values={calendarFilterValues} />
      <ResourceState resource={resource} />
      {resource.data && <>{resource.data.length === 0 && <p className={styles.state}>{t('leaves.empty')}</p>}<EmployeeCalendar anchor={anchor} events={resource.data as CalendarEvent[]} onOpen={openEvent} onCreate={openCreate} onChangeDates={changeCalendarDates} canCreate={Boolean(capabilities.data?.can_add)} canChange={Boolean(capabilities.data?.can_change)} projectScope={scope} /></>}
    </>}

    {mode === 'table' && <>
      <ResourceState resource={resource} />
      {resource.data && <LeaveTable leaves={resource.data as EmployeeLeave[]} onOpen={(leave) => { setCreating(null); setSelected(leave) }} />}
    </>}
    {(selected || creating) && <EmployeeLeaveSheet key={selected?.id ?? 'create'} employeeId={employeeId} leave={selected} initialDates={creating ?? undefined} capabilities={capabilities.data ?? { can_add: false, can_change: false, can_delete: false }} onClose={() => { setSelected(null); setCreating(null) }} onSaved={changed} onDeleted={deleted} />}
  </section>
}

function LeaveFilters({ filters, onChange, types }: { filters: EmployeeLeaveFilters; onChange: (filters: EmployeeLeaveFilters) => void; types: EmployeeLeaveType[] }) {
  const { t } = useTranslation()
  return <div className={styles.filters}>
    <label>{t('leaves.typeFilter')}<select onChange={(event) => onChange({ ...filters, type: event.target.value || undefined })} value={filters.type ?? ''}>
      <option value="">{t('leaves.allTypes')}</option>
      {types.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}
    </select></label>
    <label>{t('leaves.fromFilter')}<input max={filters.to} onChange={(event) => onChange({ ...filters, from: event.target.value || undefined })} type="date" value={filters.from ?? ''} /></label>
    <label>{t('leaves.toFilter')}<input min={filters.from} onChange={(event) => onChange({ ...filters, to: event.target.value || undefined })} type="date" value={filters.to ?? ''} /></label>
    {(filters.type || filters.from || filters.to) && <Button onClick={() => onChange({})} size="sm" variant="ghost">{t('leaves.resetFilters')}</Button>}
  </div>
}

export function LeaveTable({ leaves, onOpen, employeeNames }: { leaves: EmployeeLeave[]; onOpen: (leave: EmployeeLeave) => void; employeeNames?: Map<number, string> }) {
  const { language, t } = useTranslation()
  if (!leaves.length) return <p className={styles.state}>{t('leaves.empty')}</p>
  return <div className={styles.tableScroll}><table><thead><tr>{employeeNames && <th>{t('projectCalendar.participants')}</th>}<th>{t('leaves.type')}</th><th>{t('leaves.start')}</th><th>{t('leaves.end')}</th><th>{t('leaves.duration')}</th><th>{t('leaves.comment')}</th></tr></thead>
    <tbody>{leaves.map((leave) => { const period = halfDayLabel(leave, t); return <tr aria-label={t('leaves.open', { name: leave.type.name })} key={leave.id} onClick={() => onOpen(leave)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(leave) } }} tabIndex={0}>
      {employeeNames && <td>{employeeNames.get(leave.id) ?? '—'}</td>}<td><span className={styles.typeDot} style={{ background: leave.type.color }} />{leave.type.name}</td><td>{formatDate(leave.start_date, language)}</td><td>{formatDate(leave.end_date, language)}</td><td>{t('leaves.days', { count: leave.day_count })}<small>{period}</small></td><td>{leave.comment || '—'}</td>
    </tr> })}</tbody></table></div>
}

function ResourceState({ resource }: { resource: Resource<unknown> }) {
  const { t } = useTranslation()
  if (resource.loading) return <p className={styles.state} role="status">{t('leaves.loading')}</p>
  if (resource.error) return <div className={styles.error} role="alert"><span>{t('leaves.error')}</span><Button onClick={resource.retry} size="sm" variant="ghost">{t('common.retry')}</Button></div>
  return null
}

function useAsyncResource<T>(loader: (signal: AbortSignal) => Promise<T>, resourceKey: string, onData?: (data: T) => void): Resource<T> {
  const [attempt, setAttempt] = useState(0)
  const key = `${resourceKey}:${attempt}`
  const [state, setState] = useState<{ data: T | null; error: unknown; key: string }>({ data: null, error: null, key })
  useEffect(() => {
    const controller = new AbortController()
    loader(controller.signal).then((data) => { if (!controller.signal.aborted) { onData?.(data); setState({ data, error: null, key }) } }, (error: unknown) => { if (!controller.signal.aborted) setState({ data: null, error, key }) })
    return () => controller.abort()
  }, [key, loader, onData])
  const current = state.key === key ? state : { data: null, error: null }
  return { data: current.data, error: current.error, loading: !current.data && !current.error, retry: () => setAttempt((value) => value + 1) }
}

function formatDate(value: string, language: string) { return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) }
