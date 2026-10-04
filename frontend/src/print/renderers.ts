import { registerPrintRenderer } from './registry'
import { CalendarPrintView } from './CalendarPrintView'
import { GanttPrintView } from './GanttPrintView'
import { OrganizationChartPrintView } from './OrganizationChartPrintView'
import { DashboardPrintView } from '../dashboard/DashboardPrintView'

let registered = false
export function registerBuiltinPrintRenderers() {
  if (registered) return
  registered = true
  registerPrintRenderer({ key: 'calendar', label: 'Calendar', render: CalendarPrintView, defaultPage: { size: 'A4', orientation: 'landscape' } })
  registerPrintRenderer({ key: 'gantt', label: 'Gantt', render: GanttPrintView, defaultPage: { size: 'A3', orientation: 'landscape' } })
  registerPrintRenderer({ key: 'organization-chart', label: 'Organization chart', render: OrganizationChartPrintView, defaultPage: { size: 'A3', orientation: 'landscape' } })
  registerPrintRenderer({ key: 'dashboard', label: 'Dashboard', render: DashboardPrintView, defaultPage: { size: 'A4', orientation: 'landscape' } })
}
