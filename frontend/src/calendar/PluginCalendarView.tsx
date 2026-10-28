import FullCalendar, { type EventInput } from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import listPlugin from '@fullcalendar/react/list'
import enGbLocale from '@fullcalendar/react/locales/en-gb'
import frLocale from '@fullcalendar/react/locales/fr'
import resourceTimelinePlugin from '@fullcalendar/react-scheduler/resource-timeline'
import timelinePlugin from '@fullcalendar/react-scheduler/timeline'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from '../i18n/i18n'
import { projectCalendarRange, projectCalendarScopeOrder, projectCalendarScopes, projectDayGridViews, projectResourceViews, shiftProjectCalendarAnchor, type ProjectCalendarScope } from '../pages/projectCalendarScopes'
import { PrintButton } from '../print/PrintButton'
import { Button } from '../ui/Button'
import { pluginCalendarResources, pluginCalendarViewKey, type PluginCalendarEvent, type PluginCalendarMode, type PluginCalendarResource, type PluginCalendarRange } from './pluginCalendarPresentation'
import styles from './PluginCalendarView.module.css'

const plugins = [dayGridPlugin, timelinePlugin, resourceTimelinePlugin, listPlugin, interactionPlugin, classicThemePlugin]
const listViews = Object.fromEntries(projectCalendarScopeOrder.map((scope) => [
  `list_${scope}`, { type: 'list', duration: projectCalendarScopes[scope].duration,
    dateAlignment: scope === 'year' ? 'year' : scope === 'fifteenDays' ? undefined : 'month' },
]))
const views = { ...projectDayGridViews, ...projectResourceViews, ...listViews }
const unassignedId = '__calendar_unassigned__'

function followingDay(iso: string) {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10)
}

export function PluginCalendarCanvas({ scope, mode, anchor, events, resources = [], showCalendarName = false, print = false, onReady, onEventClick, onDateSelect, canCreate = false, unassignedLabel }: {
  scope: ProjectCalendarScope; mode: PluginCalendarMode; anchor: Date
  events: PluginCalendarEvent[]; resources?: PluginCalendarResource[]; showCalendarName?: boolean; print?: boolean; onReady?: () => void
  onEventClick?: (id: string) => void; onDateSelect?: (range: { start: string; end: string; allDay: boolean }) => void
  canCreate?: boolean; unassignedLabel: string
}) {
  const { language } = useTranslation()
  const view = pluginCalendarViewKey(scope, mode)
  const resourceRows = useMemo(() => pluginCalendarResources(events, resources, unassignedLabel), [events, resources, unassignedLabel])
  const source = useMemo(() => new Map(events.map((event) => [event.id, event])), [events])
  const mapped = useMemo<EventInput[]>(() => events.map((event) => ({
    id: event.id, title: `${showCalendarName && event.calendarName ? `${event.calendarName} · ` : ''}${event.title}${mode === 'calendar' && event.employeeNames?.length ? ` · ${event.employeeNames.length}` : ''}`, start: event.start, end: event.end, allDay: event.allDay,
    color: event.color, resourceIds: mode === 'resources' ? event.resourceIds?.length ? event.resourceIds : [unassignedId] : undefined,
    interactive: !print,
  })), [events, mode, print, showCalendarName])
  return <div className={`${styles.canvas} ${print ? styles.print : ''}`} data-calendar-mode={mode} data-calendar-view={view}>
    <FullCalendar key={`${view}:${anchor.toDateString()}:${print}`} plugins={plugins} views={views}
      initialView={view} initialDate={anchor} headerToolbar={false} firstDay={1} fixedWeekCount={false}
      locale={language.startsWith('fr') ? frLocale : enGbLocale} events={mapped}
      resources={mode === 'resources' ? resourceRows : undefined} resourceOrder="title"
      schedulerLicenseKey="AGPL-My-Frontend-And-Backend-Are-Open-Source"
      selectable={!print && canCreate} select={(info) => onDateSelect?.({ start: info.startStr, end: info.endStr, allDay: info.allDay })}
      dateClick={(info) => onDateSelect?.({ start: info.dateStr, end: info.dateStr, allDay: info.allDay })}
      eventClick={(info) => { if (!print) onEventClick?.(info.event.id) }}
      eventContent={mode === 'list' ? (info) => {
        const item = source.get(info.event.id)
        return <span className={styles.listContent}><strong>{item?.title ?? info.event.title}</strong>
          {item?.typeName && <span>{item.typeName}</span>}
          {item?.calendarName && <span>{item.calendarName}</span>}
          {!!item?.employeeNames?.length && <span>{item.employeeNames.join(', ')}</span>}
        </span>
      } : undefined}
      datesSet={() => { if (print) requestAnimationFrame(() => requestAnimationFrame(() => onReady?.())) }}
      height={print ? 'auto' : undefined} contentHeight={print ? 'auto' : undefined}
      slotMinWidth={print && mode !== 'list' && scope === 'year' ? 56 : undefined}
    />
  </div>
}

