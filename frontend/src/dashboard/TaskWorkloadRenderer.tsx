import { CalendarClock, CircleAlert, ListTodo, UserRound } from 'lucide-react'
import type { DashboardTaskWorkloadData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { isTaskWorkload } from './taskWorkloadData'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './TaskWorkloadRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
type Item = DashboardTaskWorkloadData['items'][number]

export function TaskWorkloadRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isTaskWorkload(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const { summary } = widget.data
  const items = widget.data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 5 : undefined)
  const locale = language === 'fr' ? 'fr-FR' : 'en-GB'
  const formatDate = (date: string) => new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', ...(size === 'expanded' || mode === 'print' ? { year: 'numeric' } : {}) }).format(new Date(`${date}T00:00:00`))
  const relative = (item: Item) => {
    if (item.state === 'done') return t('dashboard.tasks.state.done')
    if (item.state === 'unscheduled') return t('dashboard.tasks.state.unscheduled')
    if (item.state === 'overdue') return t('dashboard.tasks.overdueBy', { count: Math.abs(item.days_until ?? 0) })
    if (item.state === 'today') return t('dashboard.tasks.dueToday')
    if (item.days_until === 1) return t('dashboard.tasks.dueTomorrow')
    return t('dashboard.tasks.inDays', { count: item.days_until ?? 0 })
  }
  return <div className={styles.workload} data-size={size}>
    <div className={styles.summary}>
      <div className={styles.mainMetric}><ListTodo size={19} aria-hidden="true" /><strong>{summary.count}</strong><span>{t('dashboard.tasks.inScope')}</span></div>
      <div className={styles.counters}>
        <span data-tone="danger"><strong>{summary.overdue_count}</strong> {t('dashboard.tasks.overdue')}</span>
        <span data-tone="warning"><strong>{summary.due_soon_count}</strong> {t('dashboard.tasks.dueSoon')}</span>
      </div>
    </div>
    {items.length ? <ol className={styles.items}>{items.map((item) => <li key={item.key} className={styles.item} data-state={item.state}>
      <span className={styles.marker}>{item.state === 'overdue' || item.state === 'today' ? <CircleAlert size={16} aria-hidden="true" /> : <ListTodo size={16} aria-hidden="true" />}</span>
      <div className={styles.content}>
        <div className={styles.heading}>
          {mode === 'print' ? <strong>{item.title}</strong> : <a href={item.href}>{item.title}</a>}
          <span className={styles.state}>{t(`dashboard.tasks.state.${item.state}`)}</span>
        </div>
        {size !== 'compact' && <div className={styles.project}>{mode === 'print' ? <span>{item.project_name}</span> : <a href={item.project_href}>{item.project_name}</a>}</div>}
        <div className={styles.meta}>
          {size !== 'compact' && item.assignees.length > 0 && <span className={styles.assignees}><UserRound size={13} aria-hidden="true" />{item.assignees.map((employee, index) => <span key={employee.id}>{index > 0 && <span aria-hidden="true">, </span>}{employee.href && mode !== 'print' ? <a href={employee.href}>{employee.name}</a> : employee.name}</span>)}</span>}
          {item.date && <span className={styles.date}><CalendarClock size={13} aria-hidden="true" /><time dateTime={item.date}>{formatDate(item.date)}</time></span>}
          <span className={styles.relative}>{relative(item)}</span>
        </div>
      </div>
    </li>)}</ol> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
