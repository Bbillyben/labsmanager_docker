import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './ProjectWorkloadTimeline.module.css'

export type WorkloadPreset = 'year' | 'fiveYears' | 'all'
export type WorkloadTimelineItem = { id: number | string; label: string; detail?: string; quotity: string }
export type WorkloadTimelineSegment = { start: string | null; end: string | null; total_quotity: string; items: WorkloadTimelineItem[] }
export type WorkloadTimelineData = { range: { start: string | null; end: string | null }; segments: WorkloadTimelineSegment[] }
export type WorkloadTimelineCopy = {
  chart: string
  chartDescription: string
  closeDetail: string
  emptyWindow: string
  overload: (value: string) => string
  total: (value: string) => string
}

type Props = {
  copy: WorkloadTimelineCopy
  data: WorkloadTimelineData
  preset: WorkloadPreset
  shifted: boolean
  onPresetChange: (preset: WorkloadPreset) => void
  onPrevious: () => void
  onNext: () => void
  onToday: () => void
}

const WIDTH = 1000
const HEIGHT = 128
const LEFT = 46
const RIGHT = 14
const TOP = 8
const BOTTOM = 24
const DAY = 86_400_000

export function WorkloadTimeline({ copy, data, preset, shifted, onPresetChange, onPrevious, onNext, onToday }: Props) {
  const { language, t } = useTranslation()
  const [selected, setSelected] = useState<WorkloadTimelineSegment | null>(null)
  const [hovered, setHovered] = useState<WorkloadTimelineSegment | null>(null)
  const descriptionId = useId()
  const values = data.segments.map((segment) => Number(segment.total_quotity))
  const observedMaximum = Math.max(0, ...values)
  const verticalMaximum = Math.max(1.25, Math.ceil(observedMaximum * 4) / 4)
  const plotBottom = HEIGHT - BOTTOM
  const plotWidth = WIDTH - LEFT - RIGHT
  const y = (value: number) => plotBottom - (Math.min(value, verticalMaximum) / verticalMaximum) * (plotBottom - TOP)
  const finiteRange = Boolean(data.range.start && data.range.end)
  const rangeStart = data.range.start ? dateValue(data.range.start) : 0
  const rangeEndExclusive = data.range.end ? dateValue(data.range.end) + DAY : 0
  const xForDate = (value: string, end = false) => LEFT + ((dateValue(value) + (end ? DAY : 0) - rangeStart) / (rangeEndExclusive - rangeStart)) * plotWidth
  const positions = data.segments.map((segment, index) => finiteRange && segment.start && segment.end
    ? { x: xForDate(segment.start), width: Math.max(1, xForDate(segment.end, true) - xForDate(segment.start)) }
    : { x: LEFT + (index / Math.max(data.segments.length, 1)) * plotWidth, width: plotWidth / Math.max(data.segments.length, 1) })
  const linePath = positions.map((position, index) => index
    ? `V ${y(values[index] ?? 0)} H ${position.x + position.width}`
    : `M ${position.x} ${y(values[index] ?? 0)} H ${position.x + position.width}`).join(' ')
  const requestedActive = selected ?? hovered
  const active = requestedActive && data.segments.includes(requestedActive) ? requestedActive : null
  const today = new Date()
  const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const todayInRange = finiteRange && todayIso >= data.range.start! && todayIso <= data.range.end!
  const empty = data.segments.length === 0 || data.segments.every((segment) => Number(segment.total_quotity) === 0)

  return <div className={styles.root}>
    <div className={styles.toolbar}>
      <div aria-label={t('workload.period')} className={styles.presets} role="group">
        {(['year', 'fiveYears', 'all'] as const).map((value) => <Button aria-pressed={preset === value} key={value} onClick={() => onPresetChange(value)} size="xs" variant={preset === value ? 'secondary' : 'ghost'}>{t(`workload.${value}`)}</Button>)}
      </div>
      {preset !== 'all' && shifted && <Button className={styles.todayButton} onClick={onToday} size="xs" variant="ghost">{t('workload.today')}</Button>}
    </div>
    <div className={styles.chartFrame}>
      {preset !== 'all' && <button aria-label={t('workload.previous')} className={`${styles.navigation} ${styles.previous}`} onClick={onPrevious} type="button"><ChevronLeft aria-hidden="true" /></button>}
      <svg aria-describedby={descriptionId} aria-label={copy.chart} className={styles.chart} role="group" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
        <line className={styles.gridLine} x1={LEFT} x2={WIDTH - RIGHT} y1={plotBottom} y2={plotBottom} />
        <text className={styles.axisLabel} x={LEFT - 8} y={plotBottom + 3}>0</text>
        <line className={styles.threshold} data-threshold="100" x1={LEFT} x2={WIDTH - RIGHT} y1={y(1)} y2={y(1)} />
        <text className={styles.axisLabel} x={LEFT - 8} y={y(1) + 3}>100 %</text>
        {verticalMaximum > 1.25 && <text className={styles.axisLabel} x={LEFT - 8} y={TOP + 3}>{formatPercent(verticalMaximum, language)}</text>}
        {positions.map((position, index) => {
          const total = values[index] ?? 0
          const normalTop = y(Math.min(total, 1))
          return <g key={`${data.segments[index].start}-${index}`}>
            <rect className={styles.area} height={plotBottom - normalTop} width={position.width} x={position.x} y={normalTop} />
            {total > 1 && <rect aria-label={copy.overload(formatPercent(total - 1, language))} className={styles.overload} data-overload="true" height={y(1) - y(total)} role="img" width={position.width} x={position.x} y={y(total)} />}
          </g>
        })}
        {linePath && <path className={styles.line} d={linePath} />}
        {todayInRange && <g><line className={styles.todayLine} x1={xForDate(todayIso)} x2={xForDate(todayIso)} y1={TOP} y2={plotBottom} /><text className={styles.todayLabel} x={xForDate(todayIso) + 5} y={TOP + 9}>{t('workload.today')}</text></g>}
        {positions.map((position, index) => <rect
          aria-label={`${formatPeriod(data.segments[index], language, t)} — ${copy.total(formatPercent(values[index] ?? 0, language))}`}
          className={styles.hitArea}
          key={`hit-${index}`}
          onBlur={() => setHovered(null)}
          onClick={() => setSelected(data.segments[index])}
          onFocus={() => setHovered(data.segments[index])}
          onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected(data.segments[index]) } }}
          onMouseEnter={() => setHovered(data.segments[index])}
          onMouseLeave={() => setHovered(null)}
          role="button"
          tabIndex={0}
          width={position.width}
          x={position.x}
          y={TOP}
          height={plotBottom - TOP}
        />)}
        <text className={styles.rangeLabel} x={LEFT} y={HEIGHT - 5}>{data.range.start ? formatDate(data.range.start, language) : t('workload.openStart')}</text>
        <text className={styles.rangeLabel} textAnchor="end" x={WIDTH - RIGHT} y={HEIGHT - 5}>{data.range.end ? formatDate(data.range.end, language) : t('workload.openEnd')}</text>
      </svg>
      {preset !== 'all' && <button aria-label={t('workload.next')} className={`${styles.navigation} ${styles.next}`} onClick={onNext} type="button"><ChevronRight aria-hidden="true" /></button>}
    </div>
    <p className={styles.srOnly} id={descriptionId}>{empty ? copy.emptyWindow : copy.chartDescription}</p>
    {empty && <p className={styles.empty}>{copy.emptyWindow}</p>}
    {active && <SegmentDetail copy={copy} onClose={selected === active ? () => setSelected(null) : undefined} segment={active} />}
  </div>
}