export function PluginCalendarView({ title, events, resources = [], allowResources = false, showCalendarName = false, canCreate = false, onRangeChange, onModeChange, onEventClick, onDateSelect }: {
  title: string; events: PluginCalendarEvent[]; resources?: PluginCalendarResource[]; allowResources?: boolean
  showCalendarName?: boolean
  canCreate?: boolean; onRangeChange: (range: PluginCalendarRange) => void; onModeChange?: (mode: PluginCalendarMode) => void
  onEventClick?: (id: string) => void; onDateSelect?: (range: { start: string; end: string; allDay: boolean }) => void
}) {
  const { language, t } = useTranslation()
  const [scope, setScope] = useState<ProjectCalendarScope>('month')
  const [mode, setMode] = useState<PluginCalendarMode>('calendar')
  const displayMode = mode === 'resources' && !allowResources ? 'calendar' : mode
  const [anchor, setAnchor] = useState(() => new Date())
  const range = useMemo(() => projectCalendarRange(scope, anchor), [scope, anchor])
  const onRange = onRangeChange
  useEffect(() => { onRange({ start: range.from, end: followingDay(range.to) }) }, [range.from, range.to, onRange])
  const dateLabel = new Intl.DateTimeFormat(language, { dateStyle: 'medium' })
  const unassignedLabel = language.startsWith('fr') ? 'Sans ligne employé' : 'No employee row'
  return <section className={styles.root}>
    <div className={styles.toolbar}>
      <div role="group" aria-label={t('projectCalendar.period')} className={styles.group}>
        {projectCalendarScopeOrder.map((item) => <Button key={item} size="sm" variant={scope === item ? 'secondary' : 'ghost'} aria-pressed={scope === item} onClick={() => setScope(item)}>{t(projectCalendarScopes[item].label)}</Button>)}
      </div>
      <div role="group" aria-label={language.startsWith('fr') ? 'Affichage' : 'Display'} className={styles.group}>
        {(['calendar', 'list', ...(allowResources ? ['resources'] as const : [])] as PluginCalendarMode[]).map((item) => <Button key={item} size="sm" variant={displayMode === item ? 'secondary' : 'ghost'} aria-pressed={displayMode === item} onClick={() => { setMode(item); onModeChange?.(item) }}>{item === 'list' ? language.startsWith('fr') ? 'Liste' : 'List' : t(`projectCalendar.${item}`)}</Button>)}
      </div>
      <PrintButton createRequest={() => ({ renderer: 'plugin-calendar', title, state: {
        scope, mode: displayMode, anchor: anchor.toISOString(), range, events, resources, unassignedLabel, showCalendarName,
      } })} />
    </div>
    <div className={styles.navigation}>
      <Button size="sm" variant="ghost" onClick={() => setAnchor((value) => shiftProjectCalendarAnchor(value, scope, -1))} aria-label={t('leaves.previous')}>‹</Button>
      <Button size="sm" variant="ghost" onClick={() => setAnchor(new Date())}>{t('leaves.today')}</Button>
      <Button size="sm" variant="ghost" onClick={() => setAnchor((value) => shiftProjectCalendarAnchor(value, scope, 1))} aria-label={t('leaves.next')}>›</Button>
      <strong>{dateLabel.format(new Date(`${range.from}T12:00:00`))} – {dateLabel.format(new Date(`${range.to}T12:00:00`))}</strong>
    </div>
    <PluginCalendarCanvas scope={scope} mode={displayMode} anchor={anchor} events={events} resources={resources} showCalendarName={showCalendarName}
      canCreate={canCreate} onEventClick={onEventClick} onDateSelect={onDateSelect} unassignedLabel={unassignedLabel} />
  </section>
}
