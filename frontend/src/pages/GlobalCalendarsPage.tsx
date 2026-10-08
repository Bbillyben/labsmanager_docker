import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, Presentation } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getEmployeeFilterOptions, getLeaveTypes, type CalendarEvent, type CalendarFilter } from '../api/employees'
import { getProjectFilterOptions } from '../api/projects'
import { getGlobalCalendarFilters, getGlobalEmployeeCalendar, getGlobalProjectPlanning, globalCalendarQuery } from '../api/globalCalendars'
import { CalendarPluginFilters, effectiveCalendarFilterValues, type CalendarFilterValues } from '../calendar/CalendarPluginFilters'
import { SharedCalendar, type ResourceVisibilityMode } from '../calendar/SharedCalendar'
import { localToday } from '../calendar/resourceVisibility'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { employeeFilters } from '../config/employeeFilters'
import { projectFilterSources } from '../config/projectFilterSources'
import { projectFilters } from '../config/projectFilters'
import { FilterBar } from '../filters/FilterBar'
import { readFilterQuery, withFilterDefaults } from '../filters/url'
import type { FilterOption, SupportedFilter } from '../filters/types'
import { adaptPlanningGantt } from '../gantt/PlanningGanttAdapter'
import { PlanningGanttView } from '../gantt/PlanningGanttView'
import { planningWindow, type PlanningMonths } from '../gantt/planningWindow'
import { useTranslation } from '../i18n/i18n'
import { PrintButton } from '../print/PrintButton'
import type { CalendarPrintState } from '../print/CalendarPrintView'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { EmployeeCalendar } from './EmployeeCalendar'
import { EmployeeLeaveSheet } from './EmployeeLeaveSheet'
import { leaveFromEvent, rangeLabel } from './leaveCalendarPresentation'
import { MilestoneDetailSheet } from './MilestoneDetailSheet'
import { milestoneStateKey } from './milestonePresentation'
import { projectCalendarRange, projectCalendarScopeOrder, projectCalendarScopes, projectCalendarViewDefinition, shiftProjectCalendarAnchor } from './projectCalendarScopes'
import { useEmployeeResource } from './useEmployeeResource'
import { useTrackRecent } from '../hooks/useTrackRecent'
import styles from './EmployeeLeaves.module.css'
import '../dashboard/DashboardPage.css'

type Tab = 'employees' | 'projects'
const monthOptions = [6, 12, 24, 60, 120] as const
const dateText = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
const validDate = (value: string | null) => value && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) ? new Date(`${value}T12:00:00`) : new Date()

