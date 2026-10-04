import type { CalendarEvent } from '../api/employees'
import { SharedCalendar, type CalendarResource, type CalendarViewMode, type ResourceVisibilityMode } from '../calendar/SharedCalendar'
import { useTranslation } from '../i18n/i18n'
import { projectCalendarViewDefinition, type CalendarViewKey, type ProjectCalendarScope } from '../pages/projectCalendarScopes'
import type { PrintRendererProps } from './registry'
import styles from './print.module.css'

export type CalendarPrintState = {
  scope: ProjectCalendarScope
  viewType: CalendarViewKey
  mode: CalendarViewMode
  range: { from: string; to: string }
  events: CalendarEvent[]
  todayEvents?: CalendarEvent[]
  resourceVisibilityMode?: ResourceVisibilityMode
  resources?: CalendarResource[]
  employeeNames?: Record<string, string>
  filters?: Record<string, unknown>
  selectedId?: string | null
}

export function CalendarPrintView({ state, onReady }: PrintRendererProps<CalendarPrintState>) {
  const { language, t } = useTranslation()
  const definition = projectCalendarViewDefinition(state.scope, state.mode)
  if (state.viewType !== definition.key) return <p role="alert">{t('print.unknownRenderer')}</p>
  const format = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`))
  const names = new Map(Object.entries(state.employeeNames ?? {}).map(([id, name]) => [Number(id), name]))
  return <section className={styles.content} data-testid="calendar-print" data-view-type={definition.key}>
    <h2>{t(definition.label)} · {format(state.range.from)} – {format(state.range.to)}</h2>
    <SharedCalendar anchor={new Date(`${state.range.from}T12:00:00`)} scope={state.scope} viewMode={state.mode} events={state.events} resources={state.resources} todayEvents={state.todayEvents} resourceVisibilityMode={state.resourceVisibilityMode ?? 'period'} employeeNames={names} print onReady={onReady} />
  </section>
}