function SegmentDetail({ copy, segment, onClose }: { copy: WorkloadTimelineCopy; segment: WorkloadTimelineSegment; onClose?: () => void }) {
  const { language, t } = useTranslation()
  return <div className={styles.detail} role="status">
    <div><strong>{copy.total(formatPercent(Number(segment.total_quotity), language))}</strong><span>{formatPeriod(segment, language, t)}</span></div>
    <ul>{segment.items.map((item) => <li key={item.id}><span>{item.label}{item.detail && <small>{item.detail}</small>}</span><strong>{formatPercent(Number(item.quotity), language)}</strong></li>)}</ul>
    {onClose && <Button aria-label={copy.closeDetail} className={styles.close} onClick={onClose} size="xs" variant="ghost"><X aria-hidden="true" /></Button>}
  </div>
}

type Translator = ReturnType<typeof useTranslation>['t']
function formatPeriod(segment: WorkloadTimelineSegment, language: string, t: Translator) {
  if (segment.start && segment.end) return t('workload.fromTo', { start: formatDate(segment.start, language), end: formatDate(segment.end, language) })
  if (segment.start) return t('workload.since', { date: formatDate(segment.start, language) })
  if (segment.end) return t('workload.until', { date: formatDate(segment.end, language) })
  return t('workload.allTime')
}
function dateValue(value: string) { return new Date(`${value}T00:00:00Z`).getTime() }
function formatDate(value: string, language: string) { return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) }
function formatPercent(value: number, language: string) { return `${new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(value * 100)} %` }
