import { useRef, useState } from 'react'
import { useTranslation } from '../i18n/i18n'
import { ArrowLeft, FileDown, FileText, Pencil, Settings2 } from 'lucide-react'
import { Link, NavLink, useLocation, useParams } from 'react-router-dom'
import { getProject } from '../api/projects'
import { ApiError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { Alert } from '../ui/Alert'
import { ActivityStatusBadge } from '../ui/ActivityStatusBadge'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { EntityActionMenu, type EntityActionGroup } from '../components/EntityActionMenu'
import { ReportExportDialog } from '../components/ReportExportDialog'
import { SettingsSheet } from '../components/SettingsSheet'
import { getProjectSettings, updateProjectSetting } from '../api/settings'
import { ProjectOverview } from './ProjectOverview'
import { ProjectPlanningPanel } from './ProjectPlanningPanel'
import { ProjectFundingPanel } from './ProjectFundingPanel'
import { ProjectBudgetsPanel } from './ProjectBudgetsPanel'
import { ProjectCalendarPanel } from './ProjectCalendarPanel'
import { ContractSection } from './ContractSection'
import { ProjectSheet } from './ProjectSheet'
import { GenericNotes } from '../components/GenericNotes'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeDetailPage.module.css'

const sections = [
  { id: 'overview', label: 'project.overview', enabled: true },
  { id: 'tasks', label: 'project.tasks', enabled: true },
  { id: 'calendar', label: 'project.calendar', enabled: true },
  { id: 'funds', label: 'project.funds', enabled: true },
  { id: 'budgets', label: 'projectBudgets.budgets', enabled: true },
  { id: 'contributions', label: 'projectBudgets.contributions', enabled: true },
  { id: 'contracts', label: 'project.contracts', enabled: true },
  { id: 'dashboard', label: 'project.dashboard', enabled: false },
  { id: 'notes', label: 'project.notes', enabled: true },
] as const

function dateLabel(value: string | null, language: string) { return value ? new Intl.DateTimeFormat(language, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : '—' }

export function ProjectDetailPage() {
  const { t, language } = useTranslation()
  const { projectId = '' } = useParams()
  const location = useLocation()
  const showPlanning = location.pathname.endsWith('/tasks')
  const showFunding = location.pathname.endsWith('/funding')
  const showBudgets = location.pathname.endsWith('/budgets')
  const showContributions = location.pathname.endsWith('/contributions')
  const showContracts = location.pathname.endsWith('/contracts')
  const showCalendar = location.pathname.endsWith('/calendar')
  const showNotes = location.pathname.endsWith('/notes')
  const resource = useEmployeeResource(projectId, getProject)
  const [editing, setEditing] = useState(false)
  const [exportFormat, setExportFormat] = useState<'word' | 'pdf' | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [contextVersion, setContextVersion] = useState(0)
  const actionTrigger = useRef<HTMLElement | null>(null)

  if (resource.loading) return <LoadingState message={t('project.loading')} />
  if (resource.error) {
    const status = resource.error instanceof ApiError ? resource.error.status : 0
    return <div className={styles.mainError}><Alert tone="danger">{status === 404 ? t('project.notFound') : status === 403 ? t('project.forbidden') : t('project.loadError')}</Alert>{status !== 404 && <Button onClick={resource.retry}>{t('common.retry')}</Button>}</div>
  }
  if (!resource.data) return null

  const project = resource.data
  const base = `/projects/${projectId}`
  const actionGroups: EntityActionGroup[] = [
    [
      ...(project.capabilities.can_change ? [{ id: 'edit', label: t('project.edit'), icon: <Pencil aria-hidden="true" />, onSelect: () => setEditing(true) }] : []),
      ...(project.capabilities.can_change_settings ? [{ id: 'settings', label: t('project.settings'), icon: <Settings2 aria-hidden="true" />, onSelect: () => setSettingsOpen(true) }] : []),
    ],
    [
      ...(project.capabilities.can_export_word ? [{ id: 'word', label: t('reports.word'), icon: <FileText aria-hidden="true" />, onSelect: () => setExportFormat('word' as const) }] : []),
      ...(project.capabilities.can_export_pdf ? [{ id: 'pdf', label: t('reports.pdf'), icon: <FileDown aria-hidden="true" />, onSelect: () => setExportFormat('pdf' as const) }] : []),
    ],
  ]
  return <>
    <Link className={styles.back} to={`/projects/${typeof location.state?.projectListSearch === 'string' && location.state.projectListSearch ? `?${location.state.projectListSearch}` : ''}`}><ArrowLeft aria-hidden="true" /> {t('project.backToProjects')}</Link>
    <PageHeader title={project.name} meta={<div className={styles.headerMeta}><ActivityStatusBadge active={project.status} /><span>{t('project.dateRange', { start: dateLabel(project.start_date, language), end: dateLabel(project.end_date, language) })}</span></div>} actions={<EntityActionMenu label={t('reports.entityActions', { name: project.name })} groups={actionGroups} onTrigger={(trigger) => { actionTrigger.current = trigger }} finalFocus={() => editing || exportFormat || settingsOpen ? false : true} />} />
    <nav aria-label={t('project.navigation')} className={styles.resourceNav}>
      <div className={styles.resourceNavScroll} tabIndex={0}>
        {sections.filter((section) => section.id !== 'funds' || project.funding_visible).map((section) => section.enabled
          ? <NavLink className={({ isActive }) => `${styles.resourceLink} ${isActive ? styles.resourceLinkActive : ''}`} end key={section.id} to={section.id === 'tasks' ? `${base}/tasks` : section.id === 'calendar' ? `${base}/calendar` : section.id === 'funds' ? `${base}/funding` : section.id === 'budgets' ? `${base}/budgets` : section.id === 'contributions' ? `${base}/contributions` : section.id === 'contracts' ? `${base}/contracts` : section.id === 'notes' ? `${base}/notes` : base} state={location.state}>{t(section.label)}</NavLink>
          : <button disabled aria-disabled="true" className={styles.resourceLink} key={section.id} title={t('project.unavailableSection')} type="button">{t(section.label)}</button>)}
      </div>
    </nav>
    <div className={styles.panel}>{showPlanning ? <ProjectPlanningPanel key={contextVersion} projectId={projectId} /> : showCalendar ? <ProjectCalendarPanel key={`${contextVersion}:calendar`} projectId={projectId} /> : showFunding ? <ProjectFundingPanel key={contextVersion} projectId={projectId} /> : showBudgets ? <ProjectBudgetsPanel key={`${contextVersion}:budget`} projectId={projectId} kind="budget" /> : showContributions ? <ProjectBudgetsPanel key={`${contextVersion}:contribution`} projectId={projectId} kind="contribution" /> : showContracts ? <ContractSection key={`${contextVersion}:contracts`} scope={{ projectId }} /> : showNotes ? <GenericNotes scope="project" objectId={projectId} /> : <ProjectOverview projectId={projectId} resource={resource} />}</div>
    {editing && <ProjectSheet project={project} returnFocus={actionTrigger} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); void resource.refresh() }} />}
    {exportFormat && <ReportExportDialog entity="project" id={project.id} format={exportFormat} title={t('reports.projectTitle', { format: t(exportFormat === 'word' ? 'reports.word' : 'reports.pdf') })} timeframe={false} returnFocus={actionTrigger} onClose={() => setExportFormat(null)} />}
    {settingsOpen && <SettingsSheet title={t('project.settings')} description={t('settings.sheetDescription')} load={(signal) => getProjectSettings(projectId, signal)} save={(key, value) => updateProjectSetting(projectId, key, value)} returnFocus={actionTrigger} onClose={(changed) => { setSettingsOpen(false); if (changed) { setContextVersion((value) => value + 1); void resource.refresh() } }} />}
  </>
}
