import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlanningMilestone } from '../api/planning'
import { I18nProvider } from '../i18n/I18nProvider'
import { PlanningMilestoneTable } from './PlanningMilestoneTable'

const milestone: PlanningMilestone = {
  id: 8, name: 'Budget report', desc: null, start_date: null, end_date: '2026-09-15',
  status: false, type: 'q', quotity: '0.500', display_state: 'overdue', days_to_due: -2,
  work_kind: 'milestone', project: { id: 7, name: 'Atlas', can_view: false },
  employees: [{ id: 1, first_name: 'Ada', last_name: 'Lovelace', can_view: true },
    { id: 2, first_name: 'Grace', last_name: 'Hopper', can_view: false }],
  dependencies: [],
}

beforeEach(() => Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr'] }))

function renderTable(data: PlanningMilestone[] | null, error: unknown = null, loading = false) {
  const retry = vi.fn()
  render(<I18nProvider><PlanningMilestoneTable resource={{ data, error, loading, retry }} /></I18nProvider>)
  return retry
}

describe('shared Planning milestone table', () => {
  it('keeps normal rows dense and uses whole-row selection only in delay mode', async () => {
    const onToggle = vi.fn()
    const onOpen = vi.fn()
    const { rerender } = render(<I18nProvider><PlanningMilestoneTable resource={{ data: [milestone], error: null, loading: false, retry: vi.fn() }} onOpen={onOpen} /></I18nProvider>)
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sélectionner « Budget report » pour le décalage' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Ouvrir le détail de Budget report' }))
    expect(onOpen).toHaveBeenCalledWith(milestone)
    rerender(<I18nProvider><PlanningMilestoneTable resource={{ data: [milestone], error: null, loading: false, retry: vi.fn() }} onOpen={onOpen} delaySelection={{ selectedIds: [], onToggle }} /></I18nProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Sélectionner « Budget report » pour le décalage' }))
    expect(onToggle).toHaveBeenCalledWith(8)
    expect(onOpen).toHaveBeenCalledTimes(1)
    rerender(<I18nProvider><PlanningMilestoneTable resource={{ data: [milestone], error: null, loading: false, retry: vi.fn() }} onOpen={onOpen} delaySelection={{ selectedIds: [8], onToggle }} /></I18nProvider>)
    const selected = screen.getByRole('button', { name: 'Retirer « Budget report » de la sélection' })
    expect(selected).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(selected)
    expect(onToggle).toHaveBeenCalledTimes(2)
    rerender(<I18nProvider><PlanningMilestoneTable resource={{ data: [{ ...milestone, status: true }], error: null, loading: false, retry: vi.fn() }} delaySelection={{ selectedIds: [], onToggle }} /></I18nProvider>)
    expect(screen.getByRole('button', { name: 'Sélectionner « Budget report » pour le décalage' })).toBeDisabled()
  })
  it('offers single delay only on editable unfinished rows with an end date', async () => {
    const onDelay = vi.fn()
    const actions = { canChange: true, canDelete: false, onEdit: vi.fn(), onDelete: vi.fn(), onDelay }
    const { rerender } = render(<I18nProvider><PlanningMilestoneTable resource={{ data: [milestone], error: null, loading: false, retry: vi.fn() }} actions={actions} /></I18nProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Budget report' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Décaler ce jalon…' }))
    expect(onDelay).toHaveBeenCalledWith(milestone)
    rerender(<I18nProvider><PlanningMilestoneTable resource={{ data: [{ ...milestone, status: true }], error: null, loading: false, retry: vi.fn() }} actions={actions} /></I18nProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Budget report' }))
    expect(screen.queryByRole('menuitem', { name: 'Décaler ce jalon…' })).not.toBeInTheDocument()
    rerender(<I18nProvider><PlanningMilestoneTable resource={{ data: [{ ...milestone, end_date: null }], error: null, loading: false, retry: vi.fn() }} actions={{ ...actions, canChange: false }} /></I18nProvider>)
    expect(screen.queryByRole('menuitem', { name: 'Décaler ce jalon…' })).not.toBeInTheDocument()
  })
  it('shows the Admin link for a Milestone even when the Employee view has no business actions', async () => {
    renderTable([{ ...milestone, admin_url: '/admin/endpoints/milestones/8/change/' }])
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Budget report' }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })).toHaveAttribute('href', '/admin/endpoints/milestones/8/change/')
  })
  it('renders backend state, progress and compact assignees without assuming a scope', () => {
    renderTable([milestone])
    expect(screen.getByRole('button', { name: 'En retard · 1' })).toBeInTheDocument()
    const row = screen.getByRole('button', { name: 'Ouvrir le détail de Budget report' })
    expect(within(row).getByText(/Atlas · Jalon/)).toBeInTheDocument()
    expect(within(row).getByText('Personnes assignées: Ada Lovelace, Grace Hopper')).toBeInTheDocument()
    expect(within(row).getByRole('progressbar')).toHaveValue(50)
  })

  it('keeps local empty, loading and retry states', () => {
    const { unmount } = render(<I18nProvider><PlanningMilestoneTable resource={{ data: [], error: null, loading: false, retry: vi.fn() }} /></I18nProvider>)
    expect(screen.getByText('Aucun jalon ou tâche assigné.')).toBeInTheDocument()
    unmount()
    renderTable(null, new Error('offline'))
    expect(screen.getByRole('alert')).toHaveTextContent('Données momentanément indisponibles.')
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})
