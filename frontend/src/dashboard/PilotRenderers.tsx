import type { DashboardKpiData, DashboardListItem, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import type { DashboardSize } from './size'
import { genericInfoIcon } from '../pages/genericInfoIcons'
import type { DashboardMode } from './mode'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
const itemsFor = (data: unknown): DashboardListItem[] => {
  if (!data || typeof data !== 'object' || !('items' in data) || !Array.isArray(data.items)) return []
  return data.items.filter((item): item is DashboardListItem => Boolean(item && typeof item.key === 'string' && typeof item.label === 'string'))
}
const progressPercent = (item: DashboardListItem) => item.percent ?? (item.total && item.current !== undefined ? item.current / item.total * 100 : 0)
function List({ widget, size, mode, variant }: Props & { variant: 'compact' | 'alert' | 'progress' }) {
  const { t, language } = useTranslation()
  const items = itemsFor(widget.data).slice(0, mode === 'print' ? undefined : size === 'compact' ? 3 : size === 'standard' ? 6 : 12)
  if (!items.length) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const formatDate = (value?: string) => {
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return value
    const date = new Date(`${value}T00:00:00`)
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(language === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'short' }).format(date)
  }
  const severityLabel = (value?: string) => value === 'danger' ? t('dashboard.severity.danger') : value === 'warning' ? t('dashboard.severity.warning') : value === 'info' ? t('dashboard.severity.info') : value
  return <ul className={`dashboard-list dashboard-list-${variant}`}>{items.map((item) => <li key={item.key} data-tone={variant === 'alert' ? item.severity : item.tone}>
    <div className="dashboard-list-main"><span className="dashboard-list-label">{item.icon && size !== 'compact' && (() => { const Icon = genericInfoIcon(item.icon); return <Icon size={15} aria-hidden="true" /> })()}{item.href ? <a href={item.href}>{item.label}</a> : <span>{item.label}</span>}</span>{variant === 'alert' && item.severity && <small>{severityLabel(item.severity)}</small>}</div>
    {size !== 'compact' && (item.secondary || item.date || item.status) && <small className="muted-text">{[item.secondary, formatDate(item.date), item.status].filter(Boolean).join(' · ')}</small>}
    {variant === 'progress' && <div className="dashboard-progress"><progress value={Math.min(100, Math.max(0, progressPercent(item)))} max={100} aria-label={item.label} /><small>{size !== 'compact' && item.current !== undefined && item.total !== undefined ? `${new Intl.NumberFormat(language).format(item.current)} / ${new Intl.NumberFormat(language).format(item.total)} · ` : ''}{Math.round(progressPercent(item))} %</small></div>}
  </li>)}</ul>
}
export function KpiRenderer({ widget, size }: Props) {
  const { t } = useTranslation()
  const data = widget.data && typeof widget.data === 'object' ? widget.data as Partial<DashboardKpiData> : {}
  const ratio = typeof data.centered_ratio === 'number' && Number.isFinite(data.centered_ratio) ? data.centered_ratio : null
  return <div className="dashboard-kpi-content" data-tone={data.tone}>
    <strong className="dashboard-kpi">{data.value ?? '—'}</strong>
    {data.label && <span>{data.label}</span>}
    {ratio !== null && <div className="dashboard-centered-ratio" role="img" aria-label={t('dashboard.ratioDescription', { value: String(data.value) })} title={t('dashboard.advancementHelp')}><span className="dashboard-centered-ratio-center" /><span className="dashboard-centered-ratio-marker" style={{ left: `${Math.max(0, Math.min(100, ratio / 2 * 100))}%` }} /><span className="dashboard-centered-ratio-min">0</span><span className="dashboard-centered-ratio-target">1</span><span className="dashboard-centered-ratio-max">2+</span></div>}
    {ratio !== null && <small>{t('dashboard.budgetConsumed')}: {Math.round(data.budget_percent ?? 0)} % · {t('dashboard.timeElapsed')}: {Math.round(data.time_percent ?? 0)} %</small>}
    {typeof data.progress_percent === 'number' && <progress value={Math.max(0, Math.min(100, data.progress_percent))} max={100} aria-label={data.label} />}
    {size !== 'compact' && data.context && <small>{data.context}</small>}{size === 'expanded' && data.secondary && <small>{data.secondary}</small>}
  </div>
}
export function CompactListRenderer(props: Props) { return <List {...props} variant="compact" /> }
export function AlertListRenderer(props: Props) { return <List {...props} variant="alert" /> }
export function ProgressListRenderer(props: Props) { return <List {...props} variant="progress" /> }
export function EmptyRenderer({ widget }: Props) {
  const { t } = useTranslation()
  const message = (widget.data as { message?: string } | null)?.message
  return <p className="muted-text">{message || t('dashboard.emptyWidget')}</p>
}
