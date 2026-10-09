import type { ReactNode } from 'react'
import styles from './DashboardGraphics.module.css'

export type GraphicTone = 'neutral' | 'muted' | 'success' | 'info' | 'warning' | 'danger'

export function RoundedProgressGauge({ label, ariaLabel, value, max = 100, displayValue, tone = 'neutral', secondary, icon,
  showLabel = true, showValue = true, className }: {
  label: string; ariaLabel?: string; value: number | null; max?: number; displayValue: string; tone?: GraphicTone
  secondary?: string; icon?: ReactNode; showLabel?: boolean; showValue?: boolean; className?: string
}) {
  const bounded = Math.max(0, Math.min(max, value ?? 0))
  return <div className={`${styles.progressGauge} ${className ?? ''}`} data-tone={tone}>
    {(showLabel || showValue) && <div className={styles.progressHeading}>
      {showLabel && <span>{icon}{label}</span>}{showValue && <strong>{displayValue}</strong>}
    </div>}
    <progress value={bounded} max={max} aria-label={ariaLabel ?? label} aria-valuetext={displayValue} />
    {secondary && <small>{secondary}</small>}
  </div>
}

export type MetricSegment = { key: string; value: number; tone: GraphicTone; label: string }

export function VerticalStackedMetric({ label, icon, segments, total, summary, showLegend = false }: {
  label: string; icon?: ReactNode; segments: MetricSegment[]; total: number; summary?: string; showLegend?: boolean
}) {
  const description = `${total} ${label}: ${segments.map((segment) => `${segment.value} ${segment.label}`).join(', ')}`
  return <div className={styles.verticalMetric}>
    <div className={styles.verticalHeading}>{icon}<span>{label}</span></div>
    <div className={styles.stack} role="img" aria-label={description}>
      {segments.filter((segment) => segment.value > 0).map((segment) => <span key={segment.key} data-tone={segment.tone}
        style={{ height: `${total > 0 ? segment.value / total * 100 : 0}%` }} />)}
    </div>
    <strong>{total}</strong>{summary && <small>{summary}</small>}
    {showLegend && <div className={styles.legend}>{segments.map((segment) => <span key={segment.key} data-tone={segment.tone}>
      <i aria-hidden="true" />{segment.value} {segment.label}
    </span>)}</div>}
  </div>
}

export function RatioGauge({ label, value, target, domain, displayValue, targetLabel, tone = 'neutral',
  secondary, leftLabel, rightLabel }: {
  label: string; value: number | null; target: number; domain: [number, number]; displayValue: string
  targetLabel: string; tone?: GraphicTone; secondary?: string; leftLabel: string; rightLabel: string
}) {
  const position = (point: number) => Math.max(0, Math.min(100, (point - domain[0]) / (domain[1] - domain[0]) * 100))
  return <div className={styles.ratioGauge} data-tone={tone}>
    <div className={styles.ratioHeading}><span>{label}</span><strong>{displayValue}</strong></div>
    <div className={styles.ratioTrack} role="img" aria-label={`${label}: ${displayValue}; ${targetLabel}: ${target}`}>
      <span className={styles.ratioTarget} style={{ left: `${position(target)}%` }} />
      {value !== null && <span className={styles.ratioMarker} style={{ left: `${position(value)}%` }} />}
    </div>
    <div className={styles.ratioScale}><span>{leftLabel}</span><span>{targetLabel}</span><span>{rightLabel}</span></div>
    {secondary && <small>{secondary}</small>}
  </div>
}
