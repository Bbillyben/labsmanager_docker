import type { DashboardDeadlineData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { isDeadline } from './deadlineData'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './DeadlineListRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }

export function DeadlineListRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isDeadline(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const { summary } = widget.data
  const items = widget.data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 5 : undefined)
  const locale = language === 'fr' ? 'fr-FR' : 'en-GB'
  const formatDate = (date: string | null) => {
    if (!date) return t('dashboard.deadline.noDate')
    const value = new Date(`${date}T00:00:00`)
    return Number.isNaN(value.getTime()) ? date : new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', ...(size === 'expanded' || mode === 'print' ? { year: 'numeric' } : {}) }).format(value)
  }
  const relative = (item: DashboardDeadlineData['items'][number]) => {
    switch (item.state) {
      case 'overdue': return t('dashboard.deadline.overdueBy', { count: Math.abs(item.days_until ?? 0) })
      case 'today': return t('dashboard.deadline.today')
      case 'due_soon': case 'upcoming': return t('dashboard.deadline.inDays', { count: item.days_until ?? 0 })
      case 'completed': return t('dashboard.deadline.completed')
      case 'unscheduled': return t('dashboard.deadline.noDate')
    }
  }
  return <div className={styles.timeline} data-size={size}>
    <div className={styles.summary}>
      <div className={styles.mainMetric}><strong>{summary.count}</strong><span>{t('dashboard.deadline.inScope')}</span></div>
      <div className={styles.counters}>
        <span data-tone="danger"><strong>{summary.overdue_count}</strong> {t('dashboard.deadline.overdue')}</span>
        <span data-tone="warning"><strong>{summary.due_soon_count}</strong> {t('dashboard.deadline.dueSoon')}</span>
      </div>
    </div>
    {items.length ? <ol className={styles.items}>{items.map((item) => <li key={item.key} className={styles.item} data-state={item.state}>
      <div className={styles.date}>{item.date ? <time dateTime={item.date}>{formatDate(item.date)}</time> : formatDate(null)}</div>
      <div className={styles.detail}>
        {item.href && mode !== 'print' ? <a href={item.href}>{item.label}</a> : <strong>{item.label}</strong>}
        {size !== 'compact' && <span className={styles.project}>{item.project_name}</span>}
        <span className={styles.relative}>{relative(item)}</span>
      </div>
    </li>)}</ol> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
