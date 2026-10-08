import type { DashboardProjectPortfolioData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './ProjectPortfolioRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
const bounded = (value: number | null) => Math.max(0, Math.min(100, value ?? 0))

export function ProjectPortfolioRenderer({ widget, size, mode = 'view' }: Props) {
  const { t } = useTranslation()
  const data = widget.data as DashboardProjectPortfolioData | null
  if (!data || !data.summary || !Array.isArray(data.items)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const items = data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 4 : undefined)
  const percent = (value: number | null) => value === null ? '—' : `${Math.round(value)}%`
  return <div className={styles.portfolio} data-size={size}>
    <div className={styles.summary}>
      <strong>{data.summary.count}</strong><span>{t('dashboard.portfolio.projects')}</span>
      <span>{data.summary.active_count} {t('dashboard.portfolio.active')}</span>
      <span>{data.summary.ending_soon_count} {t('dashboard.portfolio.endingSoon')}</span>
      <span>{data.summary.attention_count} {t('dashboard.portfolio.attention')}</span>
    </div>
    {items.length ? <ul className={styles.items}>{items.map((item) => <li key={item.key} className={styles.item}>
      <div className={styles.heading}>{mode === 'print' ? <strong>{item.name}</strong> : <a href={item.href}>{item.name}</a>}
        <span>{t(`dashboard.portfolio.state.${item.temporal_state}`)}</span></div>
      <div className={styles.progressRow}><span>{t('dashboard.portfolio.time')}</span><progress value={bounded(item.temporal_percent)} max={100} aria-label={t('dashboard.portfolio.timeFor', { name: item.name })} /><strong>{percent(item.temporal_percent)}</strong></div>
      <div className={styles.progressRow}><span>{t('dashboard.portfolio.financial')}</span><progress value={bounded(item.financial?.percent ?? null)} max={100} aria-label={t('dashboard.portfolio.financialFor', { name: item.name })} /><strong>{percent(item.financial?.percent ?? null)}</strong></div>
      {size !== 'compact' && item.next_milestone && <p className={styles.next}>{t('dashboard.portfolio.nextMilestone')}: {mode === 'print' ? item.next_milestone.title : <a href={item.next_milestone.href}>{item.next_milestone.title}</a>} · {item.next_milestone.days_until === 0 ? t('dashboard.timeline.today') : t('dashboard.portfolio.inDays', { count: item.next_milestone.days_until })}</p>}
      {item.overdue_task_count > 0 && <p className={styles.warning}>{t('dashboard.portfolio.overdueTasks', { count: item.overdue_task_count })}</p>}
      {size === 'expanded' && item.attention_signals.length > 0 && <div className={styles.signals}>{item.attention_signals.map((signal) => <span key={signal}>{signal === 'overdue_tasks' ? t('dashboard.portfolio.signal.overdueTasks') : signal === 'overdue_milestones' ? t('dashboard.portfolio.signal.overdueMilestones') : signal === 'project_ending_soon' ? t('dashboard.portfolio.signal.endingSoon') : t('dashboard.portfolio.signal.ended')}</span>)}</div>}
    </li>)}</ul> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