function catalogues(t: ReturnType<typeof useTranslation>['t']): Record<Tab, SupportedFilter[]> {
  const employee = employeeFilters(t).filter((filter) => ['activity', 'currentStatus', 'team'].includes(filter.id))
  const project = projectFilters(t).filter((filter) => ['active', 'stale', 'team', 'institution', 'funder'].includes(filter.id))
  return {
    employees: [
      ...employee.map((filter) => ({ ...filter, parameter: `employees_${filter.parameter}` })),
      { id: 'employee', label: t('calendars.employee'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'employees_employee', source: 'allEmployees', idFormat: 'positive-integer', placeholder: t('filters.personPlaceholder') },
      { id: 'leaveType', label: t('leaves.typeFilter'), category: t('filters.categorySituation'), type: 'dynamic-choice', parameter: 'employees_type', source: 'leaveTypes' },
    ] as SupportedFilter[],
    projects: [
      ...project.map((filter) => ({ ...filter, parameter: `projects_${filter.parameter}` })),
      { id: 'project', label: t('filters.project'), category: t('filters.categoryProject'), type: 'entity-search', parameter: 'projects_project', source: 'projects', idFormat: 'positive-integer', placeholder: t('filters.projectPlaceholder') },
      { id: 'milestoneStatus', label: t('calendars.milestoneStatus'), category: t('filters.categorySituation'), type: 'dynamic-choice', parameter: 'projects_milestone_status', source: 'milestoneStatuses' },
    ] as SupportedFilter[],
  }
}

function pluginValues(definitions: CalendarFilter[], query: URLSearchParams, tab: Tab): CalendarFilterValues {
  const values: CalendarFilterValues = {}
  for (const definition of definitions) {
    const key = `${tab}_plugin_${definition.id}`
    if (!query.has(key)) continue
    values[definition.id] = definition.type === 'checkbox' ? query.getAll(key) : query.get(key) ?? ''
  }
  return values
}

function apiFilters(catalogue: SupportedFilter[], query: URLSearchParams, tab: Tab) {
  const filtered = readFilterQuery(catalogue, query)
  const result = new URLSearchParams()
  for (const [key, value] of filtered) if (value) result.set(key.replace(`${tab}_`, ''), value)
  return result
}

export function GlobalCalendarsPage() {
  useTrackRecent('calendar')
  const { language, t } = useTranslation()
  const navigate = useNavigate()
  const [query, setQuery] = useSearchParams()
  const catalog = useMemo(() => catalogues(t), [t])
  const canonicalQuery = useMemo(() => {
    const next = withFilterDefaults([...catalog.employees, ...catalog.projects], query)
    if (!next.has('tab')) next.set('tab', 'employees')
    if (!next.has('employees_date')) next.set('employees_date', dateText(new Date()))
    if (!next.has('projects_date')) next.set('projects_date', dateText(new Date()))
    if (!next.has('view')) next.set('view', 'month')
    if (!next.has('calendar_mode')) next.set('calendar_mode', 'calendar')
    if (!next.has('months')) next.set('months', '24')
    return next
  }, [catalog, query])
  const tab: Tab = canonicalQuery.get('tab') === 'projects' ? 'projects' : 'employees'
  const [selectedLeave, setSelectedLeave] = useState<CalendarEvent | null>(null)
  const [resourceVisibilityMode, setResourceVisibilityMode] = useState<ResourceVisibilityMode>('period')
  const [selectedWork, setSelectedWork] = useState<import('../api/planning').PlanningMilestone | null>(null)
  const [presentation, setPresentation] = useState(false)
  const enterPresentationButton = useRef<HTMLButtonElement>(null)
  const exitPresentationButton = useRef<HTMLButtonElement>(null)
  const presentationOpened = useRef(false)
  const anchor = validDate(canonicalQuery.get(tab === 'employees' ? 'employees_date' : 'projects_date'))
  const scope = projectCalendarScopeOrder.find((value) => value === canonicalQuery.get('view')) ?? 'month'
  const calendarMode = canonicalQuery.get('calendar_mode') === 'resources' ? 'resources' : 'calendar'
  const months = monthOptions.find((value) => String(value) === canonicalQuery.get('months')) ?? 24
  const range = tab === 'employees' ? projectCalendarRange(scope, anchor) : planningWindow(anchor, months)
  const [optionsAttempt, setOptionsAttempt] = useState(0)
  const optionsLoader = useCallback((_key: string, signal: AbortSignal) => Promise.all([
    getEmployeeFilterOptions(signal), getProjectFilterOptions(signal), getLeaveTypes(signal),
  ]), [])
  const options = useEmployeeResource(String(optionsAttempt), optionsLoader)
  const filterLoader = useCallback((key: string, signal: AbortSignal) => getGlobalCalendarFilters(key as Tab, signal), [])
  const pluginDefinitions = useEmployeeResource(tab, filterLoader)
  const selectedPluginValues = pluginValues(pluginDefinitions.data ?? [], canonicalQuery, tab)
  const effectivePluginValues = effectiveCalendarFilterValues(pluginDefinitions.data ?? [], selectedPluginValues)
  const requestQuery = globalCalendarQuery(range, apiFilters(catalog[tab], canonicalQuery, tab), effectivePluginValues)
  const employeeLoader = useCallback((key: string, signal: AbortSignal) => getGlobalEmployeeCalendar(key, signal), [])
  const projectLoader = useCallback((key: string, signal: AbortSignal) => getGlobalProjectPlanning(key, signal), [])
  const employeeData = useEmployeeResource(requestQuery, employeeLoader, tab === 'employees')
  const today = localToday()
  const todayRequestQuery = globalCalendarQuery({ from: today, to: today }, apiFilters(catalog.employees, canonicalQuery, 'employees'), effectivePluginValues)
  const todayData = useEmployeeResource(todayRequestQuery, employeeLoader, tab === 'employees' && calendarMode === 'resources' && resourceVisibilityMode === 'today')
  const projectData = useEmployeeResource(requestQuery, projectLoader, tab === 'projects')
  const employeeNames = useMemo(() => new Map(Object.entries(employeeData.data?.employee_names ?? {}).map(([id, name]) => [Number(id), name])), [employeeData.data])
  const ganttData = useMemo(() => projectData.data ? adaptPlanningGantt(projectData.data.items, [], projectData.data.projects) : null, [projectData.data])

  useEffect(() => {
    if (presentation) { presentationOpened.current = true; exitPresentationButton.current?.focus() }
    else if (presentationOpened.current) enterPresentationButton.current?.focus()
  }, [presentation])

  useEffect(() => {
    if (canonicalQuery.toString() !== query.toString()) setQuery(canonicalQuery, { replace: true })
  }, [canonicalQuery, query, setQuery])

  function setParameter(key: string, value: string) {
    const next = new URLSearchParams(canonicalQuery)
    next.set(key, value)
    setQuery(next)
  }
  function setTab(nextTab: Tab) {
    setSelectedLeave(null)
    setSelectedWork(null)
    setParameter('tab', nextTab)
  }
  function setAnchor(date: Date) { setParameter(tab === 'employees' ? 'employees_date' : 'projects_date', dateText(date)) }
  function updatePluginFilters(values: CalendarFilterValues) {
    const next = new URLSearchParams(canonicalQuery)
    for (const definition of pluginDefinitions.data ?? []) {
      const key = `${tab}_plugin_${definition.id}`
      next.delete(key)
      const value = values[definition.id]
      if (Array.isArray(value)) value.forEach((item) => next.append(key, item))
      else if (value !== undefined) next.set(key, String(value))
    }
    setQuery(next)
  }
  const choices: Record<string, FilterOption[]> = tab === 'employees' ? {
    statuses: options.data?.[0].statuses.map((item) => ({ value: String(item.id), label: item.name })) ?? [],
    teams: options.data?.[0].teams.map((item) => ({ value: String(item.id), label: item.name })) ?? [],
    leaveTypes: options.data?.[2].map((item) => ({ value: String(item.id), label: item.name })) ?? [],
  } : {
    teams: options.data?.[1].teams.map((item) => ({ value: String(item.id), label: item.name })) ?? [],
    funders: options.data?.[1].funders.map((item) => ({ value: String(item.id), label: item.short_name })) ?? [],
    institutions: options.data?.[1].institutions.map((item) => ({ value: String(item.id), label: item.short_name })) ?? [],
    milestoneStatuses: (projectData.data?.milestone_statuses ?? []).map((value) => ({ value, label: t(milestoneStateKey(value)) })),
  }

  return <main className={presentation ? 'dashboard-presentation dashboard-presentation-overlay grid gap-5' : 'grid gap-5'}>
    <div hidden={presentation}><PageHeader title={t('calendars.title')} actions={<Button ref={enterPresentationButton} onClick={() => { setSelectedLeave(null); setSelectedWork(null); setPresentation(true) }} variant="secondary"><Presentation aria-hidden="true" />{t('dashboard.presentation')}</Button>} /></div>
    {presentation && <header className="dashboard-presentation-header"><Button ref={exitPresentationButton} onClick={() => setPresentation(false)} variant="ghost"><ArrowLeft aria-hidden="true" />{t('dashboard.exitPresentation')}</Button><h1>{t('calendars.title')}</h1></header>}
    <div aria-label={t('calendars.title')} className={styles.segmented} role="group">
      <Button aria-pressed={tab === 'employees'} onClick={() => setTab('employees')} variant={tab === 'employees' ? 'default' : 'ghost'}>{t('calendars.general')}</Button>
      <Button aria-pressed={tab === 'projects'} onClick={() => setTab('projects')} variant={tab === 'projects' ? 'default' : 'ghost'}>{t('calendars.projects')}</Button>
    </div>
    {Boolean(options.error) && <Alert tone="danger">{t('calendars.optionsError')} <Button onClick={() => setOptionsAttempt((value) => value + 1)} variant="ghost">{t('common.retry')}</Button></Alert>}
    <div hidden={presentation}><FilterBar catalogue={catalog[tab]} sources={tab === 'employees' ? employeeFilterSources : projectFilterSources} choiceOptions={choices} query={canonicalQuery} onChange={setQuery} /></div>
    {Boolean(pluginDefinitions.error) && <Alert tone="danger">{t('leaves.pluginFiltersError')} <Button onClick={pluginDefinitions.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
    <div hidden={presentation}><CalendarPluginFilters definitions={pluginDefinitions.data ?? []} values={selectedPluginValues} onChange={updatePluginFilters} /></div>
    {tab === 'employees' && <section aria-label={t('calendars.general')} className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div aria-label={t('project.calendar')} className={styles.segmented} role="group">
          {(['calendar', 'resources'] as const).map((mode) => <Button aria-pressed={calendarMode === mode} key={mode} onClick={() => setParameter('calendar_mode', mode)} variant={calendarMode === mode ? 'default' : 'ghost'}>{t(`projectCalendar.${mode}`)}</Button>)}
        </div>
        <Button aria-label={t('leaves.previous')} onClick={() => setAnchor(shiftProjectCalendarAnchor(anchor, scope, -1))} size="icon-sm" variant="ghost">‹</Button>
        <Button onClick={() => setAnchor(new Date())} variant="ghost">{t('leaves.today')}</Button>
        <Button aria-label={t('leaves.next')} onClick={() => setAnchor(shiftProjectCalendarAnchor(anchor, scope, 1))} size="icon-sm" variant="ghost">›</Button>
        <strong>{rangeLabel(range, language)}</strong>
        <div aria-label={t('projectCalendar.period')} className={styles.segmented} role="group">{projectCalendarScopeOrder.map((value) => <Button aria-pressed={scope === value} key={value} onClick={() => setParameter('view', value)} variant={scope === value ? 'secondary' : 'ghost'}>{t(projectCalendarScopes[value].label)}</Button>)}</div>
        {employeeData.data && !presentation && <PrintButton disabled={calendarMode === 'resources' && resourceVisibilityMode === 'today' && !todayData.data} createRequest={() => ({ renderer: 'calendar', title: t('calendars.general'), state: { scope, viewType: projectCalendarViewDefinition(scope, calendarMode).key, mode: calendarMode, range, events: employeeData.data?.events ?? [], resources: employeeData.data?.resources ?? [], todayEvents: todayData.data?.events, resourceVisibilityMode, employeeNames: Object.fromEntries(employeeNames), filters: { ...Object.fromEntries(apiFilters(catalog.employees, canonicalQuery, 'employees')), ...effectivePluginValues }, selectedId: selectedLeave?.id ?? null } satisfies CalendarPrintState })} />}
      </div>
      {Boolean(employeeData.error) && <Alert tone="danger">{t('calendars.loadError')} <Button onClick={employeeData.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
      {calendarMode === 'resources' && resourceVisibilityMode === 'today' && Boolean(todayData.error) && <Alert tone="danger">{t('calendars.loadError')} <Button onClick={todayData.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
      {employeeData.loading && <p role="status">{t('common.loading')}</p>}
      {employeeData.data && <>{calendarMode === 'resources'
        ? <SharedCalendar anchor={anchor} scope={scope} viewMode="resources" events={employeeData.data.events} resources={employeeData.data.resources ?? []} todayEvents={todayData.data?.events} resourceVisibilityMode={resourceVisibilityMode} onResourceVisibilityModeChange={setResourceVisibilityMode} onOpen={setSelectedLeave} />
        : <EmployeeCalendar anchor={anchor} events={employeeData.data.events} onOpen={setSelectedLeave} onCreate={() => {}} onChangeDates={async () => {}} canCreate={false} canChange={false} projectScope={scope} projectEmployeeNames={employeeNames} />}{!employeeData.data.events.length && <p>{t('calendars.empty')}</p>}</>}
      {selectedLeave && <EmployeeLeaveSheet key={selectedLeave.id} employeeId={String(selectedLeave.metadata.employee_id)} leave={leaveFromEvent(selectedLeave)} capabilities={{ can_add: false, can_change: false, can_delete: false }} onClose={() => setSelectedLeave(null)} onSaved={() => {}} onDeleted={() => {}} employeeName={employeeNames.get(Number(selectedLeave.metadata.employee_id))} />}
    </section>}
    {tab === 'projects' && <section aria-label={t('calendars.projects')}>
      {Boolean(projectData.error) && <Alert tone="danger">{t('calendars.loadError')} <Button onClick={projectData.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
      {projectData.loading && <p role="status">{t('common.loading')}</p>}
      <PlanningGanttView data={ganttData} events={projectData.data?.events ?? []} anchor={anchor} months={months} onAnchorChange={setAnchor} onMonthsChange={(value: PlanningMonths) => setParameter('months', String(value))} printTitle={t('calendars.projects')} printFilters={{ ...Object.fromEntries(apiFilters(catalog.projects, canonicalQuery, 'projects')), ...effectivePluginValues }} showPrint={!presentation} onSelect={(identity) => {
        if (identity.kind === 'project') navigate(`/projects/${identity.id}`)
        if (identity.kind === 'work') setSelectedWork(projectData.data?.items.find((item) => String(item.id) === identity.id) ?? null)
      }} />
      {projectData.data && !projectData.data.projects.length && <p>{t('calendars.empty')}</p>}
      <MilestoneDetailSheet milestone={selectedWork} onClose={() => setSelectedWork(null)} />
    </section>}
  </main>
}
