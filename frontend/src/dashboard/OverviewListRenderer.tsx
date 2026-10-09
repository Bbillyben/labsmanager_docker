import type { DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { RoundedProgressGauge } from './DashboardGraphics'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import { isOverview } from './overviewData'
import styles from './OverviewListRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }

export function OverviewListRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isOverview(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const { summary } = widget.data
  const items = widget.data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 3 : undefined)
  const number = new Intl.NumberFormat(language === 'fr' ? 'fr-FR' : 'en-GB', { maximumFractionDigits: 1, notation: 'compact' })
  const amount = (value: number) => number.format(value)
  const percent = (value: number | null) => value === null ? '—' : `${Math.round(value)} %`
  return <div className={styles.overview} data-size={size}>
    <div className={styles.metrics}>
      <div className={styles.primaryMetric}><strong>{amount(summary.amount)}</strong><span>{t('dashboard.overview.total')}</span></div>
      <div className={styles.metric}><strong>{percent(summary.percent)}</strong><span>{t('dashboard.overview.consumed')}</span></div>
      {size !== 'compact' && <div className={styles.metric}><strong>{summary.count}</strong><span>{summary.count_label}</span></div>}
    </div>
    {size !== 'compact' && <RoundedProgressGauge label={t('dashboard.overview.overallProgress')}
      value={summary.percent} displayValue={percent(summary.percent)} showLabel={false} showValue={false} />}
    {items.length ? <ul className={styles.items}>{items.map((item) => <li className={styles.item} key={item.key}>
      <div className={styles.itemHeading}>
        {item.href && mode !== 'print' ? <a href={item.href}>{item.label}</a> : <span>{item.label}</span>}
        <strong>{percent(item.percent)}</strong>
      </div>
      {size === 'expanded' && item.secondary && <small className={styles.secondary}>{item.secondary}</small>}
      <div className={styles.itemDetails}>
        {size !== 'compact' && <span>{amount(item.current)} / {amount(item.total)}</span>}
        <RoundedProgressGauge label={t('dashboard.overview.itemProgress', { name: item.label })}
          value={item.percent} displayValue={percent(item.percent)} showLabel={false} showValue={false}
          className={styles.itemGauge} />
        {size !== 'compact' && item.remaining_days !== null && <span className={styles.deadline}>{item.remaining_days < 0
          ? t('dashboard.overview.expired')
          : t('dashboard.overview.daysRemaining', { count: item.remaining_days })}</span>}
      </div>
      {size !== 'compact' && item.status !== 'normal' && <span className={styles.status} data-status={item.status}>{item.status === 'expired' ? t('dashboard.overview.expired') : t('dashboard.overview.soon')}</span>}
    </li>)}</ul> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
    {size !== 'compact' && summary.attention_count > 0 && <p className={styles.footer}>{t('dashboard.overview.attention', { count: summary.attention_count })}</p>}
  </div>
}
