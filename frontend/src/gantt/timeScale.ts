export type GanttMonths = 6 | 12 | 24 | 60 | 120
export type GanttScale = { unit: 'year' | 'month' | 'week' | 'quarter'; step: number; format: (value: Date) => string }

/** The same two-level scale feeds SVAR and the static print axis. */
export function ganttScales(months: GanttMonths, language: string): [GanttScale, GanttScale] {
  const year: GanttScale = { unit: 'year', step: 1, format: (value) => new Intl.DateTimeFormat(language, { year: 'numeric' }).format(value) }
  if (months === 120) return [year, { unit: 'quarter', step: 2, format: (value) => value.getMonth() < 6 ? 'S1' : 'S2' }]
  if (months === 60) return [year, { unit: 'quarter', step: 1, format: (value) => `Q${Math.floor(value.getMonth() / 3) + 1}` }]
  if (months === 24) return [year, { unit: 'month', step: 1, format: (value) => new Intl.DateTimeFormat(language, { month: 'short' }).format(value) }]
  return [
    { unit: 'month', step: 1, format: (value) => new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(value) },
    { unit: 'week', step: 1, format: (value) => new Intl.DateTimeFormat(language, { day: 'numeric', month: 'short' }).format(value) },
  ]
}

function nextBoundary(date: Date, scale: GanttScale) {
  if (scale.unit === 'year') return new Date(date.getFullYear() + 1, 0, 1, 12)
  if (scale.unit === 'month') return new Date(date.getFullYear(), date.getMonth() + 1, 1, 12)
  if (scale.unit === 'quarter') return new Date(date.getFullYear(), Math.floor(date.getMonth() / (scale.step * 3)) * scale.step * 3 + scale.step * 3, 1, 12)
  const daysUntilMonday = (8 - date.getDay()) % 7 || 7
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + daysUntilMonday, 12)
}

export function ganttScaleSegments(from: Date, until: Date, scale: GanttScale) {
  const segments: { from: Date; to: Date; label: string }[] = []
  let cursor = new Date(from)
  while (cursor < until) {
    const next = nextBoundary(cursor, scale)
    const to = next < until ? next : until
    segments.push({ from: cursor, to, label: scale.format(cursor) })
    cursor = to
  }
  return segments
}
