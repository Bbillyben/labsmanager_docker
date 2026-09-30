import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import type { Expense } from '../api/expenses'
import { ExpenseSection } from './ExpenseSection'

const costType = { id: 1, short_name: 'HR', name: 'Personnel' }
const item: Expense = { id: 9, expense_id: 'REF-9', desc: 'Salaire', date: '2026-03-01', type: costType, status: 'r', amount: '120.00', contract: { id: 4, name: 'Contrat A' }, budget: { id: 6, name: 'Budget A' }, capabilities: { can_change: true, can_delete: true } }

function setup({ mode = 'h', canAdd = true, canSync = true, rows = [item], count = rows.length }: { mode?: 's' | 'e' | 'h'; canAdd?: boolean; canSync?: boolean; rows?: Expense[]; count?: number } = {}) {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (url.includes('/expenses/options/')) return jsonResponse({ cost_types: [costType], hr_type_ids: [1], contracts: [{ id: 4, name: 'Contrat A' }], budgets: [{ id: 6, name: 'Budget A' }] })
    if (url.includes('/expenses/?') && method === 'GET') return jsonResponse({ count, previous: url.includes('page=2') ? 'previous' : null, next: count > 20 && !url.includes('page=2') ? 'next' : null, results: rows, capabilities: { expense_mode: mode, can_add: canAdd, can_sync_expenses: canSync } })
    if (url.endsWith('/sync/') && method === 'POST') return jsonResponse({ detail: 'ok' })
    if (url.endsWith('/expenses/') && method === 'POST') return jsonResponse(item, 201)
    if (url.endsWith('/expenses/9/') && method === 'PATCH') return jsonResponse(item)
    if (url.endsWith('/expenses/9/') && method === 'DELETE') return new Response(null, { status: 204 })
    throw new Error(`Unexpected ${method} ${url}`)
  })
  const onFinancialChange = vi.fn()
  render(<I18nProvider><ExpenseSection scope={{ fundId: 7 }} onFinancialChange={onFinancialChange} /></I18nProvider>)
  return { fetchMock, onFinancialChange }
}

afterEach(() => vi.restoreAllMocks())

describe('ExpenseSection shared Fund/Contract collection', () => {
  it('shows separate Contract and Budget and sends search, type and date filters to the backend', async () => {
    const { fetchMock } = setup()
    expect(await screen.findByText('REF-9')).toBeInTheDocument()
    expect(screen.getByText('Contrat A')).toBeInTheDocument()
    expect(screen.getByText('Budget A')).toBeInTheDocument()
    await userEvent.setup().type(screen.getByLabelText('Rechercher une référence ou une description'), 'REF-9')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('search=REF-9'))).toBe(true))
    await userEvent.setup().selectOptions(screen.getByLabelText('Type de coût'), '1')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('type=1'))).toBe(true))
    await userEvent.setup().type(screen.getByLabelText('Depuis le'), '2026-01-01')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('date_from=2026-01-01'))).toBe(true))
  })

  it('uses the canonical menu and confirms deletion and synchronization', async () => {
    const { fetchMock, onFinancialChange } = setup()
    await screen.findByText('REF-9')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour REF-9' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Annuler' }))
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/expenses/9/') && init?.method === 'DELETE')).toBe(false)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Synchroniser les dépenses' }))
    expect(screen.getByText(/montants saisis manuellement/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Synchroniser les dépenses' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/sync/') && init?.method === 'POST')).toBe(true))
    await waitFor(() => expect(onFinancialChange).toHaveBeenCalled())
  })

  it('keeps read-only actions hidden and requires a relation in Simple mode', async () => {
    const readonly = { ...item, capabilities: { can_change: false, can_delete: false } }
    setup({ mode: 's', canAdd: true, canSync: false, rows: [readonly] })
    await screen.findByText('REF-9')
    expect(screen.queryByRole('button', { name: 'Synchroniser les dépenses' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour REF-9' })).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter une dépense' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Contrat')).toBeInTheDocument()
    expect(within(sheet).getByLabelText('Budget')).toBeInTheDocument()
  })

  it('submits a negative amount with independent Contract and Budget links', async () => {
    const { fetchMock } = setup()
    await screen.findByText('REF-9')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter une dépense' }))
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().type(within(sheet).getByLabelText('Référence'), 'CREDIT')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Type de coût'), '1')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Contrat'), '4')
    await userEvent.setup().selectOptions(within(sheet).getByLabelText('Budget'), '6')
    await userEvent.setup().type(within(sheet).getByLabelText('Montant'), '-12.50')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/expenses/') && init?.method === 'POST')).toBe(true))
    const call = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/expenses/') && init?.method === 'POST')!
    expect(JSON.parse(String(call[1]?.body))).toMatchObject({ amount: '-12.5', contract_id: 4, budget_id: 6, status: 'r' })
  })

  it('uses backend pagination controls', async () => {
    const { fetchMock } = setup({ count: 25 })
    await screen.findByText('REF-9')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Suivant' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('page=2'))).toBe(true))
  })
})
