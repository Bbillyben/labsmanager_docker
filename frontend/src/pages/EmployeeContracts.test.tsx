import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ContractRecord, EmployeeEndDateSyncOffer } from '../api/contracts'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { ContractSection } from './ContractSection'
import { EmployeeContracts } from './EmployeeContracts'
import { EmployeeDetailContext } from './employeeDetailContext'
import type { EmployeeDetail } from '../api/employees'

vi.mock('../components/ProseEditor', () => ({ ProseEditor: ({ initialHtml, onChange }: { initialHtml: string; onChange: (value: string) => void }) => <input aria-label="Editor" defaultValue={initialHtml} onChange={(event) => onChange(event.target.value)} /> }))

const full = { can_add: true, can_change: true, can_delete: true }
const none = { can_add: false, can_change: false, can_delete: false }
const contract: ContractRecord = {
  id: 1, employee: { id: 12, first_name: 'Jean', last_name: 'Dupont', can_view: true },
  contract_type: { id: 2, name: 'CDD Recherche' },
  fund: { id: 20, display_name: 'Atlas · ANR', reference: 'REF-20',
    project: { id: 3, name: 'Atlas', can_view: true, url: null },
    funder: { id: 30, name: 'Agence nationale', short_name: 'ANR', can_view: false, url: null },
    institution: { id: 40, name: 'Université de Lille', short_name: 'UL', can_view: true, url: '/infos/project/institution/40' } },
  start_date: '2026-01-01', end_date: '2026-12-31', quotity: '0.500', status: { code: 'effe', label: 'Effective' },
  requires_follow_up: true, temporal_state: 'current', capabilities: full,
  notes: { visible_count: 0, can_add: false },
}
const detail = { ...contract, total_amount: '25.00', remain_amount: '12.50', man_month: '6.000' }
const options = { employees: [{ id: 12, name: 'Jean Dupont' }], funds: [{ id: 20, name: 'Atlas · ANR', project_id: 3 }], contract_types: [{ id: 2, name: 'CDD Recherche' }] }
const employee: EmployeeDetail = { id: 12, first_name: 'Jean', last_name: 'Dupont', birth_date: null, email: null,
  entry_date: null, exit_date: null, is_active: true, current_statuses: [], superiors: [], contract_quotity: '0.500',
  project_quotity: null, contribution_quotity: null, active_milestones_count: 0 }

