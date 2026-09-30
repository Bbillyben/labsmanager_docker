import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlanningMilestone } from '../api/planning'
import { I18nProvider } from '../i18n/I18nProvider'
import { MilestoneDetailSheet } from './MilestoneDetailSheet'

const api = vi.hoisted(() => ({ getPlanningDependencies: vi.fn() }))
vi.mock('../api/planning', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/planning')>(), getPlanningDependencies: api.getPlanningDependencies }))

const milestone: PlanningMilestone = {
  id: 8, name: 'Task', desc: null, start_date: '2026-10-01', end_date: null, status: false,
  type: 'o', quotity: '0.000', display_state: 'planned', days_to_due: null, work_kind: 'task',
  project: { id: 7, name: 'Atlas', can_view: true }, employees: [], dependencies: [],
}

beforeEach(() => {
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  api.getPlanningDependencies.mockReset()
  api.getPlanningDependencies.mockResolvedValue({
    can_add: true,
    predecessors: [{ id: 20, predecessor: { id: 6, name: 'Preparation', work_kind: 'task', start_date: null, end_date: null, project: { id: 7, name: 'Atlas' } }, successor_id: 8, temporally_inconsistent: false, can_delete: true }],
    successors: [{ id: 21, successor: { id: 9, name: 'Publication', work_kind: 'milestone', start_date: null, end_date: null, project: { id: 7, name: 'Atlas' } }, predecessor_id: 8, temporally_inconsistent: false }],
  })
})

describe('shared Planning detail', () => {
  it('links only the independently visible Project name to its React detail', async () => {
    render(<I18nProvider><MemoryRouter><Routes><Route path="/" element={<MilestoneDetailSheet milestone={milestone} onClose={vi.fn()} />} /><Route path="/projects/:projectId" element={<p>Project page</p>} /></Routes></MemoryRouter></I18nProvider>)
    const link = screen.getByRole('link', { name: 'Atlas' })
    expect(link).toHaveAttribute('href', '/projects/7')
    await userEvent.setup().click(link)
    expect(screen.getByText('Project page')).toBeInTheDocument()
  })

  it('keeps an independently inaccessible Project as plain text', () => {
    render(<I18nProvider><MemoryRouter><MilestoneDetailSheet milestone={{ ...milestone, project: { ...milestone.project, can_view: false } }} onClose={vi.fn()} /></MemoryRouter></I18nProvider>)
    expect(screen.queryByRole('link', { name: 'Atlas' })).not.toBeInTheDocument()
    expect(screen.getByText('Atlas')).toBeInTheDocument()
  })

  it('shows the same business detail in both contexts, with predecessor mutations only in Project', async () => {
    const employee = render(<I18nProvider><MemoryRouter><MilestoneDetailSheet milestone={milestone} onClose={vi.fn()} /></MemoryRouter></I18nProvider>)
    expect(await screen.findByText('Preparation')).toBeInTheDocument()
    expect(screen.getByText('Publication')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter un prédécesseur' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter un successeur' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Preparation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Publication' })).not.toBeInTheDocument()
    employee.unmount()

    render(<I18nProvider><MemoryRouter><MilestoneDetailSheet milestone={milestone} onClose={vi.fn()} manageDependencies /></MemoryRouter></I18nProvider>)
    expect(await screen.findByText('Preparation')).toBeInTheDocument()
    expect(screen.getByText('Publication')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter un prédécesseur' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter un successeur' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actions pour Preparation' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Publication' })).not.toBeInTheDocument()
  })

  it('uses the same detail Sheet for a limited Employee edit with pending and read-only dependencies', async () => {
    let finish!: (item: PlanningMilestone) => void
    const onSave = vi.fn(() => new Promise<PlanningMilestone>((resolve) => { finish = resolve }))
    const user = userEvent.setup()
    render(<I18nProvider><MemoryRouter><MilestoneDetailSheet milestone={{ ...milestone, type: 'q', quotity: '0.250', can_change: true }} onClose={vi.fn()} employeeEdit={{ canChange: true, onSave }} /></MemoryRouter></I18nProvider>)
    const sheet = screen.getByRole('dialog')
    expect(await within(sheet).findByText('Preparation')).toBeInTheDocument()
    expect(within(sheet).getByText('Publication')).toBeInTheDocument()
    expect(within(sheet).queryByRole('button', { name: 'Ajouter un prédécesseur' })).not.toBeInTheDocument()
    const edit = within(sheet).getByRole('button', { name: 'Modifier' })
    expect(edit).toHaveClass('bg-secondary')
    expect(edit.querySelector('svg.lucide-pencil')).toHaveAttribute('aria-hidden', 'true')
    expect(edit.parentElement).toContainElement(within(sheet).getByRole('heading', { name: 'Task' }))
    await user.click(edit)
    expect(within(sheet).getByRole('spinbutton', { name: 'Progression (%)' })).toHaveValue(25)
    await user.click(within(sheet).getByRole('checkbox', { name: 'Terminé' }))
    await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    expect(onSave).toHaveBeenCalledWith({ desc: null, quotity: '0.250', status: true })
    expect(within(sheet).getByRole('button', { name: 'Enregistrer' })).toBeDisabled()
    expect(within(sheet).getByRole('button', { name: 'Fermer' })).toBeDisabled()
    finish({ ...milestone, status: true, quotity: '1.000' })
    await waitFor(() => expect(within(sheet).queryByRole('button', { name: 'Enregistrer' })).not.toBeInTheDocument())
  })

  it('translates limited Employee edit controls in English', async () => {
    Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en-US'] })
    render(<I18nProvider><MemoryRouter><MilestoneDetailSheet milestone={{ ...milestone, can_change: true }} onClose={vi.fn()} employeeEdit={{ canChange: true, onSave: vi.fn() }} /></MemoryRouter></I18nProvider>)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Edit' }))
    expect(screen.getByRole('textbox', { name: 'Description' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Completed' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
  })

  it('keeps the explicit Employee edit action absent without its capability', () => {
    render(<I18nProvider><MemoryRouter><MilestoneDetailSheet milestone={milestone} onClose={vi.fn()} employeeEdit={{ canChange: false, onSave: vi.fn() }} /></MemoryRouter></I18nProvider>)
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
  })
})
