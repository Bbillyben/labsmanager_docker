import { createRef } from 'react'
import { fireEvent, render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlanningMilestone } from '../api/planning'
import { I18nProvider } from '../i18n/I18nProvider'
import { PlanningMilestoneFormSheet } from './PlanningMilestoneFormSheet'

const api = vi.hoisted(() => ({ createProjectPlanningItem: vi.fn(), updateProjectPlanningItem: vi.fn() }))
vi.mock('../api/planning', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/planning')>(), ...api }))

const participants = [
  { id: 2, first_name: 'Marie', last_name: 'Curie' },
  { id: 3, first_name: 'Alexandre', last_name: 'Avec un nom de famille très long' },
]
const item: PlanningMilestone = {
  id: 8, name: 'Task', desc: null, start_date: '2026-10-01', end_date: null, status: true,
  type: 'o', quotity: '1.000', display_state: 'completed', days_to_due: null, work_kind: 'task',
  project: { id: 7, name: 'Atlas', can_view: true }, employees: [{ id: 2, first_name: 'Marie', last_name: 'Curie', can_view: true }], dependencies: [],
}

beforeEach(() => {
  vi.clearAllMocks()
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  api.createProjectPlanningItem.mockResolvedValue({ data: item })
  api.updateProjectPlanningItem.mockResolvedValue({ data: item })
})

function mount(edit: PlanningMilestone | null = null) {
  const onSaved = vi.fn()
  render(<I18nProvider><PlanningMilestoneFormSheet projectId="7" item={edit} participants={participants} onClose={vi.fn()} onSaved={onSaved} returnFocus={createRef<HTMLElement>()} /></I18nProvider>)
  return onSaved
}

describe('Planning form checkbox rows', () => {
  it('aligns checkbox labels, toggles both employees by their labels, and preserves Completed in the payload', async () => {
    mount()
    const sheet = screen.getByRole('dialog')
    const completed = within(sheet).getByRole('checkbox', { name: 'Terminé' })
    const marie = within(sheet).getByRole('checkbox', { name: 'Marie Curie' })
    const alexandre = within(sheet).getByRole('checkbox', { name: 'Alexandre Avec un nom de famille très long' })
    for (const checkbox of [completed, marie, alexandre]) {
      expect(checkbox.closest('label')).toHaveClass('flex', 'items-center')
      expect(checkbox.closest('label')).toContainElement(checkbox)
    }
    await userEvent.setup().click(within(sheet).getByText('Marie Curie'))
    await userEvent.setup().click(within(sheet).getByText('Alexandre Avec un nom de famille très long'))
    await userEvent.setup().click(within(sheet).getByText('Terminé'))
    expect(completed).toBeChecked()
    expect(marie).toBeChecked()
    expect(alexandre).toBeChecked()
    await userEvent.setup().click(within(sheet).getByText('Marie Curie'))
    expect(marie).not.toBeChecked()
    fireEvent.change(within(sheet).getByRole('textbox', { name: 'Nom' }), { target: { value: 'New task' } })
    fireEvent.change(within(sheet).getByLabelText('Début'), { target: { value: '2026-10-01' } })
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.createProjectPlanningItem).toHaveBeenCalledOnce())
    expect(api.createProjectPlanningItem.mock.calls[0][1]).toMatchObject({ status: true, employee_ids: [3] })
  })

  it('initializes edit selections and sends changed Completed and assignees', async () => {
    mount(item)
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByRole('checkbox', { name: 'Terminé' })).toBeChecked()
    expect(within(sheet).getByRole('checkbox', { name: 'Marie Curie' })).toBeChecked()
    await userEvent.setup().click(within(sheet).getByText('Terminé'))
    await userEvent.setup().click(within(sheet).getByText('Alexandre Avec un nom de famille très long'))
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.updateProjectPlanningItem).toHaveBeenCalledOnce())
    expect(api.updateProjectPlanningItem.mock.calls[0][2]).toMatchObject({ status: false, employee_ids: [2, 3] })
  })
})
