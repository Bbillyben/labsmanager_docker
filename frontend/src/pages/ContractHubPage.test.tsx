import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { ContractHubPage } from './ContractHubPage'

const contract = {
  id: 1, admin_url: '/admin/expense/contract/1/change/',
  employee: { id: 12, first_name: 'Jean', last_name: 'Dupont', can_view: true },
  contract_type: { id: 2, name: 'CDD Recherche' },
  fund: { id: 20, display_name: 'Atlas · ANR', reference: 'REF-20',
    project: { id: 3, name: 'Atlas', can_view: true, url: null },
    funder: { id: 30, name: 'Agence nationale', short_name: 'ANR', can_view: false, url: null },
    institution: { id: 40, name: 'Université', short_name: 'UL', can_view: false, url: null } },
  start_date: '2026-01-01', end_date: '2026-12-31', quotity: '0.500',
  status: { code: 'effe', label: 'Effective' }, requires_follow_up: true, is_active: true,
  temporal_state: 'current', total_amount: '25.00', capabilities: { can_change: false }, notes: { visible_count: 0, can_add: false },
}
const options = { contract_types: [{ id: 2, name: 'CDD Recherche' }], statuses: [{ value: 'effe', label: 'Effective' }], funders: [{ id: 30, short_name: 'ANR' }], institutions: [{ id: 40, short_name: 'UL' }] }
const editOptions = { employees: [{ id: 12, name: 'Jean Dupont' }], funds: [{ id: 20, name: 'Atlas · ANR', project_id: 3 }], contract_types: options.contract_types }
const detail = { ...contract, capabilities: { can_add: false, can_change: true, can_delete: false }, notes: { visible_count: 0, can_add: false }, remain_amount: '12.50', man_month: '6.000' }

function setup(editable = false, path = '/tools/contracts?active=true', paginated = false, noteSummary = contract.notes) {
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v1/notes/contract/1/') return jsonResponse({ capabilities: { can_add: noteSummary.can_add }, items: [
      { id: 9, name: 'Suivi', note: '<p>Texte</p>', visibility: 'object', creator: { id: 2, name: 'Alice' }, created_at: '2026-01-01T12:00:00Z', updated_at: '2026-01-01T12:00:00Z', capabilities: { can_change: false, can_rename: false, can_delete: false, can_change_visibility: false } },
      { id: 10, name: 'Suite', note: '<p>Suite</p>', visibility: 'object', creator: { id: 2, name: 'Alice' }, created_at: '2026-01-01T12:00:00Z', updated_at: '2026-01-01T12:00:00Z', capabilities: { can_change: false, can_rename: false, can_delete: false, can_change_visibility: false } },
    ].slice(0, noteSummary.visible_count) })
    if (url.startsWith('/api/v1/contracts/export/')) return new Response('csv', { status: 200, headers: { 'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename="Contract.csv"' } })
    if (url === '/api/v1/contracts/filter-options/') return jsonResponse(options)
    if (url.endsWith('/expenses/options/')) return jsonResponse({ cost_types: [], hr_type_ids: [], contracts: [{ id: 1, name: 'Jean Dupont' }], budgets: [] })
    if (url.includes('/expenses/?')) return jsonResponse({ count: 0, next: null, previous: null, results: [], capabilities: { expense_mode: 's', can_add: false, can_sync_expenses: false } })
    if (url === '/api/v1/contracts/1/options/') return jsonResponse(editOptions)
    if (url === '/api/v1/contracts/1/' && init?.method === 'PATCH') return jsonResponse({ ...detail, quotity: '0.750', employee_end_date_sync: null })
    if (url === '/api/v1/contracts/1/') return jsonResponse({ ...detail, capabilities: { can_add: false, can_change: editable, can_delete: false } })
    if (url.startsWith('/api/v1/contracts/?')) return jsonResponse({ count: paginated ? 40 : 1, next: paginated ? '/next/' : null, previous: null, results: [{ ...contract, capabilities: { can_change: editable }, notes: noteSummary }] })
    throw new Error(`Unexpected ${url}`)
  })
  const view = render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/tools/contracts" element={<ContractHubPage />} />
    <Route path="/employees/:id" element={<p>Employee profile</p>} />
    <Route path="/projects/:id" element={<p>Project profile</p>} />
  </Routes></MemoryRouter></I18nProvider>)
  return { fetch, ...view }
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

