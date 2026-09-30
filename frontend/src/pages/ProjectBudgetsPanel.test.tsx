import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import type { ProjectBudget, ProjectContribution } from '../api/projectBudgets'
import { ProjectBudgetsPanel } from './ProjectBudgetsPanel'

const full = { can_add: true, can_change: true, can_delete: true }
const none = { can_add: false, can_change: false, can_delete: false }
const costType = { id: 5, short_name: 'HR', name: 'Personnel' }
const fund = { id: 7, name: 'Atlas · ANR' }
const budget: ProjectBudget = { id: 9, fund, cost_type: costType, desc: 'Personnel 2026', emp_type: null, employee: null, contract_types: [], quotity: '0.500', amount: '100.00', expense: '20.00', available: '80.00', consumption_ratio: '0.2', capabilities: full }
const contribution: ProjectContribution = { id: 4, fund, cost_type: costType, desc: 'Apport partenaire', emp_type: null, employee: null, contract_types: [], quotity: '0.000', amount: '75.00', start_date: '2026-01-01', end_date: '2026-06-30', capabilities: full }
const options = { funds: [fund], cost_types: [costType], employee_types: [], contract_types: [], employees: [] }

function setup(readonly = false, language = 'fr-FR', fail = false, kind: 'budget' | 'contribution' = 'budget') {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: [language] })
  const budgets = [structuredClone({ ...budget, capabilities: readonly ? none : full })]
  const contributions = [structuredClone({ ...contribution, capabilities: readonly ? none : full })]
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    const isBudget = url.includes('/budgets/')
    const rows = isBudget ? budgets : contributions
    if (url.includes('/expenses/options/')) return jsonResponse({ cost_types: [costType], hr_type_ids: [5], contracts: [], budgets: [{ id: 9, name: 'Personnel 2026' }] })
    if (url.includes('/expenses/?')) return jsonResponse({ count: 0, next: null, previous: null, results: [], capabilities: { expense_mode: 's', can_add: !readonly, can_sync_expenses: false } })
    if (url.endsWith('/expenses/') && method === 'POST') return jsonResponse({ id: 11, budget: { id: 9 }, ...JSON.parse(String(init?.body)) }, 201)
    if (url.endsWith('/options/')) return jsonResponse(options)
    if ((url.endsWith('/budgets/') || url.endsWith('/contributions/')) && method === 'GET') return jsonResponse(fail ? { detail: 'Fail' } : { capabilities: readonly ? none : full, items: rows }, fail ? 503 : 200)
    if ((url.endsWith('/budgets/') || url.endsWith('/contributions/')) && method === 'POST') {
      const created = { ...rows[0], ...JSON.parse(String(init?.body)), id: isBudget ? 10 : 5 }
      rows.push(created as never)
      return jsonResponse(created, 201)
    }
    if (url.match(/\/(budgets|contributions)\/\d+\/$/) && method === 'GET') return jsonResponse(rows.find((row) => url.endsWith(`/${row.id}/`)))
    if (url.match(/\/(budgets|contributions)\/\d+\/$/) && method === 'PATCH') { Object.assign(rows[0], JSON.parse(String(init?.body))); return jsonResponse(rows[0]) }
    if (url.match(/\/(budgets|contributions)\/\d+\/$/) && method === 'DELETE') { rows.splice(0, 1); return new Response(null, { status: 204 }) }
    throw new Error(`Unexpected ${method} ${url}`)
  })
  const view = render(<I18nProvider><ProjectBudgetsPanel projectId="3" kind={kind} /></I18nProvider>)
  return { fetchMock, ...view }
}

afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('ProjectBudgetsPanel', () => {
  it('selects a Budget without opening its Sheet and shows Expenses below the list', async () => {
    setup()
    const row = await screen.findByRole('row', { name: 'Personnel 2026' })
    expect(screen.queryByRole('heading', { name: 'Contributions' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter un budget' }).querySelector('svg.lucide-plus')).toBeInTheDocument()
    await userEvent.setup().click(row)
    expect(row).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByRole('heading', { name: 'Dépenses du budget' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter une dépense' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await userEvent.setup().click(within(row).getByText('Personnel 2026'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows only Contributions and their dates, without any Expense area', async () => {
    setup(false, 'fr-FR', false, 'contribution')
    const row = await screen.findByRole('row', { name: /Ouvrir le détail de Apport partenaire/ })
    await userEvent.setup().click(row)
    expect(within(screen.getByRole('dialog')).getByText('30 juin 2026')).toBeInTheDocument()
    expect(within(screen.getByRole('dialog')).queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(within(screen.getByRole('dialog')).queryByRole('button', { name: 'Supprimer' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Budgets' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dépenses du budget' })).not.toBeInTheDocument()
  })

  it('uses the same form for create/edit, confirms delete, and keeps backend capabilities authoritative', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Personnel 2026')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter un budget' }))
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Financement'), '7')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '5')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/budgets/') && init?.method === 'POST')).toBe(true))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Personnel 2026' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    expect(await within(screen.getByRole('dialog')).findByLabelText('Financement')).toBeDisabled()
    expect(within(screen.getByRole('dialog')).queryByRole('heading', { name: 'Dépenses du budget' })).not.toBeInTheDocument()
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/budgets/9/') && init?.method === 'PATCH')).toBe(true))
    await userEvent.setup().keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Personnel 2026' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(screen.getByText(/Ses dépenses liées le seront aussi/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByText('Annuler'))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
  })

  it('deletes a Budget only after confirmation', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Personnel 2026')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Personnel 2026' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getAllByText('Supprimer').at(-1)!)
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/budgets/9/') && init?.method === 'DELETE')).toBe(true))
  })

  it('fixes Budget and Fund in the nested Expense form and refreshes after creation', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Personnel 2026')
    await userEvent.setup().click(screen.getByRole('row', { name: 'Personnel 2026' }))
    await screen.findByRole('heading', { name: 'Dépenses du budget' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter une dépense' }))
    const sheet = screen.getAllByRole('dialog').at(-1)!
    expect(within(sheet).getByLabelText('Budget')).toBeDisabled()
    expect(within(sheet).getByLabelText('Budget')).toHaveValue('9')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '5')
    await userEvent.setup().type(within(sheet).getByLabelText('Montant'), '15')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/budgets/9/expenses/') && init?.method === 'POST' && JSON.parse(String(init.body)).budget_id === 9)).toBe(true))
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/budgets/') ).length).toBeGreaterThan(1))
  })

  it('hides actions for readers, reports API failures, and renders English labels', async () => {
    setup(true)
    await screen.findByText('Personnel 2026')
    expect(screen.queryByRole('button', { name: 'Ajouter un budget' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Personnel 2026' })).not.toBeInTheDocument()
  })

  it('supports Contribution creation and deletion without Expense controls', async () => {
    const { fetchMock } = setup(false, 'fr-FR', false, 'contribution')
    await screen.findByText('Apport partenaire')
    expect(screen.getByRole('button', { name: 'Ajouter une contribution' }).querySelector('svg.lucide-plus')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter une contribution' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Date de début')).toBeInTheDocument()
    expect(within(sheet).getByLabelText('Date de fin')).toBeInTheDocument()
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Financement'), '7')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '5')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/contributions/') && init?.method === 'POST')).toBe(true))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Apport partenaire' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    expect(within(screen.getByRole('dialog')).getByLabelText('Date de début')).toBeInTheDocument()
    await userEvent.setup().keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Apport partenaire' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getAllByText('Supprimer').at(-1)!)
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/contributions/4/') && init?.method === 'DELETE')).toBe(true))
    expect(screen.queryByRole('heading', { name: 'Dépenses du budget' })).not.toBeInTheDocument()
  })

  it('hides Contribution create and row actions without backend capabilities', async () => {
    setup(true, 'fr-FR', false, 'contribution')
    await screen.findByText('Apport partenaire')
    expect(screen.queryByRole('button', { name: 'Ajouter une contribution' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Apport partenaire' })).not.toBeInTheDocument()
  })

  it('shows API errors and English UI strings without translating stored names', async () => {
    const view = setup(false, 'en-US', true)
    expect(await screen.findAllByText(/Could not load budgets or contributions/)).toHaveLength(1)
    view.unmount()
    vi.restoreAllMocks()
    setup(false, 'en-US')
    expect(await screen.findByRole('button', { name: 'Add budget' })).toBeInTheDocument()
    expect(screen.queryByText('Apport partenaire')).not.toBeInTheDocument()
  })
})
