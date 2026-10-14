import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { IApi, ITask } from '@svar-ui/react-gantt'
import { SvarGanttAdapter, toSvarTasks, type PlanningGanttVisibility } from './SvarGanttAdapter'
import type { GanttIdentity, LabsManagerGanttData } from './model'

vi.mock('@svar-ui/react-gantt', () => ({
  Willow: ({ children }: { children: ReactNode }) => <>{children}</>,
  WillowDark: ({ children }: { children: ReactNode }) => <>{children}</>,
  Gantt: ({ init, tasks, readonly, links }: {
    init: (api: IApi) => void
    tasks: ITask[]
    readonly: boolean
    links: unknown[]
  }) => {
    let select: (event: { id: string | number }) => void = () => undefined
    init({ on: (name: string, handler: (event: { id: string | number }) => void) => { if (name === 'select-task') select = handler } } as IApi)
    return <div data-readonly={readonly} data-links={links.length}>
      {tasks.map((task) => <button key={task.id} onClick={() => select({ id: task.id! })} type="button">{task.id}</button>)}
    </div>
  },
}))

const data: LabsManagerGanttData = { items: [
  { key: 'project:7', kind: 'group', label: 'Atlas', start: '2026-01-01', end: '2026-12-31', identity: { kind: 'project', id: '7' } },
  { key: 'participation:3', parentKey: 'project:7', kind: 'participation', label: 'Member', start: '2026-02-01', end: '2026-08-31', identity: { kind: 'participation', id: '3' } },
  { key: 'work:8', parentKey: 'project:7', kind: 'task', label: 'Task', start: '2026-03-01', end: '2026-03-20', identity: { kind: 'work', id: '8' } },
  { key: 'work:9', parentKey: 'project:7', kind: 'milestone', label: 'Milestone', start: null, end: '2026-04-01', identity: { kind: 'work', id: '9' } },
], dependencies: [] }

describe('SVAR selection adapter', () => {
  it('keeps Project bars and dates while independently hiding Planning kinds and orphan links', () => {
    const projectWithoutChildren = { key: 'project:10', kind: 'group' as const, label: 'Empty project', start: '2026-02-01', end: '2026-10-31', identity: { kind: 'project' as const, id: '10' } }
    const source: LabsManagerGanttData = { items: [...data.items, projectWithoutChildren], dependencies: [
      { id: '51', predecessor: { kind: 'work', id: '8' }, successor: { kind: 'work', id: '9' }, temporallyInconsistent: false },
    ] }
    const window = { from: '2026-01-01', to: '2026-12-31', months: 12 as const }
    const render = (visibility: PlanningGanttVisibility) => toSvarTasks(source, [], window, new Set(), visibility)
    const both = render({ showMilestones: true, showTasks: true })
    const milestones = render({ showMilestones: true, showTasks: false })
    const tasks = render({ showMilestones: false, showTasks: true })
    const neither = render({ showMilestones: false, showTasks: false })
    const ids = (result: typeof both) => result.tasks.map((task) => String(task.id))

    expect(ids(both)).toEqual(['project:7', 'participation:3', 'work:8', 'work:9', 'project:10'])
    expect(ids(milestones)).toEqual(['project:7', 'participation:3', 'work:9', 'project:10'])
    expect(ids(tasks)).toEqual(['project:7', 'participation:3', 'work:8', 'project:10'])
    expect(ids(neither)).toEqual(['project:7', 'participation:3', 'project:10'])
    const globalProjects = { ...source, items: source.items.filter((item) => item.kind !== 'participation') }
    expect(toSvarTasks(globalProjects, [], window, new Set(), { showMilestones: false, showTasks: false }).tasks.map((task) => task.id)).toEqual(['project:7', 'project:10'])
    expect(both.links).toHaveLength(1)
    expect(milestones.links).toHaveLength(0)
    expect(tasks.links).toHaveLength(0)
    expect(neither.links).toHaveLength(0)
    for (const result of [milestones, tasks, neither]) {
      expect(result.tasks[0].start).toEqual(both.tasks[0].start)
      expect(result.tasks[0].end).toEqual(both.tasks[0].end)
      expect(result.tasks.find((task) => task.id === 'project:10')?.open).toBe(false)
    }
    expect(source.items).toHaveLength(5)
    expect(source.dependencies).toHaveLength(1)
  })

  it('forwards selected tasks and milestones as LabsManager identities, while keeping SVAR read-only', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn<(identity: GanttIdentity) => void>()
    render(<SvarGanttAdapter data={data} dark={false} events={[]} language="en" onSelect={onSelect} window={{ from: '2026-01-01', to: '2026-06-30', months: 6 }} />)
    await user.click(screen.getByRole('button', { name: 'work:8' }))
    await user.click(screen.getByRole('button', { name: 'work:9' }))
    expect(onSelect.mock.calls).toEqual([[{ kind: 'work', id: '8' }], [{ kind: 'work', id: '9' }]])
    expect(screen.getByRole('button', { name: 'work:8' }).parentElement).toHaveAttribute('data-readonly', 'true')
    expect(screen.getByRole('button', { name: 'work:8' }).parentElement).toHaveAttribute('data-links', '0')
  })

  it('passes only visible links to SVAR in read-only mode', () => {
    render(<SvarGanttAdapter data={{ ...data, dependencies: [{ id: '51', predecessor: { kind: 'work', id: '8' }, successor: { kind: 'work', id: '9' }, temporallyInconsistent: false }] }} dark={false} events={[]} language="en" onSelect={() => undefined} window={{ from: '2026-01-01', to: '2026-06-30', months: 6 }} />)
    expect(screen.getByRole('button', { name: 'work:8' }).parentElement).toHaveAttribute('data-links', '1')
    expect(screen.getByRole('button', { name: 'work:8' }).parentElement).toHaveAttribute('data-readonly', 'true')
  })
})
