import type { DashboardDetail, DashboardWidget, WidgetDefinition } from '../api/dashboards'

export type DashboardPrintState = {
  dashboard: Pick<DashboardDetail, 'id' | 'name' | 'scope'>
  widgets: DashboardWidget[]
  definitions: WidgetDefinition[]
}

export function printableWidgets(state: DashboardPrintState) {
  const definitions = new Map(state.definitions.map((definition) => [definition.key, definition]))
  return [...state.widgets]
    .filter((widget) => definitions.get(widget.definition_key)?.printable !== false)
    .sort((first, second) => first.logical_order - second.logical_order || first.id.localeCompare(second.id))
}
