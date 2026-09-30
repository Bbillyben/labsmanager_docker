import { useCallback, useLayoutEffect, useRef } from 'react'
import { Gantt, Willow, WillowDark, type IApi, type ILink, type ITask } from '@svar-ui/react-gantt'
import '@svar-ui/react-gantt/all.css'
import type { CalendarEvent } from '../api/employees'
import type { GanttIdentity, LabsManagerGanttData, LabsManagerGanttItem } from './model'
import styles from './LabsManagerGantt.module.css'

export type GanttWindow = { from: string; to: string; months: 6 | 12 | 24 | 60 | 120 }

function date(value: string) { return new Date(`${value.slice(0, 10)}T12:00:00`) }
function calendarDate(value: string) { return value.includes('T') ? new Date(value) : date(value) }
function valid(value: string | null): value is string { return Boolean(value && !Number.isNaN(Date.parse(value))) }

// Kept beside the renderer so SVAR-specific mapping stays inside its adapter.
// eslint-disable-next-line react-refresh/only-export-components
export function toSvarTasks(data: LabsManagerGanttData, events: CalendarEvent[], window: GanttWindow): { tasks: ITask[]; links: ILink[]; identities: Map<string, GanttIdentity>; omitted: number } {
  const tasks: ITask[] = []
  const identities = new Map<string, GanttIdentity>()
  let omitted = 0
  const byGroup = new Map<string, LabsManagerGanttItem[]>()
  for (const item of data.items) if (item.parentKey) {
    if (!byGroup.has(item.parentKey)) byGroup.set(item.parentKey, [])
    byGroup.get(item.parentKey)!.push(item)
  }
  for (const group of data.items.filter((item) => item.kind === 'group')) {
    const children = byGroup.get(group.key) ?? []
    const dated = children.filter((item) => item.kind === 'milestone' ? valid(item.end) : valid(item.start) || (item.kind === 'participation' && valid(item.end)))
    const starts = [group.start, ...dated.map((item) => item.kind === 'milestone' ? item.end : item.start)].filter(valid).sort()
    const ends = [group.end, ...dated.map((item) => item.end)].filter(valid).sort()
    if (dated.some((item) => !item.start)) starts.push(window.from)
    if (dated.some((item) => !item.end) || (valid(group.start) && !valid(group.end))) ends.push(window.to)
    starts.sort()
    ends.sort()
    if (!starts.length || !ends.length || starts[0] > ends[ends.length - 1]) { omitted += 1 + children.length; continue }
    tasks.push({ id: group.key, text: group.label, type: 'summary', start: date(starts[0]), end: date(ends[ends.length - 1]), open: true })
    identities.set(group.key, group.identity)
    for (const item of children) {
      const start = item.kind === 'milestone' ? item.end : item.start ?? (item.kind === 'participation' ? window.from : null)
      const end = item.end ?? ((item.kind === 'participation' || item.kind === 'task') && valid(item.start) ? window.to : null)
      if (!valid(start) || !valid(end) || start > end) { omitted++; continue }
      tasks.push({
        id: item.key, parent: group.key, text: `${item.label}${!item.end ? ' ↗' : ''}`,
        type: item.kind === 'milestone' ? 'milestone' : 'task',
        start: date(start), end: date(end),
        state: item.state,
      })
      identities.set(item.key, item.identity)
    }
  }
  for (const event of events) {
    if (event.display === 'background') continue
    if (!valid(event.start)) { omitted++; continue }
    const end = valid(event.end) ? event.end : event.start
    const key = `calendar:${event.source}:${event.id}`
    tasks.push({ id: key, text: event.title, type: end === event.start ? 'milestone' : 'task', start: calendarDate(event.start), end: calendarDate(end), color: event.color ?? undefined })
    identities.set(key, { kind: 'calendar', id: event.id })
  }
  const keyByIdentity = new Map(
    [...identities].map(([key, identity]) => [`${identity.kind}:${identity.id}`, key]),
  )
  const links: ILink[] = []
  for (const dependency of data.dependencies) {
    const source = keyByIdentity.get(`${dependency.predecessor.kind}:${dependency.predecessor.id}`)
    const target = keyByIdentity.get(`${dependency.successor.kind}:${dependency.successor.id}`)
    if (source && target) links.push({ id: dependency.id, source, target, type: 'e2s' })
  }
  return { tasks, links, identities, omitted }
}

export function SvarGanttAdapter({ data, events, window, onSelect, dark, language }: {
  data: LabsManagerGanttData
  events: CalendarEvent[]
  window: GanttWindow
  onSelect: (identity: GanttIdentity) => void
  dark: boolean
  language: string
}) {
  const { tasks, links, identities } = toSvarTasks(data, events, window)
  const selection = useRef({ identities, onSelect })
  useLayoutEffect(() => { selection.current = { identities, onSelect } }, [identities, onSelect])
  const init = useCallback((api: IApi) => {
    api.on('select-task', ({ id }) => {
      const identity = selection.current.identities.get(String(id))
      if (identity) selection.current.onSelect(identity)
    })
  }, [])
  const Wrapper = dark ? WillowDark : Willow
  let width 
  if (window.months === 6) {
    width = 42
  } else if (window.months === 12) {
    width = 26
  } else if (window.months === 24) {
    width = 16
  } else if (window.months === 60) {
    width = 10
  }  else if (window.months === 120) {
    width = 0.5
  }
  const scales = window.months === 120  ? [
      {
        unit: 'year', step: 1, format: (value: Date) => new Intl.DateTimeFormat(language, { year: 'numeric' }).format(value),
      },
       {
        unit: 'quarter',
        step: 2,
        format: (value: Date) =>
          value.getMonth() < 6 ? 'S1' : 'S2',
      },
    ]
  : window.months === 60  ? [
      {
        unit: 'year', step: 1, format: (value: Date) => new Intl.DateTimeFormat(language, { year: 'numeric' }).format(value),
      },
      {
        unit: 'quarter', step: 1, format: (value: Date) => `Q${Math.floor(value.getMonth() / 3) + 1}`,
      },
    ]
  : window.months === 24 ? 
      [
          { unit: 'year', step: 1, format: (value: Date) => new Intl.DateTimeFormat(language, { year: 'numeric' }).format(value) }, 
          { unit: 'month', step: 1, format: (value: Date) => new Intl.DateTimeFormat(language, { month: 'short' }).format(value) }
      ]
    : [
        { unit: 'month', step: 1, format: (value: Date) => new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(value) }, 
        { unit: 'week', step: 1, format: (value: Date) => new Intl.DateTimeFormat(language, { day: 'numeric', month: 'short' }).format(value) }
      ]
    

  return <div className={styles.chart}>
    <Wrapper><Gantt
      readonly
      init={init}
      tasks={tasks}
      links={links}
      start={date(window.from)}
      end={date(window.to)}
      autoScale={false}
      zoom={false}
      cellWidth={width}
      cellHeight={25}
      scales={scales}
      columns={[{ id: 'text', header: ' ', width: 240 }]}
      taskTemplate={({ data: task }) => <span className={styles.task} data-state={task.state} style={task.color ? { backgroundColor: task.color } : undefined}>{task.text}{task.state === 'overdue' ? ' !' : ''}</span>}
    /></Wrapper>
  </div>
}
