import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { EmployeeContract, EmployeeContractDetail, EmployeeDetail } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeContracts } from './EmployeeContracts'
import { EmployeeDetailContext } from './employeeDetailContext'

const employee: EmployeeDetail = {
  id: 12, first_name: 'Jean', last_name: 'Dupont', birth_date: null, email: null,
  entry_date: null, exit_date: null, is_active: true, current_statuses: [], superiors: [],
  contract_quotity: '0.500', project_quotity: null, contribution_quotity: null, active_milestones_count: 0,
}
const organization = (id: number, name: string, canView: boolean) => ({
  id, short_name: name.slice(0, 3).toUpperCase(), name, can_view: canView,
  url: canView ? `/infos/project/institution/${id}` : null,
})
const contract = (id: number, state: EmployeeContract['temporal_state'], extra: Partial<EmployeeContract> = {}): EmployeeContract => ({
  id,
  employee: { id: 12, first_name: 'Jean', last_name: 'Dupont' },
  contract_type: { id: 1, name: id === 1 ? 'CDD Recherche' : `Contrat ${id}` },
  fund: {
    id: 20 + id,
    display_name: `Projet Atlas | ANR -> Université ${id}`,
    reference: `REF-${id}`,
    project: { id: 30, name: 'Projet Atlas', can_view: false, url: null },
    funder: organization(40, 'Agence nationale', true),
    institution: organization(50 + id, id === 1 ? 'Université de Lille' : 'Institut contextuel', id === 1),
  },
  start_date: state === 'future' ? '2027-01-01' : '2025-01-01',
  end_date: state === 'past' ? '2025-12-31' : '2027-12-31',
  quotity: '0.500',
  status: { code: state === 'future' ? 'prov' : 'effe', label: state === 'future' ? 'Provisionnal' : 'Effective' },
  requires_follow_up: id === 1,
  temporal_state: state,
  ...extra,
})
const contracts = [contract(1, 'current'), contract(2, 'current'), contract(3, 'future'), contract(4, 'past')]
const detail: EmployeeContractDetail = {
  ...contracts[0],
  expense_count: 2,
  expense_total: '100.00',
  expenses: [
    { id: 1, expense_id: 'PAY-1', date: '2026-09-01', desc: 'Salaire septembre', type: { id: 1, short_name: 'SAL', name: 'Salaire' }, amount: '120.00' },
    { id: 2, expense_id: null, date: '2026-08-01', desc: null, type: { id: 2, short_name: 'COR', name: 'Correction' }, amount: '-20.00' },
  ],
}

function renderPanel(fetchImpl?: (url: string) => Promise<Response>) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (fetchImpl) return fetchImpl(url)
    if (url.endsWith('/contracts/')) return jsonResponse(contracts)
    if (url.endsWith('/contracts/1/')) return jsonResponse(detail)
    if (url.match(/\/contracts\/\d+\/$/)) return jsonResponse({ ...detail, ...contracts.find((item) => url.endsWith(`/contracts/${item.id}/`)), expenses: [], expense_count: 0, expense_total: '0.00' })
    throw new Error(`Unexpected URL ${url}`)
  })
  return render(<I18nProvider><BrowserRouter><EmployeeDetailContext.Provider value={{ employee, employeeId: '12' }}><EmployeeContracts /></EmployeeDetailContext.Provider></BrowserRouter></I18nProvider>)
}

describe('Employee Contracts panel', () => {
  beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
  afterEach(() => vi.restoreAllMocks())

  it('groups contracts, emphasizes Institution and keeps history compact', async () => {
    const user = userEvent.setup()
    renderPanel()

    expect(await screen.findByRole('heading', { name: /Contrats en cours · 2/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /À venir · 1/ })).toBeInTheDocument()
    const institutionLink = screen.getByRole('link', { name: 'Université de Lille' })
    expect(institutionLink).toHaveAttribute('href', '/infos/project/institution/51')
    fireEvent.click(institutionLink, { button: 1 })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getAllByText('Institut contextuel')).toHaveLength(2)
    expect(screen.queryByRole('link', { name: 'Institut contextuel' })).not.toBeInTheDocument()
    expect(screen.getAllByText('50 %').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Suivi RH')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: /Contrat 4/ })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Historique · 1/ }))
    expect(screen.getByRole('button', { name: /Ouvrir le détail du contrat Contrat 4/ })).toBeInTheDocument()
  })

  it('opens the detail Sheet by click and shows only the simple expense synthesis', async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(await screen.findByRole('button', { name: 'Ouvrir le détail du contrat CDD Recherche' }))
    const sheet = await screen.findByRole('dialog')
    expect(within(sheet).getByRole('heading', { name: 'CDD Recherche' })).toBeInTheDocument()
    expect(within(sheet).getByText('Université de Lille')).toBeInTheDocument()
    expect(within(sheet).getByText('Salaire septembre')).toBeInTheDocument()
    expect(within(sheet).getByText('Correction')).toBeInTheDocument()
    expect(within(sheet).getByText(/Total\s*:\s*100,00/)).toBeInTheDocument()
    expect(within(sheet).queryByText(/Engaged|Realised|Projected|Engagé|Réalisé/)).not.toBeInTheDocument()
  })

  it('opens by keyboard and renders the empty expense state', async () => {
    const user = userEvent.setup()
    renderPanel()
    const open = await screen.findByRole('button', { name: 'Ouvrir le détail du contrat Contrat 2' })
    open.focus()
    await user.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { name: 'Contrat 2' })).toBeInTheDocument()
    expect(await screen.findByText('Aucune dépense liée.')).toBeInTheDocument()
  })

  it('keeps a detail failure local to the Sheet and retries it', async () => {
    let detailFailed = false
    const user = userEvent.setup()
    renderPanel(async (url) => {
      if (url.endsWith('/contracts/')) return jsonResponse(contracts)
      if (url.endsWith('/contracts/1/')) {
        if (!detailFailed) { detailFailed = true; return jsonResponse({}, 500) }
        return jsonResponse(detail)
      }
      throw new Error(`Unexpected URL ${url}`)
    })
    await user.click(await screen.findByRole('button', { name: 'Ouvrir le détail du contrat CDD Recherche' }))
    const sheet = await screen.findByRole('dialog')
    await user.click(await within(sheet).findByRole('button', { name: 'Réessayer' }))

    expect(await within(sheet).findByText('Salaire septembre')).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Fermer' }))
    expect(screen.getByRole('heading', { name: /Contrats en cours · 2/ })).toBeInTheDocument()
  })

  it('shows initial loading and a retryable local error', async () => {
    let resolveList!: (response: Response) => void
    let failed = false
    renderPanel(async (url) => {
      if (!url.endsWith('/contracts/')) throw new Error(`Unexpected URL ${url}`)
      if (!failed) {
        failed = true
        return new Promise<Response>((resolve) => { resolveList = resolve })
      }
      return jsonResponse([])
    })
    expect(screen.getByRole('status')).toHaveTextContent('Chargement des contrats…')
    resolveList(jsonResponse({}, 500))
    const alert = await screen.findByRole('alert')
    await userEvent.setup().click(within(alert).getByRole('button', { name: 'Réessayer' }))
    expect(await screen.findByText('Aucun contrat visible.')).toBeInTheDocument()
  })
})
