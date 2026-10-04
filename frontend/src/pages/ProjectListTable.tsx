import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { ProjectItem, ProjectOrdering, ProjectSortField } from '../api/projects'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { ActivityStatusBadge } from '../ui/ActivityStatusBadge'
import { useTranslation } from '../i18n/i18n'
import styles from './EmployeeListPage.module.css'

function CompactList({ values }: { values: string[] }) {
  if (!values.length) return <>—</>
  const shown = values.slice(0, 2).join(', ')
  return <span title={values.join(', ')} aria-label={values.join(', ')} tabIndex={values.length > 2 ? 0 : undefined}>{shown}{values.length > 2 ? ` +${values.length - 2}` : ''}</span>
}

const dateLabel = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : '—'

type Props = {
  projects: ProjectItem[]
  selectedId?: number | null
  onSelect?: (id: number | null) => void
  ordering?: ProjectOrdering
  onSort?: (ordering: ProjectOrdering) => void
  linkState?: object
  renderActions?: (project: ProjectItem) => ReactNode
}

export function ProjectListTable({ projects, selectedId, onSelect, ordering, onSort, linkState, renderActions }: Props) {
  const { t, language } = useTranslation()
  function header(label: string, field: ProjectSortField) {
    return onSort && ordering ? <SortableTableHeader label={label} field={field} ordering={ordering} onSort={onSort} /> : <th scope="col">{label}</th>
  }

  return <div className={styles.scroll} role="region" aria-label={t('project.tableScroll')} tabIndex={0}>
    <table className={styles.table}>
      <caption className={styles.caption}>{t(onSelect ? 'project.tableHelp' : 'project.tableHelpReadOnly')}</caption>
      <thead><tr>{header(t('employee.project'), 'name')}{header(t('project.columnStart'), 'start_date')}{header(t('project.columnEnd'), 'end_date')}<th scope="col">{t('project.institutions')}</th><th scope="col">{t('project.participants')}</th><th scope="col">{t('project.columnFunds')}</th>{header(t('project.columnStatus'), 'status')}{renderActions && <th scope="col"><span className="sr-only">{t('list.menu')}</span></th>}</tr></thead>
      <tbody>{projects.map((project) => {
        const cells = <>
        <th scope="row">{onSelect && <span className={styles.selectionMark} aria-hidden="true">{selectedId === project.id ? '✓' : ''}</span>}<Link to={`/projects/${project.id}`} state={linkState}>{project.name}</Link></th>
        <td className={styles.date}>{dateLabel(project.start_date, language)}</td><td className={styles.date}>{dateLabel(project.end_date, language)}</td>
        <td><CompactList values={project.institutions} /></td><td><CompactList values={project.participants} /></td><td><CompactList values={project.funds} /></td>
        <td><ActivityStatusBadge active={project.status} /></td>
        {renderActions && <td className={styles.actions}>{renderActions(project)}</td>}
        </>
        return onSelect ? <SelectableTableRow key={project.id} id={`project-row-${project.id}`} rowId={project.id} selectedId={selectedId ?? null} onSelect={onSelect}>{cells}</SelectableTableRow> : <tr key={project.id}>{cells}</tr>
      })}</tbody>
    </table>
  </div>
}
