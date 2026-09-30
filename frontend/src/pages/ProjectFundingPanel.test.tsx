import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import type { Fund, FundDetail, ProjectFunding } from '../api/funding'
import { ProjectFundingPanel } from './ProjectFundingPanel'

const full = { can_add: true, can_change: true, can_delete: true }
const readonly = { can_add: false, can_change: false, can_delete: false }
const costType = { id: 5, short_name: 'HR', name: 'Human resources' }
const fund: Fund = { id: 7, funder: { id: 2, short_name: 'ANR', name: 'Agence' }, institution: { id: 3, short_name: 'UL', name: 'Université' }, ref: 'A-1', start_date: '2026-01-01', end_date: '2026-12-31', amount: '100.00', expense: '-30.00', available: '70.00', is_active: true, capabilities: full }
const totals = { amount: '100.00', expense: '-30.00', available: '70.00' }
const base: ProjectFunding = { capabilities: { can_add: true }, project_dates: { start_date: '2026-01-01', end_date: '2026-12-31' }, funds: [fund], overview: { rows: [{ type: costType, cells: { '7': totals }, total: totals }], fund_totals: { '7': totals }, grand_total: totals } }
const detail: FundDetail = { fund, summary: base.overview.rows, total: totals, items: { capabilities: full, items: [{ id: 9, type: costType, entry_date: '2026-01-01', value_date: '2026-02-01', ...totals }] }, expense_points: { capabilities: { ...full, expense_mode: 's' }, items: [{ id: 10, type: costType, entry_date: '2026-01-01', value_date: '2026-02-01', amount: '-30.00' }] } }

function setup(data: ProjectFunding = base, fundDetail: FundDetail = detail, loadStatus = 200, language = 'fr-FR') {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: [language] })
  const state = structuredClone(data)
  const selected = structuredClone(fundDetail)
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (url === '/api/v1/projects/3/funding/' && method === 'GET') return jsonResponse(loadStatus === 200 ? state : { detail: 'Unavailable' }, loadStatus)
    if (url === '/api/v1/projects/3/funding/' && method === 'POST') { const body = JSON.parse(String(init?.body)); const created = { ...fund, id: 8, ref: body.ref, start_date: body.start_date, end_date: body.end_date }; state.funds.push(created); return jsonResponse(created, 201) }
    if (url === '/api/v1/projects/3/funding/options/') return jsonResponse({ funders: [fund.funder], institutions: [fund.institution], cost_types: [costType], project_dates: state.project_dates })
    if (url === '/api/v1/projects/3/funding/funds/7/' && method === 'GET') return jsonResponse(selected)
    if (url.startsWith('/api/v1/funds/7/expenses/?')) return jsonResponse({ count: 0, next: null, previous: null, results: [], capabilities: { expense_mode: 's', can_add: false, can_sync_expenses: false } })
    if (url === '/api/v1/funds/7/expenses/options/') return jsonResponse({ cost_types: [costType], hr_type_ids: [costType.id], contracts: [], budgets: [] })
    if (url === '/api/v1/projects/3/funding/funds/7/' && method === 'PATCH') { const body = JSON.parse(String(init?.body)); selected.fund = { ...selected.fund, ...body }; state.funds[0] = selected.fund; return jsonResponse(selected.fund) }
    if (url === '/api/v1/projects/3/funding/funds/7/' && method === 'DELETE') { state.funds = []; state.overview = { rows: [], fund_totals: {}, grand_total: { amount: '0.00', expense: '0.00', available: '0.00' } }; return new Response(null, { status: 204 }) }
    if (url === '/api/v1/projects/3/funding/funds/7/items/' && method === 'POST') return jsonResponse({ id: 11, type: costType, ...JSON.parse(String(init?.body)) }, 201)
    if (url === '/api/v1/projects/3/funding/funds/7/expense-points/' && method === 'POST') return jsonResponse({ id: 12, type: costType, ...JSON.parse(String(init?.body)) }, 201)
    if (url.match(/\/funds\/7\/(items|expense-points)\/\d+\/$/) && method === 'PATCH') return jsonResponse({ id: 10, type: costType, ...JSON.parse(String(init?.body)) })
    if (url.match(/\/funds\/7\/(items|expense-points)\/\d+\/$/) && method === 'DELETE') return new Response(null, { status: 204 })
    return jsonResponse({ detail: `Unexpected ${method} ${url}` }, 404)
  })
  const view = render(<I18nProvider><ProjectFundingPanel projectId="3" /></I18nProvider>)
  return { ...view, fetchMock }
}

afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('ProjectFundingPanel', () => {
  it('shows one unified financial table below the Fund list without a duplicate detail block', async () => {
    setup()
    expect(await screen.findByText('Financements')).toBeInTheDocument()
    const row = screen.getByRole('row', { name: /ANR.*UL.*A-1/ })
    await userEvent.setup().click(within(row).getByText('ANR'))
    const summary = await screen.findByRole('table', { name: 'Synthèse financière' })
    expect(screen.queryByText('Détail : ANR · A-1')).not.toBeInTheDocument()
    expect(within(summary).getByRole('columnheader', { name: 'Ligne budgétaire' })).toBeInTheDocument()
    expect(within(summary).getByRole('columnheader', { name: 'Situation de dépense' })).toBeInTheDocument()
    expect(within(summary).getByRole('row', { name: /Human resources/ })).toHaveTextContent('70,00')
    expect(within(summary).getByRole('row', { name: /Total/ })).toHaveTextContent('70,00')
    expect(await screen.findByRole('heading', { name: 'Dépenses individuelles' })).toBeInTheDocument()
  })

  it('hides mutation controls for read-only users while retaining Fund, item and point details', async () => {
    setup({ ...base, capabilities: { can_add: false }, funds: [{ ...fund, capabilities: readonly }] }, { ...detail, fund: { ...fund, capabilities: readonly }, items: { ...detail.items, capabilities: readonly }, expense_points: { ...detail.expense_points, capabilities: { ...readonly, expense_mode: 'e' } } })
    expect(await screen.findByText('Financements')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter un financement' })).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByText('ANR'))
    expect(await screen.findByRole('table', { name: 'Synthèse financière' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions sur la synthèse financière' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Actions sur la ligne budgétaire|Actions sur la situation de dépense/ })).not.toBeInTheDocument()
  })

  it('opens the Fund Sheet and requires explicit project end-date synchronization', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Financements')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour ANR · A-1' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).queryByText('Mettre aussi à jour la date de fin du projet')).not.toBeInTheDocument()
    await userEvent.setup().clear(within(sheet).getByLabelText('Date de fin'))
    await userEvent.setup().type(within(sheet).getByLabelText('Date de fin'), '2027-03-01')
    expect(within(sheet).getByText('Mettre aussi à jour la date de fin du projet')).toBeInTheDocument()
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/funds/7/') && init?.method === 'PATCH')).toBe(true))
    const call = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/funds/7/') && init?.method === 'PATCH')!
    expect(JSON.parse(String(call[1]?.body)).update_project_end).toBe(false)
  })

  it('cancels Fund deletion and removes the selected detail only after confirmation', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Financements')
    await userEvent.setup().click(screen.getByText('ANR'))
    await screen.findByRole('table', { name: 'Synthèse financière' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour ANR · A-1' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Annuler' }))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour ANR · A-1' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(screen.queryByRole('table', { name: 'Synthèse financière' })).not.toBeInTheDocument())
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true)
    await waitFor(() => expect(document.activeElement).toHaveAttribute('id', 'project-funds-section'))
  })

  it('submits a new Fund item from the selected Fund and confirms child deletion', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Financements')
    await userEvent.setup().click(screen.getByText('ANR'))
    await screen.findByRole('table', { name: 'Synthèse financière' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la synthèse financière' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Ajouter une ligne budgétaire' }))
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '5')
    await userEvent.setup().type(within(sheet).getByLabelText('Montant'), '25')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/items/') && init?.method === 'POST')).toBe(true))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la ligne budgétaire Human resources' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/items/9/') && init?.method === 'DELETE')).toBe(true))
    await waitFor(() => expect(document.activeElement).toHaveAttribute('aria-labelledby', 'fund-summary-heading'))
  })

  it('shows an Expense point read-only in expense mode and hides its add control', async () => {
    setup(base, { ...detail, expense_points: { ...detail.expense_points, capabilities: { can_add: false, can_change: false, can_delete: false, expense_mode: 'e' } } })
    await screen.findByText('Financements')
    await userEvent.setup().click(screen.getByText('ANR'))
    expect(await screen.findByRole('table', { name: 'Synthèse financière' })).toBeInTheDocument()
    expect(screen.getAllByText(/-30,00/).length).toBeGreaterThan(0)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la synthèse financière' }))
    expect(screen.queryByRole('menuitem', { name: 'Ajouter une situation de dépense' })).not.toBeInTheDocument()
  })

  it('shows empty and retryable error states without financial calculations in React', async () => {
    const empty = { ...base, funds: [], overview: { rows: [], fund_totals: {}, grand_total: { amount: '0.00', expense: '0.00', available: '0.00' } } }
    const view = setup(empty)
    expect(await screen.findAllByText('Aucun financement visible.')).toHaveLength(1)
    view.unmount()
    setup(base, detail, 503)
    expect(await screen.findByText('Impossible de charger les financements.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })

  it('creates a Fund with the Project dates as defaults', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Financements')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter un financement' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Date de début')).toHaveValue('2026-01-01')
    expect(within(sheet).getByLabelText('Date de fin')).toHaveValue('2026-12-31')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Financeur'), '2')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Institution gestionnaire'), '3')
    await userEvent.setup().type(within(sheet).getByLabelText('Référence'), 'B-2')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url) === '/api/v1/projects/3/funding/' && init?.method === 'POST')).toBe(true))
  })

  it('submits Expense point create and edit only when backend capabilities permit it', async () => {
    const { fetchMock } = setup()
    await screen.findByText('Financements')
    await userEvent.setup().click(screen.getByText('ANR'))
    await screen.findByRole('table', { name: 'Synthèse financière' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la synthèse financière' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Ajouter une situation de dépense' }))
    let sheet = screen.getByRole('dialog')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '5')
    await userEvent.setup().type(within(sheet).getByLabelText('Montant'), '15')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/expense-points/') && init?.method === 'POST')).toBe(true))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la situation de dépense Human resources' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    sheet = screen.getByRole('dialog')
    await userEvent.setup().clear(within(sheet).getByLabelText('Montant'))
    await userEvent.setup().type(within(sheet).getByLabelText('Montant'), '20')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/expense-points/10/') && init?.method === 'PATCH')).toBe(true))
  })

  it('distinguishes missing objects from real zero amounts without creating a counterpart', async () => {
    const item = detail.items.items[0]
    const point = detail.expense_points.items[0]
    const itemOnly = { ...item, amount: '0.00', expense: '0.00', available: '0.00' }
    const pointOnly = { ...point, id: 12, type: { id: 6, short_name: 'TR', name: 'Travel' }, amount: '-5.00' }
    setup(base, { ...detail, summary: [{ type: costType, cells: {}, total: { amount: '0.00', expense: '0.00', available: '0.00' } }], items: { ...detail.items, items: [itemOnly] }, expense_points: { ...detail.expense_points, items: [pointOnly] } })
    await userEvent.setup().click(await screen.findByText('ANR'))
    const table = await screen.findByRole('table', { name: 'Synthèse financière' })
    const itemRow = within(table).getByRole('row', { name: /Human resources/ })
    const pointRow = within(table).getByRole('row', { name: /Travel/ })
    expect(itemRow).toHaveTextContent('0,00')
    expect(within(itemRow).getAllByText('—')).toHaveLength(2)
    expect(within(pointRow).getAllByText('—')).toHaveLength(2)
    expect(pointRow).toHaveTextContent('-5,00')
    expect(within(table).queryByRole('row', { name: /Equipment/ })).not.toBeInTheDocument()
  })

  it('shows only the permitted global creation action and keeps object menus separate', async () => {
    setup(base, { ...detail, items: { ...detail.items, capabilities: { ...full, can_add: false } } })
    await userEvent.setup().click(await screen.findByText('ANR'))
    await screen.findByRole('table', { name: 'Synthèse financière' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la synthèse financière' }))
    expect(screen.queryByRole('menuitem', { name: 'Ajouter une ligne budgétaire' })).not.toBeInTheDocument()
    expect(await screen.findByRole('menuitem', { name: 'Ajouter une situation de dépense' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actions sur la ligne budgétaire Human resources' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actions sur la situation de dépense Human resources' })).toBeInTheDocument()
  })

  it('shows no financial object row when neither Fund_Item nor Expense_point exists', async () => {
    setup(base, { ...detail, summary: [], items: { ...detail.items, items: [] }, expense_points: { ...detail.expense_points, items: [] } })
    await userEvent.setup().click(await screen.findByText('ANR'))
    const table = await screen.findByRole('table', { name: 'Synthèse financière' })
    expect(within(table).queryByRole('row', { name: /Human resources/ })).not.toBeInTheDocument()
    expect(within(table).getByRole('row', { name: /Total/ })).toBeInTheDocument()
  })

  it('renders the unified summary actions in English', async () => {
    setup(base, detail, 200, 'en-US')
    await userEvent.setup().click(await screen.findByText('ANR'))
    const table = await screen.findByRole('table', { name: 'Financial overview' })
    expect(within(table).getByRole('columnheader', { name: 'Fund item' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Financial summary actions' }))
    expect(await screen.findByRole('menuitem', { name: 'Add a fund item' })).toBeInTheDocument()
  })

  it('opens the global menu by keyboard and restores focus after cancelling its Sheet', async () => {
    setup()
    await userEvent.setup().click(await screen.findByText('ANR'))
    const trigger = await screen.findByRole('button', { name: 'Actions sur la synthèse financière' })
    trigger.focus()
    await userEvent.setup().keyboard('{Enter}')
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Ajouter une ligne budgétaire' }))
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Annuler' }))
    await waitFor(() => expect(document.activeElement).toBe(trigger))
  })

  it('keeps the expense point menu available in hybrid mode', async () => {
    setup(base, { ...detail, expense_points: { ...detail.expense_points, capabilities: { ...full, expense_mode: 'h' } } })
    await userEvent.setup().click(await screen.findByText('ANR'))
    expect(await screen.findByRole('button', { name: 'Actions sur la situation de dépense Human resources' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions sur la synthèse financière' }))
    expect(await screen.findByRole('menuitem', { name: 'Ajouter une situation de dépense' })).toBeInTheDocument()
  })
})
