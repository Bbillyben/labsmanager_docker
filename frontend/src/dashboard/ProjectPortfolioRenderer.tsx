import { CalendarClock, CircleAlert, CircleCheck, TrendingDown, TrendingUp } from 'lucide-react'
import type { DashboardProjectPortfolioData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { RoundedProgressGauge } from './DashboardGraphics'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './ProjectPortfolioRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
type Signal = DashboardProjectPortfolioData['items'][number]['attention_signals'][number]

export function ProjectPortfolioRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  const data = widget.data as DashboardProjectPortfolioData | null
  if (!data || !data.summary || !Array.isArray(data.items)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const full = size === 'expanded' || mode === 'print'
  const items = data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 4 : undefined)
  const percent = (value: number | null) => value === null ? '—' : `${Math.round(value)}%`
  const formatDate = (date: string) => new Intl.DateTimeFormat(language === 'fr' ? 'fr-FR' : 'en-GB', {
    day: 'numeric', month: 'short', ...(full ? { year: 'numeric' } : {}),
  }).format(new Date(`${date}T00:00:00`))
  const signalLabel = (signal: Signal) => {
    if (signal.key === 'overdue_tasks') return t(signal.count === 1 ? 'dashboard.portfolio.overdueTask' : 'dashboard.portfolio.overdueTasks', { count: signal.count ?? 0 })
    if (signal.key === 'overdue_milestones') return t(signal.count === 1 ? 'dashboard.portfolio.overdueMilestone' : 'dashboard.portfolio.overdueMilestones', { count: signal.count ?? 0 })
    if (signal.key === 'project_ending_soon') return t('dashboard.portfolio.signal.endingSoon')
    return t('dashboard.portfolio.signal.ended')
  }
  return <div className={styles.portfolio} data-size={size}>
    <div className={styles.summary}>
      <strong>{data.summary.count}</strong><span>{t('dashboard.portfolio.projects')}</span>
      <span>{data.summary.active_count} {t('dashboard.portfolio.active')}</span>
      <span>{data.summary.ending_soon_count} {t('dashboard.portfolio.endingSoon')}</span>
      <span data-tone="warning">{data.summary.attention_count} {t('dashboard.portfolio.attention')}</span>
    </div>
    {items.length ? <ul className={styles.items}>{items.map((item) => {
      const signals = item.attention_signals.filter((signal) => signal.key !== 'funding_ahead' && signal.key !== 'funding_behind')
      const shownSignals = full ? signals : signals.slice(0, size === 'compact' ? 1 : 2)
      return <li key={item.key} className={styles.item}>
        <div className={styles.heading}>{mode === 'print' ? <strong>{item.name}</strong> : <a href={item.href}>{item.name}</a>}
          <span data-state={item.temporal_state}>{t(`dashboard.portfolio.state.${item.temporal_state}`)}</span></div>
        <RoundedProgressGauge label={t('dashboard.portfolio.time')} ariaLabel={t('dashboard.portfolio.timeFor', { name: item.name })}
          value={item.temporal_percent} displayValue={percent(item.temporal_percent)} className={styles.progressGauge} />
        <RoundedProgressGauge label={t('dashboard.portfolio.financial')} ariaLabel={t('dashboard.portfolio.financialFor', { name: item.name })}
          value={item.financial?.percent ?? null} displayValue={percent(item.financial?.percent ?? null)} className={styles.progressGauge} />
        {item.financial_state && <div className={styles.financialState} data-tone={item.financial_state.tone}>
          {item.financial_state.key === 'funding_ahead' ? <TrendingUp size={14} aria-hidden="true" /> : item.financial_state.key === 'funding_behind' ? <TrendingDown size={14} aria-hidden="true" /> : <CircleCheck size={14} aria-hidden="true" />}
          <span>{t(`dashboard.portfolio.financialState.${item.financial_state.key}`)}</span>
          {full && item.financial_delta !== null && <strong>{t('dashboard.portfolio.deltaPoints', { count: item.financial_delta > 0 ? `+${item.financial_delta}` : item.financial_delta })}</strong>}
        </div>}
        {shownSignals.length > 0 && <div className={styles.signals}>{shownSignals.map((signal) => <span key={signal.key} data-tone={signal.tone}>
          <CircleAlert size={13} aria-hidden="true" />{signalLabel(signal)}
        </span>)}</div>}
        {(size !== 'compact' || mode === 'print') && item.next_milestone && <div className={styles.next}>
          <CalendarClock size={14} aria-hidden="true" /><span>{t('dashboard.portfolio.nextMilestone')}:</span>
          {mode === 'print' ? <strong>{item.next_milestone.title}</strong> : <a href={item.next_milestone.href}>{item.next_milestone.title}</a>}
          <time dateTime={item.next_milestone.date}>{formatDate(item.next_milestone.date)}</time>
          <span>{item.next_milestone.relative_state === 'today' ? t('dashboard.timeline.today') : t('dashboard.portfolio.inDays', { count: item.next_milestone.days_until })}</span>
        </div>}
      </li>
    })}</ul> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
