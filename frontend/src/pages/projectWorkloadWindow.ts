import type { WorkloadPreset } from '../components/WorkloadTimeline'

export function workloadWindow(today: Date, preset: Exclude<WorkloadPreset, 'all'>, offset: number) {
  const shift = offset * 6
  const start = addUtcMonths(today, (preset === 'year' ? -3 : -12) + shift)
  const end = addUtcMonths(today, (preset === 'year' ? 9 : 48) + shift)
  return { start: isoDate(start), end: isoDate(end) }
}

function isoDate(value: Date) { return value.toISOString().slice(0, 10) }
function addUtcMonths(value: Date, amount: number) {
  const year = value.getUTCFullYear()
  const month = value.getUTCMonth() + amount
  const target = new Date(Date.UTC(year, month, 1))
  const lastDay = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate()
  target.setUTCDate(Math.min(value.getUTCDate(), lastDay))
  return target
}