function setup(kind: 'project' | 'employee', allowed = true, offer: EmployeeEndDateSyncOffer | null = null, noteSummary = contract.notes, adminUrl: string | null = null) {
  const rows = [{ ...contract, admin_url: adminUrl, capabilities: allowed ? full : none, notes: { ...noteSummary } }]
  const noteRows = [{ id: 9, name: 'Suivi', note: '<p>Texte</p>', visibility: 'object', creator: { id: 2, name: 'Alice' }, created_at: '2026-01-01T12:00:00Z', updated_at: '2026-01-01T12:00:00Z', capabilities: { can_change: true, can_rename: true, can_delete: true, can_change_visibility: true } }]
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (url.endsWith('/notes/contract/1/') && method === 'GET') return jsonResponse({ capabilities: { can_add: noteSummary.can_add }, items: rows[0].notes.visible_count ? noteRows : [] })
    if (url.endsWith('/notes/contract/1/') && method === 'POST') { const note = { ...noteRows[0], ...JSON.parse(String(init?.body)), id: 10, note: '' }; noteRows.push(note); rows[0].notes.visible_count++; return jsonResponse(note, 201) }
    if (url.includes('/notes/contract/1/') && method === 'PATCH') { const note = noteRows.find((item) => url.endsWith(`/${item.id}/`))!; Object.assign(note, JSON.parse(String(init?.body))); return jsonResponse(note) }
    if (url.includes('/notes/contract/1/') && method === 'DELETE') { noteRows.splice(noteRows.findIndex((item) => url.endsWith(`/${item.id}/`)), 1); rows[0].notes.visible_count--; return new Response(null, { status: 204 }) }
    if (url.endsWith('/expenses/options/')) return jsonResponse({ cost_types: [{ id: 5, short_name: 'HR', name: 'Personnel' }], hr_type_ids: [5], contracts: [{ id: 1, name: 'Jean Dupont' }], budgets: [] })
    if (url.includes('/expenses/?')) return jsonResponse({ count: 0, next: null, previous: null, results: [], capabilities: { expense_mode: 'e', can_add: allowed, can_sync_expenses: false } })
    if (url.includes('/expenses/') && method === 'POST') return jsonResponse({ id: 10, ...JSON.parse(String(init?.body)) }, 201)
    if (url.endsWith('/contracts/capabilities/')) return jsonResponse(allowed ? full : none)
    if (url.endsWith('/contracts/options/')) return jsonResponse(options)
    if (url.endsWith('/sync-employee-end-date/') && method === 'POST') return jsonResponse({ employee_id: 12, end_date: offer?.proposed_end_date })
    if (url.endsWith('/contracts/') && method === 'GET') return jsonResponse(kind === 'project' ? { items: rows, capabilities: allowed ? full : none } : rows)
    if (url.endsWith('/contracts/') && method === 'POST') { const item = { ...contract, ...JSON.parse(String(init?.body)), id: 2 }; rows.push(item); return jsonResponse(item, 201) }
    if (url.endsWith('/contracts/1/') && method === 'GET') return jsonResponse({ ...detail, capabilities: allowed ? full : none })
    if (url.endsWith('/contracts/1/') && method === 'PATCH') return jsonResponse({ ...detail, ...JSON.parse(String(init?.body)), employee_end_date_sync: offer })
    if (url.endsWith('/contracts/1/') && method === 'DELETE') { rows.splice(0, 1); return new Response(null, { status: 204 }) }
    if (url.endsWith('/contracts/2/') && method === 'GET') return jsonResponse(rows[1])
    throw new Error(`Unexpected ${method} ${url}`)
  })
  const view = render(<I18nProvider><BrowserRouter>{kind === 'project'
    ? <ContractSection scope={{ projectId: '3' }} />
    : <EmployeeDetailContext.Provider value={{ employee, employeeId: '12' }}><EmployeeContracts /></EmployeeDetailContext.Provider>}
  </BrowserRouter></I18nProvider>)
  return { fetchMock, ...view }
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('shared Contract section', () => {
  it('shows the backend Admin link for a Contract in the row menu', async () => {
    setup('project', false, null, contract.notes, '/admin/expense/contract/1/change/')
    const row = await screen.findByRole('row', { name: 'CDD Recherche' })
    await userEvent.click(within(row).getByRole('button', { name: /Actions pour/ }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })).toHaveAttribute('href', '/admin/expense/contract/1/change/')
  })
  it.each(['project', 'employee'] as const)('%s shows only visible note counts and opens the shared Notes Sheet without selecting the row', async (kind) => {
    const { fetchMock } = setup(kind, true, null, { visible_count: 2, can_add: true })
    const row = await screen.findByRole('row', { name: 'CDD Recherche' })
    const open = within(row).getByRole('button', { name: 'Ouvrir les notes du contrat · 2 notes' })
    expect(open).toHaveTextContent('2')
    await userEvent.setup().click(open)
    expect(row).toHaveAttribute('aria-selected', 'false')
    const sheet = await screen.findByRole('dialog', { name: 'Notes du contrat' })
    expect(within(sheet).getByRole('tab', { name: 'Suivi' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/api/v1/notes/contract/1/'))).toBe(true)
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Notes du contrat' })).not.toBeInTheDocument())
  })

  it('shows an icon without zero when Add is allowed, and no icon for a reader with no notes', async () => {
    const view = setup('project', true, null, { visible_count: 0, can_add: true })
    const row = await screen.findByRole('row', { name: 'CDD Recherche' })
    expect(within(row).getByRole('button', { name: 'Ouvrir les notes du contrat' })).toHaveTextContent('')
    expect(within(row).getByRole('button', { name: 'Ouvrir les notes du contrat' })).not.toHaveTextContent('0')
    view.unmount()
    vi.restoreAllMocks()
    setup('project', false, null, { visible_count: 0, can_add: false })
    expect(within(await screen.findByRole('row', { name: 'CDD Recherche' })).queryByRole('button', { name: 'Ouvrir les notes du contrat' })).not.toBeInTheDocument()
  })

  it('reuses GenericNotes create, edit and final save inside the Contract Sheet', async () => {
    const { fetchMock } = setup('project', true, null, { visible_count: 1, can_add: true })
    await userEvent.setup().click(within(await screen.findByRole('row', { name: 'CDD Recherche' })).getByRole('button', { name: 'Ouvrir les notes du contrat · 1 note' }))
    const sheet = await screen.findByRole('dialog', { name: 'Notes du contrat' })
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Ajouter une note' }))
    await userEvent.setup().type(screen.getByLabelText('Nom'), 'Réunion')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await within(sheet).findByRole('tab', { name: 'Réunion' })).toBeInTheDocument()
    await userEvent.setup().type(within(sheet).getByLabelText('Editor'), '<p>Dernière saisie</p>')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/notes/contract/1/10/') && init?.method === 'PATCH' && String(init.body).includes('Dernière saisie'))).toBe(true))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Notes du contrat' })).not.toBeInTheDocument())
    expect(within(screen.getByRole('row', { name: 'CDD Recherche' })).getByRole('button', { name: 'Ouvrir les notes du contrat · 2 notes' })).toBeInTheDocument()
  })

  it('keeps rename, visibility and confirmed deletion in the Contract Sheet', async () => {
    const { fetchMock } = setup('employee', true, null, { visible_count: 1, can_add: true })
    await userEvent.setup().click(within(await screen.findByRole('row', { name: 'CDD Recherche' })).getByRole('button', { name: 'Ouvrir les notes du contrat · 1 note' }))
    const sheet = await screen.findByRole('dialog', { name: 'Notes du contrat' })
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Actions sur la note' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Renommer' }))
    await userEvent.setup().clear(screen.getByLabelText('Nom'))
    await userEvent.setup().type(screen.getByLabelText('Nom'), 'Suivi modifié')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await within(sheet).findByRole('tab', { name: 'Suivi modifié' })).toBeInTheDocument()
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Actions sur la note' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Visibilité' }))
    await userEvent.setup().selectOptions(screen.getByRole('combobox', { name: 'Visibilité' }), 'creator')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await within(sheet).findByRole('tab', { name: /Suivi modifié/ })).toBeInTheDocument()
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Actions sur la note' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/notes/contract/1/9/') && init?.method === 'DELETE')).toBe(true))
  })

  it.each(['project', 'employee'] as const)('%s selects a row, renders common detail and Expenses outside a Sheet', async (kind) => {
    setup(kind)
    const row = await screen.findByRole('row', { name: 'CDD Recherche' })
    await userEvent.setup().click(row)
    expect(row).toHaveAttribute('aria-selected', 'true')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'Détail du contrat' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Jean Dupont' })).toHaveAttribute('href', '/employees/12')
    expect(screen.getByRole('link', { name: 'Atlas' })).toHaveAttribute('href', '/projects/3')
    expect(screen.getByRole('link', { name: 'Université de Lille' })).toHaveAttribute('href', '/infos/project/institution/40')
    expect(screen.getAllByText('Suivi RH').length).toBeGreaterThan(0)
    expect(await screen.findByRole('heading', { name: 'Dépenses liées' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter une dépense' })).toBeInTheDocument()
  })

  it('Project exposes participant/Fund options, creates and edits through the menu, and confirms deletion', async () => {
    const { fetchMock } = setup('project')
    await screen.findByRole('row', { name: 'CDD Recherche' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter un contrat' }))
    const create = screen.getByRole('dialog')
    expect(within(create).getByLabelText('Identité').querySelectorAll('option')).toHaveLength(2)
    await userEvent.setup().selectOptions(within(create).getByLabelText('Identité'), '12')
    await userEvent.setup().selectOptions(within(create).getByLabelText('Financement'), '20')
    await userEvent.setup().selectOptions(within(create).getByLabelText('Type de contrat'), '2')
    await userEvent.setup().click(within(create).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/projects/3/contracts/') && init?.method === 'POST')).toBe(true))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await userEvent.setup().click(screen.getAllByRole('button', { name: 'Actions pour CDD Recherche' })[0])
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    const edit = screen.getByRole('dialog')
    expect(within(edit).getByLabelText('Identité')).toBeDisabled()
    expect(within(edit).getByLabelText('Financement')).toBeDisabled()
    expect(within(edit).queryByRole('heading', { name: 'Dépenses liées' })).not.toBeInTheDocument()
    await userEvent.setup().click(within(edit).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/contracts/1/') && init?.method === 'PATCH')).toBe(true))
    expect(screen.queryByRole('alertdialog', { name: 'Mettre à jour la date de fin de l’employé ?' })).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getAllByRole('button', { name: 'Actions pour CDD Recherche' })[0])
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    await userEvent.setup().click(screen.getAllByText('Supprimer').at(-1)!)
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/contracts/1/') && init?.method === 'DELETE')).toBe(true))
  })

  it('adds an Expense through the selected Project Contract scope', async () => {
    const { fetchMock } = setup('project')
    await userEvent.setup().click(await screen.findByRole('row', { name: 'CDD Recherche' }))
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Ajouter une dépense' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Contrat')).toBeDisabled()
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '5')
    await userEvent.setup().type(within(sheet).getByLabelText('Montant'), '25')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/projects/3/contracts/1/expenses/') && init?.method === 'POST')).toBe(true))
  })

  it('Employee keeps its own capabilities and hides mutations for a reader', async () => {
    setup('employee', false)
    await screen.findByRole('row', { name: 'CDD Recherche' })
    expect(screen.queryByRole('button', { name: 'Ajouter un contrat' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour CDD Recherche' })).not.toBeInTheDocument()
  })

  it.each(['project', 'employee'] as const)('%s asks after saving and applies the Employee date only on confirmation', async (kind) => {
    const offer = { employee_id: 12, current_end_date: '2026-12-31', proposed_end_date: '2027-06-30', can_update: true }
    const { fetchMock } = setup(kind, true, offer)
    await screen.findByRole('row', { name: 'CDD Recherche' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour CDD Recherche' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    const prompt = await screen.findByRole('alertdialog', { name: 'Mettre à jour la date de fin de l’employé ?' })
    expect(prompt).toHaveTextContent('31 décembre 2026')
    expect(prompt).toHaveTextContent('30 juin 2027')
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/sync-employee-end-date/') && init?.method === 'POST')).toBe(false)
    await userEvent.setup().click(within(prompt).getByRole('button', { name: 'Mettre à jour' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/sync-employee-end-date/') && init?.method === 'POST')).toBe(true))
  }, 15000)

  it.each(['project', 'employee'] as const)('%s keeps the Employee date when the proposal is declined', async (kind) => {
    const offer = { employee_id: 12, current_end_date: '2028-12-31', proposed_end_date: '2027-06-30', can_update: true }
    const { fetchMock } = setup(kind, true, offer)
    await screen.findByRole('row', { name: 'CDD Recherche' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour CDD Recherche' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    const prompt = await screen.findByRole('alertdialog', { name: 'Mettre à jour la date de fin de l’employé ?' })
    await userEvent.setup().click(within(prompt).getByRole('button', { name: 'Conserver la date actuelle' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/sync-employee-end-date/') && init?.method === 'POST')).toBe(false)
  }, 15000)
})
