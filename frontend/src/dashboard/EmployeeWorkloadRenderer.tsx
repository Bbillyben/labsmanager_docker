import type { DashboardEmployeeWorkloadData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './EmployeeWorkloadRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
type Bar = { key: string; label: string; value: number }

export function EmployeeWorkloadRenderer({ widget, size, mode = 'view' }: Props) {
  const { t } = useTranslation()
  const metricLabel = (key: string) => key === 'project_allocation' ? t('dashboard.workload.metric.project_allocation')
    : key === 'open_tasks' ? t('dashboard.workload.metric.open_tasks')
      : key === 'open_milestones' ? t('dashboard.workload.metric.open_milestones') : t('dashboard.workload.metric.open_work_items')
  const data = widget.data as DashboardEmployeeWorkloadData | null
  if (!data || !('mode' in data) || !['single', 'comparison'].includes(data.mode)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const single = data.mode === 'single'
  const metric = single ? null : data.metric
  const bars: Bar[] = single ? data.metrics.map((item) => ({ key: item.key, label: metricLabel(item.key), value: item.value }))
    : data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 4 : size === 'standard' ? 8 : undefined).map((item) => ({ key: String(item.employee_id), label: item.employee_name, value: item.value }))
  const unit = single ? null : data.unit
  const max = single ? Math.max(1, ...data.metrics.filter((item) => item.unit === 'count').map((item) => item.value))
    : Math.max(1, data.reference_value ?? 0, ...bars.map((bar) => bar.value))
  const display = (value: number, kind: 'percent' | 'count') => kind === 'percent' ? `${value}%` : String(value)
  return <div className={styles.workload} data-size={size} data-mode={data.mode}>
    {single ? <p className={styles.title}>{mode === 'print' ? data.employee.name : <a href={data.employee.href}>{data.employee.name}</a>}</p>
      : <p className={styles.title}>{metricLabel(metric ?? 'project_allocation')}</p>}
    <div className={styles.scroll}><div className={styles.bars}>
      {bars.map((bar) => {
        const item = single ? data.metrics.find((entry) => entry.key === bar.key)! : null
        const kind = item?.unit ?? unit ?? 'count'
        const barMax = single && kind === 'percent' ? Math.max(100, bar.value) : max
        const height = barMax > 0 ? Math.max(0, Math.min(100, bar.value / barMax * 100)) : 0
        const reference = kind === 'percent' ? 100 / barMax * 100 : null
        return <div key={bar.key} className={styles.column}>
          <strong>{display(bar.value, kind)}</strong>
          <div className={styles.track}>
            {reference !== null && <span className={styles.reference} style={{ bottom: `${reference}%` }} aria-label={t('dashboard.workload.reference')} />}
            <span className={styles.bar} style={{ height: `${height}%` }} role="img" aria-label={`${bar.label}: ${display(bar.value, kind)}`} />
          </div>
          {single || mode === 'print' ? <span className={styles.label}>{bar.label}</span> : <a className={styles.label} href={data.items.find((row) => String(row.employee_id) === bar.key)?.href}>{bar.label}</a>}
        </div>
      })}
    </div></div>
    {!bars.length && <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
