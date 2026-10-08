import { CalendarDays, UserRound, UserRoundMinus, UserRoundPlus, UsersRound } from 'lucide-react'
import type { DashboardEmployeeMovementsData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { isEmployeeMovements } from './employeeMovementData'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import styles from './EmployeeMovementsRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
type Item = DashboardEmployeeMovementsData['items'][number]

const movementIcon = (state: Item['state']) => state === 'arriving' || state === 'arrived_recently'
  ? UserRoundPlus : state === 'leaving' || state === 'departed' ? UserRoundMinus : UserRound

export function EmployeeMovementsRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isEmployeeMovements(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const { summary } = widget.data
  const items = widget.data.items.slice(0, mode === 'print' ? undefined : size === 'compact' ? 2 : size === 'standard' ? 5 : undefined)
  const locale = language === 'fr' ? 'fr-FR' : 'en-GB'
  const formatDate = (date: string) => new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', ...(size === 'expanded' || mode === 'print' ? { year: 'numeric' } : {}) }).format(new Date(`${date}T00:00:00`))
  const relative = (item: Item) => {
    if (item.days_until === null) return null
    if (item.days_until === 0) return t('dashboard.employees.today')
    if (item.days_until > 0) return t('dashboard.employees.inDays', { count: item.days_until })
    return t('dashboard.employees.daysAgo', { count: Math.abs(item.days_until) })
  }
  return <div className={styles.movements} data-size={size}>
    <div className={styles.summary}>
      <div className={styles.mainMetric}><UsersRound size={19} aria-hidden="true" /><strong>{summary.count}</strong><span>{t('dashboard.employees.inScope')}</span></div>
      <div className={styles.counters}>
        <span data-tone="success"><strong>{summary.arrivals_count}</strong> {t('dashboard.employees.arrivals')}</span>
        <span data-tone="warning"><strong>{summary.departures_count}</strong> {t('dashboard.employees.departures')}</span>
      </div>
    </div>
    {items.length ? <ul className={styles.items}>{items.map((item) => {
      const Icon = movementIcon(item.state)
      return <li key={item.key} className={styles.item} data-state={item.state}>
        <span className={styles.icon}><Icon size={17} aria-hidden="true" /></span>
        <div className={styles.content}>
          <div className={styles.heading}>
            {mode === 'print' ? <strong>{item.name}</strong> : <a href={item.href}>{item.name}</a>}
            <span className={styles.state}>{t(`dashboard.employees.state.${item.state}`)}</span>
          </div>
          {size !== 'compact' && (item.role || item.team_name) && <div className={styles.context}>
            {item.role && <span>{item.role}</span>}
            {item.role && item.team_name && <span aria-hidden="true">·</span>}
            {item.team_name && (item.team_href && mode !== 'print' ? <a href={item.team_href}>{item.team_name}</a> : <span>{item.team_name}</span>)}
          </div>}
          {item.date && <div className={styles.date}><CalendarDays size={13} aria-hidden="true" />
            <span>{t(item.state === 'arriving' || item.state === 'arrived_recently' ? 'dashboard.employees.arrival' : 'dashboard.employees.departure')}</span>
            <time dateTime={item.date}>{formatDate(item.date)}</time>
            <span aria-hidden="true">·</span><span>{relative(item)}</span>
          </div>}
        </div>
      </li>
    })}</ul> : <p className="muted-text">{t('dashboard.emptyWidget')}</p>}
  </div>
}
