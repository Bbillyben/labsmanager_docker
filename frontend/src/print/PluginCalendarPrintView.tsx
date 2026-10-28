import { PluginCalendarCanvas } from '../calendar/PluginCalendarView'
import type { PluginCalendarEvent, PluginCalendarMode, PluginCalendarResource } from '../calendar/pluginCalendarPresentation'
import type { ProjectCalendarScope } from '../pages/projectCalendarScopes'
import type { PrintRendererProps } from './registry'
import styles from './print.module.css'

type State = { scope: ProjectCalendarScope; mode: PluginCalendarMode; anchor: string
  range: { from: string; to: string }; events: PluginCalendarEvent[]; resources: PluginCalendarResource[]; unassignedLabel: string; showCalendarName?: boolean }

export function PluginCalendarPrintView({ state, onReady }: PrintRendererProps<State>) {
  return <section className={styles.content} data-testid="plugin-calendar-print" data-calendar-mode={state.mode}>
    <h2>{state.range.from} – {state.range.to}</h2>
    <PluginCalendarCanvas scope={state.scope} mode={state.mode} anchor={new Date(state.anchor)} events={state.events}
      resources={state.resources} unassignedLabel={state.unassignedLabel} showCalendarName={state.showCalendarName} print onReady={onReady} />
  </section>
}
