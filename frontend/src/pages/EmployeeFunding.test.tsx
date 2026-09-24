import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { EmployeeBudget, EmployeeContribution, EmployeeDetail } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeDetailContext } from './employeeDetailContext'
import { EmployeeFunding } from './EmployeeFunding'

const employee: EmployeeDetail = {
  id: 12, first_name: 'Jean', last_name: 'Dupont', birth_date: null, email: null,
  entry_date: null, exit_date: null, is_active: true, current_statuses: [], superiors: [],
  contract_quotity: null, project_quotity: null, contribution_quotity: '0.500', active_milestones_count: 0,
}
const contributions: EmployeeContribution[] = [
  { id: 1, fund: { id: 10, display_name: 'Atlas | ANR -> ULille', reference: 'ANR-42', project: { id: 20, name: 'Atlas' } }, cost_type: { id: 30, short_name: 'SAL', name: 'Salaire', is_hr: true }, desc: 'Valorisation chercheur', start_date: null, end_date: null, quotity: '0.500', amount: '12000.00', employee_type: null, contract_types: [], temporal_state: 'current' },
  { id: 2, fund: { id: 11, display_name: 'Beta | UE -> ULille', reference: null, project: { id: 21, name: 'Beta' } }, cost_type: { id: 30, short_name: 'SAL', name: 'Salaire', is_hr: true }, desc: null, start_date: '2027-01-01', end_date: null, quotity: '0.300', amount: '5000.00', employee_type: null, contract_types: [], temporal_state: 'future' },
  { id: 3, fund: { id: 12, display_name: 'Legacy | ANR -> ULille', reference: null, project: { id: 22, name: 'Legacy' } }, cost_type: null, desc: null, start_date: null, end_date: '2025-01-01', quotity: '0.100', amount: null, employee_type: null, contract_types: [], temporal_state: 'past' },
]
const workload = {
  range: { start: '2026-06-21', end: '2027-06-21' },
  segments: [
    { start: '2026-06-21', end: '2026-12-31', total_quotity: '0.500', contributions: [{ id: 1, quotity: '0.500', fund: { id: 10, display_name: 'Atlas | ANR -> ULille', reference: 'ANR-42' }, project: { id: 20, name: 'Atlas' }, cost_type: { id: 30, short_name: 'SAL', name: 'Salaire' } }] },
    { start: '2027-01-01', end: '2027-06-21', total_quotity: '1.300', contributions: [{ id: 1, quotity: '0.500', fund: { id: 10, display_name: 'Atlas | ANR -> ULille', reference: 'ANR-42' }, project: { id: 20, name: 'Atlas' }, cost_type: { id: 30, short_name: 'SAL', name: 'Salaire' } }, { id: 2, quotity: '0.800', fund: { id: 11, display_name: 'Beta | UE -> ULille', reference: null }, project: { id: 21, name: 'Beta' }, cost_type: { id: 30, short_name: 'SAL', name: 'Salaire' } }] },
  ],
}
const budgets: EmployeeBudget[] = [
  { id: 101, fund: { id: 40, display_name: 'Precise | ANR -> ULille', reference: 'PREC-1', project: { id: 50, name: 'Precise' } }, cost_type: { id: 30, short_name: 'SAL', name: 'Personnel chercheur', is_hr: true }, desc: 'Ingénieur de recherche', employee_type: { id: 2, code: 'ENG', name: 'Ingénieur' }, contract_types: [{ id: 3, name: 'CDD' }], quotity: '0.500', amount: '80000.00', consumed: '54000.00', available: '26000.00', consumption_ratio: '0.675' },
  { id: 102, fund: { id: 41, display_name: 'Overrun | UE -> ULille', reference: null, project: { id: 51, name: 'Overrun' } }, cost_type: { id: 30, short_name: 'SAL', name: 'Personnel chercheur', is_hr: true }, desc: null, employee_type: null, contract_types: [], quotity: null, amount: '100.00', consumed: '112.00', available: '-12.00', consumption_ratio: '1.12' },
  { id: 103, fund: { id: 42, display_name: 'Zero | ANR -> ULille', reference: null, project: { id: 52, name: 'Zero' } }, cost_type: null, desc: null, employee_type: null, contract_types: [], quotity: null, amount: '0.00', consumed: '10.00', available: '-10.00', consumption_ratio: null },
  { id: 104, fund: { id: 43, display_name: 'Refund | ANR -> ULille', reference: null, project: { id: 53, name: 'Refund' } }, cost_type: null, desc: null, employee_type: null, contract_types: [], quotity: null, amount: '40000.00', consumed: '-1000.00', available: '41000.00', consumption_ratio: '-0.025' },
]

function renderFunding(node: ReactNode = <EmployeeFunding />) {
  return render(<I18nProvider><EmployeeDetailContext.Provider value={{ employee, employeeId: '12' }}>{node}</EmployeeDetailContext.Provider></I18nProvider>)
}

