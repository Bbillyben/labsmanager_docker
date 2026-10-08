import { BriefcaseBusiness, CalendarClock } from 'lucide-react'
import type { DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { isContractData } from './contractData'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './ContractListRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }

export function ContractListRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isContractData(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const { summary } = widget.data
  const items = widget.data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 5 : undefined)
  const locale = language === 'fr' ? 'fr-FR' : 'en-GB'
  const formatDate = (date: string) => new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${date}T00:00:00`))
  return <div className={styles.contracts} data-size={size}>
    <div className={styles.summary}>
      <div className={styles.mainMetric}><BriefcaseBusiness size={18} aria-hidden="true" /><strong>{summary.count}</strong><span>{t('dashboard.contracts.inScope')}</span></div>
      <div className={styles.counters}>
        <span data-tone="warning"><strong>{summary.ending_soon_count}</strong> {t('dashboard.contracts.endingSoon')}</span>
        <span data-tone="danger"><strong>{summary.stale_count}</strong> {t('dashboard.contracts.stale')}</span>
      </div>
    </div>
    {items.length ? <ul className={styles.items}>{items.map((item) => <li key={item.key} className={styles.item} data-state={item.state}>
      <div className={styles.identity}>
        {item.employee_href && mode !== 'print' ? <a href={item.employee_href}>{item.employee_name}</a> : <strong>{item.employee_name}</strong>}
        <span className={styles.state}>{t(`dashboard.contracts.state.${item.state}`)}</span>
      </div>
      {size !== 'compact' && <div className={styles.context}>
        {item.contract_type && <span>{item.contract_type}</span>}
        {item.contract_type && item.project_name && <span aria-hidden="true">·</span>}
        {item.project_href && mode !== 'print' ? <a href={item.project_href}>{item.project_name}</a> : <span>{item.project_name}</span>}
      </div>}
      <div className={styles.date}><CalendarClock size={14} aria-hidden="true" />{item.date
        ? <><time dateTime={item.date}>{formatDate(item.date)}</time><span aria-hidden="true">·</span><span>{item.days_until === null ? '' : item.days_until < 0
          ? t('dashboard.contracts.endedDaysAgo', { count: Math.abs(item.days_until) })
          : item.days_until === 0 ? t('dashboard.contracts.endsToday')
            : t('dashboard.contracts.endsInDays', { count: item.days_until })}</span></>
        : <span>{t('dashboard.contracts.noEndDate')}</span>}</div>
    </li>)}</ul> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
