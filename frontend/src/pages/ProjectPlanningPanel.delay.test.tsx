import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlanningMilestone, ProjectPlanningCollection } from '../api/planning'
import { I18nProvider } from '../i18n/I18nProvider'
import { ProjectPlanningPanel } from './ProjectPlanningPanel'

const api = vi.hoisted(() => ({ get: vi.fn(), preview: vi.fn(), apply: vi.fn() }))
vi.mock('../api/planning', async (importOriginal) => ({
  ...await importOriginal<typeof import('../api/planning')>(),
  getProjectPlanning: api.get,
  previewProjectPlanningDelay: api.preview,
  applyProjectPlanningDelay: api.apply,
}))

function item(id: number, name: string, status = false, endDate: string | null = '2026-11-01'): PlanningMilestone {
  return { id, name, desc: null, start_date: null, end_date: endDate, status, type: 'o', quotity: '0.000',
    display_state: status ? 'completed' : 'planned', days_to_due: 20, work_kind: 'milestone',
    project: { id: 7, name: 'Atlas', can_view: true }, employees: [], dependencies: [] }
}

const collection: ProjectPlanningCollection = {
  capabilities: { can_add: false, can_change: true, can_delete: false }, participants: [],
  items: [item(1, 'Alpha'), item(2, 'Beta'), item(3, 'Completed', true)],
}

beforeEach(() => {
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en-US'] })
  api.get.mockReset().mockResolvedValue(collection)
  api.preview.mockReset().mockImplementation((_project, intent) => Promise.resolve({
    ...intent, nodes: intent.root_ids.map((id: number) => ({ id, name: collection.items.find((row) => row.id === id)?.name ?? '',
      project: { id: 7, name: 'Atlas' }, work_kind: 'milestone', end_date: '2026-11-01', eligible: true, unavailable_reason: null, affected: true })),
    edges: [], affected: intent.root_ids.map((id: number) => ({ id, old_end_date: '2026-11-01', new_end_date: '2026-11-15' })),
    excluded_ids: [], revision: 'current',
  }))
  api.apply.mockReset().mockResolvedValue({ affected_ids: [1, 2] })
})

function setup() {
  render(<I18nProvider><MemoryRouter><ProjectPlanningPanel projectId="7" /></MemoryRouter></I18nProvider>)
  return userEvent.setup()
}

describe('Project Planning delay entry points', () => {
  it('keeps the normal list unchanged and uses a temporary, keyboard-accessible bulk selection', async () => {
    const user = setup()
    expect(await screen.findByRole('button', { name: 'Open details for Alpha' })).toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Select “Alpha” for delay' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Delay milestones…' }))
    expect(screen.getByText('0 selected')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Select “Alpha” for delay' }))
    await user.click(screen.getByRole('button', { name: 'Select “Beta” for delay' }))
    expect(screen.getByText('2 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Completed.*1/ }))
    expect(screen.getByRole('button', { name: 'Select “Completed” for delay' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Deselect “Alpha” for delay' }))
    expect(screen.getByText('1 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByText('1 selected')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open details for Alpha' })).toBeInTheDocument()
  })

  it('passes multiple selected roots into the shared Sheet and exits bulk mode after success', async () => {
    const user = setup()
    await screen.findByRole('button', { name: 'Open details for Alpha' })
    await user.click(screen.getByRole('button', { name: 'Delay milestones…' }))
    await user.click(screen.getByRole('button', { name: 'Select “Alpha” for delay' }))
    await user.click(screen.getByRole('button', { name: 'Select “Beta” for delay' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    expect(await screen.findByRole('dialog', { name: 'Delay tasks and milestones' })).toBeInTheDocument()
    await waitFor(() => expect(api.preview).toHaveBeenCalledWith('7', expect.objectContaining({ root_ids: [1, 2] }), expect.anything()))
    await user.click(await screen.findByRole('button', { name: 'Apply delay' }))
    await waitFor(() => expect(api.apply).toHaveBeenCalledOnce())
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Delay tasks and milestones' })).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Delay milestones…' })).toBeInTheDocument()
    expect(screen.queryByText('2 selected')).not.toBeInTheDocument()
    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2))
  })

  it('opens the same Sheet from one eligible row without entering bulk mode', async () => {
    const user = setup()
    await screen.findByRole('button', { name: 'Open details for Alpha' })
    await user.click(screen.getByRole('button', { name: 'Actions for Alpha' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Delay milestone…' }))
    expect(await screen.findByRole('dialog', { name: 'Delay tasks and milestones' })).toBeInTheDocument()
    await waitFor(() => expect(api.preview).toHaveBeenCalledWith('7', expect.objectContaining({ root_ids: [1] }), expect.anything()))
    expect(screen.queryByText(/selected/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Delay tasks and milestones' })).not.toBeInTheDocument())
    await waitFor(() => expect(screen.getByRole('button', { name: 'Actions for Alpha' })).toHaveFocus())
    expect(screen.getByRole('button', { name: 'Delay milestones…' })).toBeInTheDocument()
  })
})
