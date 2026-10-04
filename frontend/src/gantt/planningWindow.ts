import type { GanttWindow } from './SvarGanttAdapter'

export type PlanningMonths = GanttWindow['months']
const iso = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`

export function planningWindow(anchor: Date, months: PlanningMonths): GanttWindow {
  const from = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
  return { from: iso(from), to: iso(new Date(from.getFullYear(), from.getMonth() + months, 0)), months }
}
