import { render, screen, within } from '@testing-library/react'
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
