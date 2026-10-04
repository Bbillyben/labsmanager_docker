import { useEffect } from 'react'
import type { CalendarEvent } from '../api/employees'
import { toSvarTasks, type GanttWindow } from '../gantt/SvarGanttAdapter'
import type { LabsManagerGanttData } from '../gantt/model'
import { ganttScales, ganttScaleSegments } from '../gantt/timeScale'
import ganttStyles from '../gantt/LabsManagerGantt.module.css'
import { useTranslation } from '../i18n/i18n'
import type { PrintRendererProps } from './registry'
import styles from './print.module.css'

export type GanttPrintState = { data: LabsManagerGanttData; events: CalendarEvent[]; window: GanttWindow; filters?: Record<string, unknown>; closedKeys?: string[] }

export function GanttPrintView({ state, onReady }: PrintRendererProps<GanttPrintState>) {
  const { language } = useTranslation()
  useEffect(() => { onReady() }, [onReady])
  const closed = new Set(state.closedKeys ?? [])
  const { tasks, links } = toSvarTasks(state.data, state.events, state.window, closed)
  const visible = tasks.filter((task) => !task.parent || !closed.has(String(task.parent)))
  const left = 250
  const width = 1000
  const row = 30
  const header = 56
  const start = new Date(`${state.window.from}T12:00:00`).getTime()
  const until = new Date(`${state.window.to}T12:00:00`)
  until.setDate(until.getDate() + 1)
  const end = until.getTime()
  const x = (date: Date) => left + Math.max(0, Math.min(1, (date.getTime() - start) / Math.max(1, end - start))) * width
  const [major, minor] = ganttScales(state.window.months, language)
  const majorSegments = ganttScaleSegments(new Date(start), until, major)
  const minorSegments = ganttScaleSegments(new Date(start), until, minor)
  const positions = new Map(visible.map((task, index) => [String(task.id), { x: x(task.end ?? task.start ?? new Date(start)), y: header + 23 + index * row }]))
  const height = Math.max(100, header + 10 + visible.length * row)
  return <section className={styles.content} data-testid="gantt-print">
    <h2>{state.window.from} – {state.window.to}</h2>
    <svg className={`${styles.gantt} ${ganttStyles.printPalette}`} viewBox={`0 0 ${left + width + 20} ${height}`} role="img" aria-label="Gantt" data-major-scale={major.unit} data-minor-scale={minor.unit}>
      <rect x={left} y={0} width={width} height={header} fill="#f1f4f7" />
      {majorSegments.map((segment) => <g key={`major:${segment.from.toISOString()}`} data-scale="major" data-date={segment.from.toISOString().slice(0, 10)}>
        <line x1={x(segment.from)} x2={x(segment.from)} y1={0} y2={height} stroke="#9eacb9" />
        <text x={(x(segment.from) + x(segment.to)) / 2} y={18} textAnchor="middle" fontSize="12" fontWeight="bold">{segment.label}</text>
      </g>)}
      {minorSegments.map((segment) => <g key={`minor:${segment.from.toISOString()}`} data-scale="minor" data-date={segment.from.toISOString().slice(0, 10)}>
        <line x1={x(segment.from)} x2={x(segment.from)} y1={26} y2={height} stroke="#d9e0e6" />
        <text x={(x(segment.from) + x(segment.to)) / 2} y={43} textAnchor="middle" fontSize={minor.unit === 'week' ? 9 : 11}>{segment.label}</text>
      </g>)}
      <line x1={left} x2={left + width} y1={26} y2={26} stroke="#9eacb9" />
      <line x1={0} x2={left + width} y1={header} y2={header} stroke="#9eacb9" />
      {visible.map((task, index) => { const y = header + 10 + index * row; const barStart = x(task.start ?? new Date(start)); const barEnd = x(task.end ?? task.start ?? new Date(start)); return <g key={String(task.id)} data-task-id={String(task.id)}>
        <text x={task.parent ? 18 : 4} y={y + 15} fontSize="12" fontWeight={task.type === 'summary' ? 'bold' : 'normal'}>{task.text}</text>
        <line x1={left} x2={left + width} y1={y + 23} y2={y + 23} stroke="#ddd" />
        {task.type === 'milestone' ? <path d={`M${barStart} ${y + 5} l8 8 -8 8 -8 -8 Z`} fill={task.color ?? '#444'} /> : <rect className={ganttStyles.printBar} data-state={task.state} data-type={task.type} x={barStart} y={y + 5} width={Math.max(2, barEnd - barStart)} height={16} rx={2} style={task.color ? { fill: task.color } : undefined} />}
      </g> })}
      {links.map((link) => { const source = positions.get(String(link.source)); const target = positions.get(String(link.target)); return source && target ? <path key={String(link.id)} d={`M${source.x} ${source.y} H${target.x - 6} V${target.y} H${target.x}`} fill="none" stroke="#555" strokeWidth="1" /> : null })}
    </svg>
  </section>
}