describe('Employee Funding', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-09-21T12:00:00Z'))
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    localStorage.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('renders temporal groups and an accessible contribution composition', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/budgets/')) return jsonResponse([])
      return url.includes('contribution-workload') ? jsonResponse(workload) : jsonResponse(contributions)
    })
    const { container } = renderFunding()

    expect(await screen.findByRole('heading', { name: 'Contributions', level: 2 })).toBeInTheDocument()
    expect(await screen.findByRole('group', { name: 'Quotité de contribution au cours du temps' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Contributions actuelles · 1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'À venir · 1' })).toBeInTheDocument()
    expect(screen.getByText('Valorisation chercheur')).toBeInTheDocument()
    expect(screen.queryByText('Legacy | ANR -> ULille')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Historique · 1' }))
    expect(screen.getByText('Legacy | ANR -> ULille')).toBeInTheDocument()

    expect(container.querySelector('[data-threshold="100"]')).toBeInTheDocument()
    expect(container.querySelector('[data-overload="true"]')).toBeInTheDocument()
    const peak = screen.getByRole('button', { name: /Quotité contribution : 130/ })
    peak.focus()
    await user.keyboard('{Enter}')
    const detail = screen.getByRole('status')
    expect(detail).toHaveTextContent('Atlas | ANR -> ULille')
    expect(detail).toHaveTextContent('Beta | UE -> ULille')
    expect(within(detail).getByRole('button', { name: 'Fermer le détail de la période' })).toBeInTheDocument()
  })

  it('shows loading then the empty states', async () => {
    let resolveList!: (response: Response) => void
    const pendingList = new Promise<Response>((resolve) => { resolveList = resolve })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input).includes('contribution-workload')) return jsonResponse({ range: { start: '2026-06-21', end: '2027-06-21' }, segments: [] })
      if (String(input).endsWith('/budgets/')) return jsonResponse([])
      return pendingList
    })
    renderFunding()

    expect(screen.getByText('Chargement des contributions…')).toHaveAttribute('role', 'status')
    resolveList(jsonResponse([]))
    expect(await screen.findByText('Aucune contribution visible.')).toBeInTheDocument()
    expect(screen.getAllByText('Aucune contribution dans cette période.')).toHaveLength(2)
    expect(screen.getByText('Aucun budget affecté.')).toBeInTheDocument()
  })

  it('retries a local list error', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    let listAttempts = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input).includes('contribution-workload')) return jsonResponse(workload)
      if (String(input).endsWith('/budgets/')) return jsonResponse([])
      listAttempts += 1
      return listAttempts === 1 ? jsonResponse({}, 500) : jsonResponse([])
    })
    renderFunding()

    await user.click(await screen.findByRole('button', { name: 'Réessayer' }))
    expect(await screen.findByText('Aucune contribution visible.')).toBeInTheDocument()
    await waitFor(() => expect(listAttempts).toBe(2))
  })

  it('shows budget amounts, consumption, overrun and a non-calculable ratio', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('contribution-workload')) return jsonResponse(workload)
      if (url.endsWith('/contributions/')) return jsonResponse(contributions)
      if (url.endsWith('/budgets/')) return jsonResponse(budgets)
      throw new Error(`Unexpected URL ${url}`)
    })
    renderFunding()

    const normal = (await screen.findByText('Precise | ANR -> ULille')).closest('article')!
    expect(normal).toHaveTextContent(/80.?000,00/)
    expect(normal).toHaveTextContent(/54.?000,00/)
    expect(normal).toHaveTextContent(/26.?000,00/)
    expect(normal).toHaveTextContent('67,5 %')
    expect(within(normal).getByRole('progressbar', { name: 'Consommation du budget Precise | ANR -> ULille' })).toHaveValue(0.675)

    const overrun = screen.getByText('Overrun | UE -> ULille').closest('article')!
    expect(overrun).toHaveTextContent('112 %')
    expect(overrun).toHaveTextContent(/-12,00/)
    expect(within(overrun).getByRole('progressbar')).toHaveValue(1)

    const zero = screen.getByText('Zero | ANR -> ULille').closest('article')!
    expect(zero).toHaveTextContent('Taux non calculable')
    expect(within(zero).queryByRole('progressbar')).not.toBeInTheDocument()

    const refund = screen.getByText('Refund | ANR -> ULille').closest('article')!
    expect(refund).toHaveTextContent(/-1.?000,00/)
    expect(refund).toHaveTextContent(/41.?000,00/)
    expect(refund).toHaveTextContent('-2,5 %')
    expect(within(refund).queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('keeps Contributions visible during a local Budget error and retries it', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    let budgetAttempts = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('contribution-workload')) return jsonResponse(workload)
      if (url.endsWith('/contributions/')) return jsonResponse(contributions)
      if (url.endsWith('/budgets/')) {
        budgetAttempts += 1
        return budgetAttempts === 1 ? jsonResponse({}, 500) : jsonResponse([])
      }
      throw new Error(`Unexpected URL ${url}`)
    })
    renderFunding()

    expect(await screen.findByText('Valorisation chercheur')).toBeInTheDocument()
    const budgetSection = screen.getByRole('button', { name: 'Replier Budgets affectés' }).closest('section')!
    await user.click(await within(budgetSection).findByRole('button', { name: 'Réessayer' }))
    expect(await within(budgetSection).findByText('Aucun budget affecté.')).toBeInTheDocument()
    expect(budgetAttempts).toBe(2)
  })

  it('provides the Budget labels in English', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('contribution-workload')) return jsonResponse(workload)
      if (url.endsWith('/contributions/')) return jsonResponse([])
      if (url.endsWith('/budgets/')) return jsonResponse(budgets)
      throw new Error(`Unexpected URL ${url}`)
    })
    renderFunding()

    const normal = (await screen.findByText('Precise | ANR -> ULille')).closest('article')!
    expect(normal).toHaveTextContent('Budgeted')
    expect(normal).toHaveTextContent('Net expense')
    expect(normal).toHaveTextContent('Available')
    expect(screen.getByText('Rate unavailable')).toBeInTheDocument()
  })
})
