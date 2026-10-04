import type { DashboardSeriesData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }

const colors = ['var(--primary)', 'var(--chart-2, #b17439)', 'var(--chart-3, #5b80ae)', 'var(--chart-4, #9168a4)', 'var(--chart-5, #5e9876)']

export function LineChartRenderer({ widget }: Props) {
  const { t, language } = useTranslation()
  const payload = widget.data as Partial<DashboardSeriesData> | null
  const series = Array.isArray(payload?.series) ? payload.series.filter((item) => Array.isArray(item.points) && item.points.length) : []
  if (!series.length) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const dates = [...new Set(series.flatMap((item) => item.points.map((point) => point.date)))].sort()
  const values = series.flatMap((item) => item.points.map((point) => point.value)).filter(Number.isFinite)
  if (!dates.length || !values.length) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const min = Math.min(0, ...values)
  const max = Math.max(1, ...values)
  const span = max - min || 1
  const left = 68; const top = 12; const width = 550; const height = 190
  const x = (date: string) => left + (dates.length === 1 ? width / 2 : dates.indexOf(date) / (dates.length - 1) * width)
  const y = (value: number) => top + height - (value - min) / span * height
  const format = (value: number) => new Intl.NumberFormat(language === 'fr' ? 'fr-FR' : 'en-GB', { maximumFractionDigits: 0, notation: Math.abs(value) >= 1000000 ? 'compact' : 'standard' }).format(value)
  return <div className="dashboard-line-chart">
    <svg viewBox="0 0 640 240" role="img" aria-label={t('dashboard.chartDescription')} preserveAspectRatio="xMidYMid meet">
      <line x1={left} y1={top} x2={left} y2={top + height} className="dashboard-chart-axis" />
      <line x1={left} y1={top + height} x2={left + width} y2={top + height} className="dashboard-chart-axis" />
      <text x={left - 8} y={top + 6} textAnchor="end" className="dashboard-chart-label">{format(max)}</text>
      <text x={left - 8} y={top + height} textAnchor="end" className="dashboard-chart-label">{format(min)}</text>
      <text x={left} y={top + height + 23} className="dashboard-chart-label">{dates[0].slice(0, 7)}</text>
      <text x={left + width} y={top + height + 23} textAnchor="end" className="dashboard-chart-label">{dates.at(-1)?.slice(0, 7)}</text>
      {series.map((item, index) => {
        const color = item.kind === 'reference' ? 'var(--muted-foreground)' : colors[index % colors.length]
        const points = item.points.filter((point) => Number.isFinite(point.value) && dates.includes(point.date))
        return <g key={item.key}>
          <polyline fill="none" stroke={color} strokeWidth="2.5" strokeDasharray={item.kind === 'reference' ? '6 5' : undefined} points={points.map((point) => `${x(point.date)},${y(point.value)}`).join(' ')} />
          {points.map((point) => <circle key={point.date} cx={x(point.date)} cy={y(point.value)} r="4" fill={color} tabIndex={0}><title>{`${item.label} · ${point.date.slice(0, 7)} · ${format(point.value)}`}</title></circle>)}
        </g>
      })}
    </svg>
    {series.length > 1 && <ul className="dashboard-chart-legend">{series.map((item, index) => <li key={item.key}><span aria-hidden="true" style={{ background: item.kind === 'reference' ? 'var(--muted-foreground)' : colors[index % colors.length] }} />{item.label}</li>)}</ul>}
    <table className="sr-only"><caption>{t('dashboard.chartDescription')}</caption><thead><tr><th>{t('dashboard.chartDate')}</th>{series.map((item) => <th key={item.key}>{item.label}</th>)}</tr></thead><tbody>{dates.map((date) => <tr key={date}><th>{date}</th>{series.map((item) => <td key={item.key}>{item.points.find((point) => point.date === date)?.value ?? '—'}</td>)}</tr>)}</tbody></table>
  </div>
}
