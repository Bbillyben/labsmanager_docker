import { ArrowLeft } from 'lucide-react'
import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import { getEmployee } from '../api/employees'
import { ApiError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { StatusBadge } from '../ui/StatusBadge'
import { EmployeeDetailContext } from './employeeDetailContext'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeDetailPage.module.css'

export function EmployeeDetailPage() {
  const { employeeId = '' } = useParams()
  const { t } = useTranslation()
  const employee = useEmployeeResource(employeeId, getEmployee)

  if (employee.loading) return <LoadingState message={t('employee.loading')} />
  if (employee.error) {
    const status = employee.error instanceof ApiError ? employee.error.status : 0
    const message = status === 404 ? t('employee.notFound') : status === 403 ? t('employee.forbidden') : t('employee.loadError')
    return <div className={styles.mainError}><Alert tone="danger">{message}</Alert>{status !== 404 && <Button onClick={employee.retry}>{t('common.retry')}</Button>}</div>
  }
  if (!employee.data) return null

  const name = `${employee.data.first_name} ${employee.data.last_name}`
  return <EmployeeDetailContext.Provider value={{ employee: employee.data, employeeId }}>
    <Link className={styles.back} to="/employees/"><ArrowLeft aria-hidden="true" /> {t('common.backToEmployees')}</Link>
    <PageHeader
      title={name}
      meta={<div className={styles.headerMeta}>
        <StatusBadge tone={employee.data.is_active ? 'success' : 'neutral'}>{t(employee.data.is_active ? 'employee.active' : 'employee.inactive')}</StatusBadge>
        {employee.data.current_statuses.map((status) => <StatusBadge key={status.id}>{status.name || status.code}</StatusBadge>)}
      </div>}
    />
    <EmployeeResourceNav employeeId={employeeId} />
    <div className={styles.panel}><Outlet /></div>
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
  const base = `/employees/${employeeId}`
  return <nav aria-label={t('employee.resourceNavigation')} className={styles.resourceNav}>
    <div className={styles.resourceNavScroll} tabIndex={0}>
      {resourceLinks.map((item) => <NavLink
        className={({ isActive }) => `${styles.resourceLink} ${isActive ? styles.resourceLinkActive : ''}`}
        end={item.end}
        key={item.path || 'overview'}
        to={item.path ? `${base}/${item.path}` : base}
      >{t(item.label)}</NavLink>)}
    </div>
  </nav>
}
