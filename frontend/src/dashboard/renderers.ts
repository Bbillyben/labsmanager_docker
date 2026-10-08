import type { ReactNode } from 'react'
import type { DashboardWidget } from '../api/dashboards'
import { KpiRenderer, CompactListRenderer, AlertListRenderer, ProgressListRenderer, EmptyRenderer } from './PilotRenderers'
import { LineChartRenderer } from './LineChartRenderer'
import { DataConsistencyRenderer } from './DataConsistencyRenderer'
import { OverviewListRenderer } from './OverviewListRenderer'
import { DeadlineListRenderer } from './DeadlineListRenderer'
import { ContractListRenderer } from './ContractListRenderer'
import { EmployeeMovementsRenderer } from './EmployeeMovementsRenderer'
import { TaskWorkloadRenderer } from './TaskWorkloadRenderer'
import { TimelineCalendarRenderer } from './TimelineCalendarRenderer'
import { CalendarGridRenderer } from './CalendarGridRenderer'
import { ProjectPortfolioRenderer } from './ProjectPortfolioRenderer'
import { EmployeeWorkloadRenderer } from './EmployeeWorkloadRenderer'
import type { DashboardSize } from './size'
import type { DashboardMode } from './mode'

export type DashboardRenderer = (props: { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }) => ReactNode
type RendererEntry = { component: DashboardRenderer; printComponent?: DashboardRenderer }
const registry = new Map<string, RendererEntry>()
export function registerDashboardRenderer(key: string, renderer: DashboardRenderer, printComponent?: DashboardRenderer) {
  if (registry.has(key)) throw new Error(`Duplicate dashboard renderer: ${key}`)
  registry.set(key, { component: renderer, printComponent })
}
export function getDashboardRenderer(key: string, mode: DashboardMode = 'view') {
  const entry = registry.get(key)
  return mode === 'print' ? entry?.printComponent ?? entry?.component : entry?.component
}

registerDashboardRenderer('kpi', KpiRenderer)
registerDashboardRenderer('compact-list', CompactListRenderer)
registerDashboardRenderer('alert-list', AlertListRenderer)
registerDashboardRenderer('progress-list', ProgressListRenderer)
registerDashboardRenderer('overview-list', OverviewListRenderer)
registerDashboardRenderer('deadline-list', DeadlineListRenderer)
registerDashboardRenderer('contract-list', ContractListRenderer)
registerDashboardRenderer('employee-movements', EmployeeMovementsRenderer)
registerDashboardRenderer('task-workload', TaskWorkloadRenderer)
registerDashboardRenderer('timeline-calendar', TimelineCalendarRenderer)
registerDashboardRenderer('calendar-grid', CalendarGridRenderer)
registerDashboardRenderer('project-portfolio', ProjectPortfolioRenderer)
registerDashboardRenderer('employee-workload', EmployeeWorkloadRenderer)
registerDashboardRenderer('empty', EmptyRenderer)
registerDashboardRenderer('line-chart', LineChartRenderer)
registerDashboardRenderer('data-consistency', DataConsistencyRenderer)