describe('Contract Hub', () => {
  it('accumulates and removes canonical filters, then sorts and pages through URL requests', async () => {
    const { fetch } = setup(false, '/tools/contracts', true)
    const user = userEvent.setup()
    await screen.findByRole('row', { name: /Jean Dupont/ })
    await user.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await user.click(within(screen.getByRole('dialog', { name: 'Ajouter un filtre' })).getByRole('button', { name: 'Actif' }))
    await user.selectOptions(screen.getByLabelText('Actif'), 'false')
    await user.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await user.click(within(screen.getByRole('dialog', { name: 'Ajouter un filtre' })).getByRole('button', { name: 'En cours' }))
    await user.selectOptions(screen.getByLabelText('En cours'), 'true')
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('active=false') && String(input).includes('ongoing=true'))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Supprimer le filtre actif' }))
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('ongoing=true') && !String(input).includes('active='))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }))
    await user.click(screen.getByRole('button', { name: /Trier par identité/i }))
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('ordering=-employee__last_name'))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Suivant' }))
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('offset=25'))).toBe(true))
  })

  it('uses shared URL filters, sorting and export without Contract creation or deletion', async () => {
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:contracts') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const { fetch } = setup(false, '/tools/contracts?active=true&ongoing=false&employee=12&project=3&ordering=-start_date&limit=10&offset=20')
    const row = await screen.findByRole('row', { name: /Jean Dupont/ })
    expect(within(row).getByRole('link', { name: 'Jean Dupont' })).toHaveAttribute('href', '/employees/12')
    expect(within(row).getByRole('link', { name: 'Atlas' })).toHaveAttribute('href', '/projects/3')
    expect(screen.queryByRole('button', { name: /Ajouter un contrat/i })).not.toBeInTheDocument()
    const listUrl = String(fetch.mock.calls.find(([input]) => String(input).startsWith('/api/v1/contracts/?'))?.[0])
    expect(listUrl).toContain('active=true')
    expect(listUrl).toContain('ongoing=false')
    expect(listUrl).toContain('employee=12')
    expect(listUrl).toContain('project=3')
    expect(listUrl).toContain('ordering=-start_date')
    expect(listUrl).toContain('offset=20')
    await userEvent.click(within(row).getByRole('button', { name: /Actions pour/ }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })).toHaveAttribute('href', '/admin/expense/contract/1/change/')
    expect(screen.queryByRole('menuitem', { name: 'Supprimer' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Modifier' })).not.toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    await userEvent.click(screen.getByRole('button', { name: 'Exporter' }))
    await userEvent.click(screen.getByRole('button', { name: 'Télécharger' }))
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).startsWith('/api/v1/contracts/export/'))).toBe(true))
    const exportUrl = String(fetch.mock.calls.find(([input]) => String(input).startsWith('/api/v1/contracts/export/'))?.[0])
    expect(exportUrl).toContain('ongoing=false')
    expect(exportUrl).toContain('format=xlsx')
    expect(exportUrl).not.toContain('offset=')
    expect(exportUrl).not.toContain('limit=')
  })

  it('selects a row for the shared detail and opens the existing Edit Sheet when allowed', async () => {
    const { fetch } = setup(true)
    const user = userEvent.setup()
    const row = await screen.findByRole('row', { name: /Jean Dupont/ })
    await user.click(within(row).getByText('CDD Recherche'))
    expect(await screen.findByRole('heading', { name: 'Détail du contrat' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Dépenses liées' })).toBeInTheDocument()
    expect(fetch.mock.calls.some(([input]) => String(input) === '/api/v1/contracts/1/expenses/?page=1')).toBe(true)
    await user.click(within(row).getByRole('button', { name: /Actions pour/ }))
    await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Modifier')
    expect(screen.queryByRole('menuitem', { name: 'Supprimer' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetch.mock.calls.some(([input, init]) => String(input) === '/api/v1/contracts/1/' && init?.method === 'PATCH')).toBe(true))
  })

  it('opens the shared Notes Sheet directly from the row and refreshes the grouped count on close', async () => {
    const { fetch } = setup(false, '/tools/contracts', false, { visible_count: 2, can_add: false })
    const user = userEvent.setup()
    const row = await screen.findByRole('row', { name: /Jean Dupont/ })
    const open = within(row).getByRole('button', { name: 'Ouvrir les notes du contrat · 2 notes' })
    expect(open).toHaveTextContent('2')
    await user.click(open)
    const sheet = await screen.findByRole('dialog', { name: 'Notes du contrat' })
    expect(fetch.mock.calls.some(([input]) => String(input) === '/api/v1/notes/contract/1/')).toBe(true)
    expect(screen.queryByRole('heading', { name: 'Détail du contrat' })).not.toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Notes du contrat' })).not.toBeInTheDocument())
    await waitFor(() => expect(fetch.mock.calls.filter(([input]) => String(input).startsWith('/api/v1/contracts/?'))).toHaveLength(2))
    await user.click(within(row).getByText('CDD Recherche'))
    expect(await screen.findByRole('heading', { name: 'Détail du contrat' })).toBeInTheDocument()
  })

  it('shows an icon without zero when notes may be added', async () => {
    setup(false, '/tools/contracts', false, { visible_count: 0, can_add: true })
    const row = await screen.findByRole('row', { name: /Jean Dupont/ })
    expect(within(row).getByRole('button', { name: 'Ouvrir les notes du contrat' })).not.toHaveTextContent('0')
  })

  it('hides Notes when no visible note or add permission exists', async () => {
    setup()
    const row = await screen.findByRole('row', { name: /Jean Dupont/ })
    expect(within(row).queryByRole('button', { name: 'Ouvrir les notes du contrat' })).not.toBeInTheDocument()
  })
})
