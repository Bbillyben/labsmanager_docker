import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { IApi, ITask } from '@svar-ui/react-gantt'
import { SvarGanttAdapter } from './SvarGanttAdapter'
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
