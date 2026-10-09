import { CalendarClock, Diamond, FileClock, Gauge, ListChecks, WalletCards } from 'lucide-react'
import type { DashboardProjectHealthBarsData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { RatioGauge, RoundedProgressGauge, VerticalStackedMetric } from './DashboardGraphics'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './ProjectHealthBarsRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
type Relative = DashboardProjectHealthBarsData['items'][number]['deadline']['relative']

export function ProjectHealthBarsRenderer({ widget, size, mode = 'view' }: Props) {
  const { t } = useTranslation()
  const data = widget.data as DashboardProjectHealthBarsData | null
  if (!data || !Array.isArray(data.items)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const full = size === 'expanded' || mode === 'print'
  const items = data.items
  const percent = (value: number | null) => value === null ? '—' : `${Math.round(value)}%`
  const relativeText = (relative: Relative) => {
    if (relative.state === 'unknown') return t('dashboard.health.deadlineUnknown')
    if (relative.state === 'ends_today') return t('dashboard.health.endsToday')
    if (relative.state === 'starts_in') return t('dashboard.health.startsInDays', { count: relative.count ?? 0 })
    if (relative.state === 'ended_ago') return t('dashboard.health.endedDaysAgo', { count: relative.count ?? 0 })
    return relative.unit === 'months' ? t('dashboard.health.endsInMonths', { count: relative.count ?? 0 })
      : t('dashboard.health.endsInDays', { count: relative.count ?? 0 })
  }
  return <div className={styles.health} data-size={size}>
    {items.length ? <ul className={styles.items}>{items.map((item) => <li key={item.key} className={styles.item}>
      <div className={styles.heading}>
        {mode === 'print' ? <strong>{item.name}</strong> : <a href={item.href}>{item.name}</a>}
        <span data-state={item.deadline.state}>{t(`dashboard.portfolio.state.${item.deadline.state}`)}</span>
      </div>
      <div className={styles.verticals}>
        <VerticalStackedMetric label={t('dashboard.health.milestones')} icon={<Diamond size={15} aria-hidden="true" />}
          total={item.milestones.total} summary={t('dashboard.health.overdue', { count: item.milestones.overdue_count })}
          showLegend={full} segments={[
            { key: 'upcoming', value: item.milestones.upcoming_count, tone: 'success', label: t('dashboard.health.upcoming') },
            { key: 'imminent', value: item.milestones.imminent_count, tone: 'info', label: t('dashboard.health.imminent') },
            { key: 'overdue', value: item.milestones.overdue_count, tone: 'danger', label: t('dashboard.health.overdueLabel') },
            { key: 'unscheduled', value: item.milestones.unscheduled_count, tone: 'muted', label: t('dashboard.health.unscheduled') },
          ]} />
        <VerticalStackedMetric label={t('dashboard.health.tasks')} icon={<ListChecks size={15} aria-hidden="true" />}
          total={item.tasks.total} summary={t('dashboard.health.overdue', { count: item.tasks.overdue_count })}
          showLegend={full} segments={[
            { key: 'upcoming', value: item.tasks.upcoming_count, tone: 'success', label: t('dashboard.health.upcoming') },
            { key: 'imminent', value: item.tasks.imminent_count, tone: 'info', label: t('dashboard.health.imminent') },
            { key: 'overdue', value: item.tasks.overdue_count, tone: 'danger', label: t('dashboard.health.overdueLabel') },
            { key: 'unscheduled', value: item.tasks.unscheduled_count, tone: 'muted', label: t('dashboard.health.unscheduled') },
          ]} />
        <VerticalStackedMetric label={t('dashboard.health.contracts')} icon={<FileClock size={15} aria-hidden="true" />}
          total={item.contracts.total} summary={size === 'compact' && mode !== 'print'
            ? t('dashboard.health.hrAttention', { count: item.contracts.expired_rh_active_count })
            : t('dashboard.health.contractSummary', { soon: item.contracts.ending_soon_count, attention: item.contracts.expired_rh_active_count })}
          showLegend={full} segments={[
            { key: 'active', value: item.contracts.active_count, tone: 'success', label: t('dashboard.health.hrCurrent') },
            { key: 'ending', value: item.contracts.ending_soon_count, tone: 'info', label: t('dashboard.health.endingSoon') },
            { key: 'expired', value: item.contracts.expired_rh_active_count, tone: 'danger', label: t('dashboard.health.expiredRhActive') },
          ]} />
      </div>
      <div className={styles.gauges}>
        <RoundedProgressGauge label={t('dashboard.health.funding')} icon={<WalletCards size={14} aria-hidden="true" />}
          value={item.funding?.percent ?? null} displayValue={percent(item.funding?.percent ?? null)}
          tone={item.funding?.tone ?? 'muted'} secondary={full && item.funding
            ? t('dashboard.health.fundingAmounts', { spent: item.funding.spent, amount: item.funding.amount }) : undefined} />
        <RoundedProgressGauge label={t('dashboard.health.deadline')} icon={<CalendarClock size={14} aria-hidden="true" />}
          value={item.deadline.percent} displayValue={percent(item.deadline.percent)} tone={item.deadline.tone}
          secondary={relativeText(item.deadline.relative)} />
        <div className={styles.pace}>
          <Gauge size={14} aria-hidden="true" />
          <RatioGauge label={t('dashboard.health.pace')} value={item.funding_pace.ratio} target={1} domain={[0, 2]}
            displayValue={item.funding_pace.ratio === null ? '—' : item.funding_pace.ratio.toFixed(2)}
            targetLabel={t('dashboard.health.target')} leftLabel="0" rightLabel="2+" tone={item.funding_pace.tone}
            secondary={t(`dashboard.health.paceState.${item.funding_pace.state}`)} />
        </div>
      </div>
    </li>)}</ul> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
