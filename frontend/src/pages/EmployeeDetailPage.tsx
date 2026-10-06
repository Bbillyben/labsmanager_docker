import { useRef, useState } from 'react'
import { ArrowLeft, FileDown, FileText } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom'
import { getEmployee } from '../api/employees'
import { ApiError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { EntityActionMenu, type EntityActionGroup } from '../components/EntityActionMenu'
import { ObjectPreferenceActions } from '../components/ObjectPreferenceActions'
import { ReportExportDialog } from '../components/ReportExportDialog'
import { StatusBadge } from '../ui/StatusBadge'
import { EmployeeDetailContext } from './employeeDetailContext'
import { useEmployeeResource } from './useEmployeeResource'
import { useTrackRecent } from '../hooks/useTrackRecent'
import styles from './EmployeeDetailPage.module.css'

export function EmployeeDetailPage() {
  const { employeeId = '' } = useParams()
  const location = useLocation()
  const { t } = useTranslation()
  const employee = useEmployeeResource(employeeId, getEmployee)
  useTrackRecent('employee', Number(employeeId), Boolean(employee.data))
  const [exportFormat, setExportFormat] = useState<'word' | 'pdf' | null>(null)
  const actionTrigger = useRef<HTMLElement | null>(null)

  if (employee.loading) return <LoadingState message={t('employee.loading')} />
  if (employee.error) {
    const status = employee.error instanceof ApiError ? employee.error.status : 0
    const message = status === 404 ? t('employee.notFound') : status === 403 ? t('employee.forbidden') : t('employee.loadError')
    return <div className={styles.mainError}><Alert tone="danger">{message}</Alert>{status !== 404 && <Button onClick={employee.retry}>{t('common.retry')}</Button>}</div>
  }
  if (!employee.data) return null

  const name = `${employee.data.first_name} ${employee.data.last_name}`
  const actionGroups: EntityActionGroup[] = [[
    ...(employee.data.capabilities?.can_export_word ? [{ id: 'word', label: t('reports.word'), icon: <FileText aria-hidden="true" />, onSelect: () => setExportFormat('word' as const) }] : []),
    ...(employee.data.capabilities?.can_export_pdf ? [{ id: 'pdf', label: t('reports.pdf'), icon: <FileDown aria-hidden="true" />, onSelect: () => setExportFormat('pdf' as const) }] : []),
  ]]
  return <EmployeeDetailContext.Provider value={{ employee: employee.data, employeeId, refreshEmployee: employee.refresh }}>
    <Link className={styles.back} to={`/employees/${typeof location.state?.employeeListSearch === 'string' && location.state.employeeListSearch ? `?${location.state.employeeListSearch}` : ''}`}><ArrowLeft aria-hidden="true" /> {t('common.backToEmployees')}</Link>
    <PageHeader
      title={name}
      actions={<div className="flex items-center gap-2"><ObjectPreferenceActions key={employee.data.id} type="employee" objectId={employee.data.id} /><EntityActionMenu label={t('reports.entityActions', { name })} groups={actionGroups} adminUrl={employee.data.admin_url} onTrigger={(trigger) => { actionTrigger.current = trigger }} finalFocus={() => exportFormat ? false : true} /></div>}
      meta={<div className={styles.headerMeta}>
        <StatusBadge tone={employee.data.is_active ? 'success' : 'neutral'}>{t(employee.data.is_active ? 'employee.active' : 'employee.inactive')}</StatusBadge>
        {employee.data.current_statuses.map((status) => <StatusBadge key={status.id}>{status.name || status.code}</StatusBadge>)}
      </div>}
    />
    <EmployeeResourceNav employeeId={employeeId} />
    <div className={styles.panel}><Outlet /></div>
    {exportFormat && <ReportExportDialog entity="employee" id={employee.data.id} format={exportFormat} title={t('reports.employeeTitle', { format: t(exportFormat === 'word' ? 'reports.word' : 'reports.pdf') })} timeframe returnFocus={actionTrigger} onClose={() => setExportFormat(null)} />}
  </EmployeeDetailContext.Provider>
}

const resourceLinks: Array<{ path: string; label: TranslationKey; end?: boolean }> = [
  { path: '', label: 'employee.navOverview', end: true },
  { path: 'contracts', label: 'employee.navContracts' },
  { path: 'projects', label: 'employee.navProjects' },
  { path: 'funding', label: 'employee.navFunding' },
  { path: 'leaves', label: 'employee.navLeaves' },
  { path: 'notes', label: 'employee.navNotes' },
]

function EmployeeResourceNav({ employeeId }: { employeeId: string }) {
  const { t } = useTranslation()
  const location = useLocation()
  const base = `/employees/${employeeId}`
  return <nav aria-label={t('employee.resourceNavigation')} className={styles.resourceNav}>
    <div className={styles.resourceNavScroll} tabIndex={0}>
      {resourceLinks.map((item) => <NavLink
        className={({ isActive }) => `${styles.resourceLink} ${isActive ? styles.resourceLinkActive : ''}`}
        end={item.end}
        key={item.path || 'overview'}
        to={item.path ? `${base}/${item.path}` : base}
        state={location.state}
      >{t(item.label)}</NavLink>)}
    </div>
  </nav>
}
