import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import type { LabsManagerGanttData } from './model'
import { PlanningGanttView } from './PlanningGanttView'

vi.mock('./LabsManagerGantt', () => ({ LabsManagerGantt: ({ data, visibility, window }: {
  data: LabsManagerGanttData
  visibility: { showMilestones: boolean; showTasks: boolean }
  window: { months: number }
}) => <div data-testid="planning-gantt" data-milestones={String(visibility.showMilestones)} data-tasks={String(visibility.showTasks)} data-window={window.months} data-items={data.items.length} /> }))
vi.mock('../print/PrintButton', () => ({ PrintButton: ({ createRequest }: { createRequest: () => { state: { data: LabsManagerGanttData } } }) =>
  <span data-testid="gantt-print-data" data-items={createRequest().state.data.items.length} /> }))

const data: LabsManagerGanttData = { items: [
  { key: 'project:7', kind: 'group', label: 'Atlas', start: '2026-01-01', end: '2026-12-31', identity: { kind: 'project', id: '7' } },
  { key: 'work:8', parentKey: 'project:7', kind: 'task', label: 'Task', start: '2026-03-01', end: '2026-03-20', identity: { kind: 'work', id: '8' } },
  { key: 'work:9', parentKey: 'project:7', kind: 'milestone', label: 'Milestone', start: null, end: '2026-04-01', identity: { kind: 'work', id: '9' } },
], dependencies: [] }

function Harness() {
  const [months, setMonths] = useState<6 | 12 | 24 | 60 | 120>(24)
  return <I18nProvider><PlanningGanttView data={data} events={[]} anchor={new Date(2026, 0, 1)} months={months} onAnchorChange={() => undefined} onMonthsChange={setMonths} onSelect={() => undefined} /></I18nProvider>
}

describe('shared Planning Gantt visibility', () => {
  beforeEach(() => Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] }))

  it('allows all four combinations and retains the choice across periods without changing Print data', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const milestones = screen.getByRole('checkbox', { name: 'Jalons' })
    const tasks = screen.getByRole('checkbox', { name: 'Tâches' })
    const gantt = screen.getByTestId('planning-gantt')
    expect(milestones).toBeChecked()
    expect(tasks).toBeChecked()
    expect(gantt).toHaveAttribute('data-milestones', 'true')
    expect(gantt).toHaveAttribute('data-tasks', 'true')
    await user.click(tasks)
    expect(gantt).toHaveAttribute('data-milestones', 'true')
    expect(gantt).toHaveAttribute('data-tasks', 'false')
    await user.click(tasks)
    await user.click(milestones)
    expect(gantt).toHaveAttribute('data-milestones', 'false')
    expect(gantt).toHaveAttribute('data-tasks', 'true')
    await user.click(tasks)
    expect(gantt).toHaveAttribute('data-milestones', 'false')
    expect(gantt).toHaveAttribute('data-tasks', 'false')
    expect(gantt).toHaveAttribute('data-items', '3')
    expect(screen.getByTestId('gantt-print-data')).toHaveAttribute('data-items', '3')
    await user.click(screen.getByRole('button', { name: '1 an' }))
    expect(gantt).toHaveAttribute('data-window', '12')
    expect(milestones).not.toBeChecked()
    expect(tasks).not.toBeChecked()
  })
})
