import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EmployeeMilestone } from '../api/employees'
import { MilestoneDependencies } from './MilestoneDependencies'

const api = vi.hoisted(() => ({
  getPlanningDependencies: vi.fn(),
  getEditablePlanningProjects: vi.fn(),
  getProjectPlanningItems: vi.fn(),
  createPlanningDependency: vi.fn(),
  deletePlanningDependency: vi.fn(),
}))
vi.mock('../api/planning', () => api)

const milestone: EmployeeMilestone = {
  id: 8, name: 'Follow-up', desc: null, start_date: '2026-06-02', end_date: '2026-06-10',
  status: false, type: 'o', quotity: '0', display_state: 'planned', days_to_due: 20,
  work_kind: 'task', project: { id: 7, name: 'Atlas', can_view: true }, employees: [], dependencies: [],
}
const predecessor = { id: 9, name: 'Preparation', work_kind: 'task' as const, start_date: '2026-06-01', end_date: '2026-06-03', project: { id: 7, name: 'Atlas' } }

beforeEach(() => {
  vi.clearAllMocks()
  api.getPlanningDependencies.mockResolvedValue({ can_add: true, predecessors: [] })
  api.getEditablePlanningProjects.mockResolvedValue([{ id: 7, name: 'Atlas' }, { id: 11, name: 'Other' }])
  api.getProjectPlanningItems.mockResolvedValue([predecessor])
  api.createPlanningDependency.mockResolvedValue({ id: 20, predecessor, successor_id: 8, temporally_inconsistent: false, can_delete: true })
})

describe('Milestone dependencies sheet section', () => {
  it('defaults to the current editable project and adds a predecessor', async () => {
    const user = userEvent.setup()
    const changed = vi.fn()
    render(<MilestoneDependencies milestone={milestone} onChanged={changed} />)
    expect(await screen.findByText('Aucun prédécesseur.')).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Projet du prédécesseur' })).not.toBeInTheDocument()
    expect(api.getEditablePlanningProjects).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Ajouter un prédécesseur' }))
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Projet du prédécesseur' })).toHaveValue('7'))
    await screen.findByRole('option', { name: 'Preparation · Tâche' })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Tâche ou jalon prédécesseur' }), '9')
    await user.click(screen.getByRole('button', { name: 'Ajouter la dépendance' }))
    await waitFor(() => expect(api.createPlanningDependency).toHaveBeenCalledWith(8, 9))
    expect(changed).toHaveBeenCalledOnce()
    expect(screen.queryByRole('combobox', { name: 'Projet du prédécesseur' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter un prédécesseur' })).toBeInTheDocument()
  })

  it('shows a read-only predecessor and its temporal warning', async () => {
    api.getPlanningDependencies.mockResolvedValue({ can_add: false, predecessors: [{ id: 20, predecessor, successor_id: 8, temporally_inconsistent: true, can_delete: false }] })
    render(<MilestoneDependencies milestone={milestone} />)
    expect(await screen.findByText(/Preparation/)).toBeInTheDocument()
    expect(screen.getByText(/Ordre chronologique incohérent/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter un prédécesseur' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Supprimer' })).not.toBeInTheDocument()
  })

  it('changes project before searching items and confirms deletion', async () => {
    const user = userEvent.setup()
    const linked = { id: 20, predecessor, successor_id: 8, temporally_inconsistent: false, can_delete: true }
    api.getPlanningDependencies.mockResolvedValue({ can_add: true, predecessors: [linked] })
    api.deletePlanningDependency.mockResolvedValue(undefined)
    render(<MilestoneDependencies milestone={milestone} />)
    await screen.findByRole('button', { name: 'Supprimer la dépendance avec Preparation' })
    expect(screen.getByText(/Preparation/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ajouter un prédécesseur' }))
    await screen.findByRole('option', { name: 'Other' })
    await user.selectOptions(screen.getByRole('combobox', { name: 'Projet du prédécesseur' }), '11')
    await waitFor(() => expect(api.getProjectPlanningItems).toHaveBeenCalledWith(11, '', 8, expect.any(AbortSignal)))
    await user.click(screen.getByRole('button', { name: 'Supprimer la dépendance avec Preparation' }))
    expect(await screen.findByText('Supprimer cette dépendance ?')).toBeInTheDocument()
    expect(api.deletePlanningDependency).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(api.deletePlanningDependency).toHaveBeenCalledWith(8, 20))
  })

  it('cancels the inline form without a mutation', async () => {
    const user = userEvent.setup()
    render(<MilestoneDependencies milestone={milestone} />)
    await screen.findByRole('button', { name: 'Ajouter un prédécesseur' })
    await user.click(screen.getByRole('button', { name: 'Ajouter un prédécesseur' }))
    expect(screen.getByRole('combobox', { name: 'Projet du prédécesseur' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.queryByRole('combobox', { name: 'Projet du prédécesseur' })).not.toBeInTheDocument()
    expect(api.createPlanningDependency).not.toHaveBeenCalled()
  })

  it('starts closed for another milestone in the keyed Sheet content', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<MilestoneDependencies key={milestone.id} milestone={milestone} />)
    await screen.findByRole('button', { name: 'Ajouter un prédécesseur' })
    await user.click(screen.getByRole('button', { name: 'Ajouter un prédécesseur' }))
    expect(screen.getByRole('combobox', { name: 'Projet du prédécesseur' })).toBeInTheDocument()
    const other = { ...milestone, id: 12, name: 'Next task' }
    rerender(<MilestoneDependencies key={other.id} milestone={other} />)
    await screen.findByRole('button', { name: 'Ajouter un prédécesseur' })
    expect(screen.queryByRole('combobox', { name: 'Projet du prédécesseur' })).not.toBeInTheDocument()
  })
})
