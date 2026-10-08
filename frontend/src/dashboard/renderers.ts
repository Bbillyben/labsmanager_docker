import type { ReactNode } from 'react'
import type { DashboardWidget } from '../api/dashboards'
import { KpiRenderer, CompactListRenderer, AlertListRenderer, ProgressListRenderer, EmptyRenderer } from './PilotRenderers'
import { LineChartRenderer } from './LineChartRenderer'
import { DataConsistencyRenderer } from './DataConsistencyRenderer'
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
registerDashboardRenderer('empty', EmptyRenderer)
registerDashboardRenderer('line-chart', LineChartRenderer)
registerDashboardRenderer('data-consistency', DataConsistencyRenderer)
