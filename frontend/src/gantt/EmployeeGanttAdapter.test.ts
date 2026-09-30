import { describe, expect, it } from 'vitest'
import type { EmployeeMilestone, EmployeeProjectParticipation } from '../api/employees'
import { adaptEmployeeGantt } from './EmployeeGanttAdapter'
import { adaptPlanningGantt } from './PlanningGanttAdapter'
import { toSvarTasks } from './SvarGanttAdapter'

const participation: EmployeeProjectParticipation = {
  id: 3, project: { id: 7, name: 'Atlas', start_date: '2026-01-01', end_date: '2026-12-31', can_view: true },
  role: { code: 'member', label: 'Member' }, start_date: '2026-02-01', end_date: '2026-08-31',
  quotity: '0.5', is_active: true,
}
const work: EmployeeMilestone[] = [
  { id: 8, name: 'Task', desc: null, start_date: '2026-03-01', end_date: '2026-03-20', status: false, type: 'o', quotity: '0', display_state: 'overdue', days_to_due: -1, work_kind: 'task', project: { id: 7, name: 'Atlas', can_view: true }, employees: [], dependencies: [] },
  { id: 9, name: 'Milestone', desc: null, start_date: null, end_date: '2026-04-01', status: true, type: 'o', quotity: '1', display_state: 'completed', days_to_due: 0, work_kind: 'milestone', project: { id: 7, name: 'Atlas', can_view: true }, employees: [], dependencies: [] },
  { id: 10, name: 'Undated', desc: null, start_date: '2026-05-01', end_date: null, status: false, type: 'o', quotity: '0', display_state: 'planned', days_to_due: null, work_kind: 'task', project: { id: 7, name: 'Atlas', can_view: true }, employees: [], dependencies: [] },
]

describe('Employee Gantt adaptation', () => {
  it('groups Employee resources by Project and preserves backend states', () => {
    const data = adaptEmployeeGantt([participation], work)
    expect(data.items.map((item) => item.key)).toEqual(['project:7', 'participation:3', 'work:8', 'work:9', 'work:10'])
    expect(data.items[2]).toMatchObject({ parentKey: 'project:7', kind: 'task', state: 'overdue' })
    expect(data.items[3]).toMatchObject({ kind: 'milestone', state: 'completed' })
  })

  it('adapts the same Planning items without Employee participation rows', () => {
    const data = adaptPlanningGantt(work)
    expect(data.items.map((item) => item.key)).toEqual(['project:7', 'work:8', 'work:9', 'work:10'])
    expect(data.items[1]).toMatchObject({ kind: 'task', state: 'overdue' })
  })

  it('maps scoped dependencies without inventing missing endpoints', () => {
    const scoped = work.map((item) => ({ ...item, dependencies: item.id === 9 ? [
      { id: 51, predecessor_id: 8, successor_id: 9, temporally_inconsistent: false },
      { id: 52, predecessor_id: 999, successor_id: 9, temporally_inconsistent: false },
    ] : [] }))
    const mapped = toSvarTasks(adaptEmployeeGantt([participation], scoped), [], { from: '2026-01-01', to: '2026-06-30', months: 6 })
    expect(mapped.links).toEqual([{ id: '51', source: 'work:8', target: 'work:9', type: 'e2s' }])
  })

  it('maps dated items and normal Calendar events, while leaving background and undated items out', () => {
    const data = adaptEmployeeGantt([participation], work)
    const mapped = toSvarTasks(data, [
      { id: 'normal', title: 'Conference', start: '2026-04-10', end: '2026-04-12', source: 'ical', kind: 'event', all_day: true, color: '#336699', description: null, display: 'auto', metadata: {} },
      { id: 'holiday', title: 'Holiday', start: '2026-04-11', end: '2026-04-13', source: 'any-plugin', kind: 'holiday', all_day: true, color: '#c9e0cf', description: null, display: 'background', metadata: {} },
    ], { from: '2026-01-01', to: '2026-06-30', months: 6 })
    expect(mapped.tasks.map((item) => item.id)).toEqual(['project:7', 'participation:3', 'work:8', 'work:9', 'work:10', 'calendar:ical:normal'])
    expect(mapped.tasks[3]).toMatchObject({ type: 'milestone', state: 'completed' })
    expect(mapped.tasks[5]).toMatchObject({ color: '#336699' })
    expect(mapped.tasks[4].end).toEqual(new Date('2026-06-30T12:00:00'))
    expect(mapped.omitted).toBe(0)
    expect(mapped.identities.get('work:8')).toEqual({ kind: 'work', id: '8' })
  })

  it('keeps an empty scope empty and renders a Calendar point as a milestone', () => {
    const empty = adaptEmployeeGantt([], [])
    expect(toSvarTasks(empty, [], { from: '2026-01-01', to: '2026-06-30', months: 6 }).tasks).toEqual([])
    const mapped = toSvarTasks(empty, [{
      id: 'point', title: 'Meeting', start: '2026-02-01T10:30:00+01:00', end: null,
      source: 'other', kind: 'meeting', all_day: false, color: null,
      description: null, display: 'auto', metadata: {},
    }], { from: '2026-01-01', to: '2026-06-30', months: 6 })
    expect(mapped.tasks[0]).toMatchObject({ type: 'milestone', start: new Date('2026-02-01T10:30:00+01:00') })
  })
})
