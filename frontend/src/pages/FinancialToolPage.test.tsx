import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { FinancialToolPage } from './FinancialToolPage'
import type { FinancialKind } from '../config/financialFilters'

const relation = (id: number, name: string) => ({ id, name, can_view: true })
const fund = { project: relation(3, 'Atlas'), funder: relation(4, 'ANR'), institution: relation(5, 'Université'), ref: 'REF-1', start_date: '2026-01-01', end_date: '2026-12-31', is_active: true }
const type = { id: 2, name: 'Personnel', short_name: 'RH' }
const rows = {
  'fund-items': { id: 10, admin_url: '/admin/fund/fund_item/10/change/', fund, type, entry_date: '2026-01-01', value_date: '2026-01-01', amount: '100.00', expense: '-20.00', available: '80.00', contract_count: 1 },
  budgets: { id: 11, admin_url: null, fund, cost_type: type, desc: 'Budget RH', emp_type: null, employee: null, contract_types: [], quotity: '0.500', amount: '100.00', expense: '20.00', available: '80.00', consumption_ratio: '0.2', capabilities: { can_add: true, can_change: true, can_delete: true } },
  expenses: { id: 12, admin_url: null, fund, expense_id: 'EXP-1', desc: 'Salaire', date: '2026-03-01', type, amount: '-20.00', status: 'r' },
} as const
const options = { cost_types: [type], contract_types: [], employee_types: [], statuses: [{ value: 'r', label: 'Réalisée' }] }

function setup(kind: FinancialKind, path = `/tools/${kind}`, empty = false, missingContractTypes = false) {
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url === '/api/v1/financial/filter-options/') return jsonResponse(options)
    if (url === '/api/v1/fund-items/10/contracts/') return jsonResponse([{ id: 20, employee: 'Jean Dupont', type: 'CDD', status: 'effe', start_date: '2026-01-01', end_date: '2026-12-31', quotity: '1.000', is_active: true }])
    if (url.startsWith(`/api/v1/${kind}/?`)) {
      const row = { ...rows[kind] } as Record<string, unknown>
      if (missingContractTypes) delete row.contract_types
      return jsonResponse({ count: empty ? 0 : 1, next: empty ? null : '/next/', previous: null, results: empty ? [] : [row] })
    }
    if (url.startsWith(`/api/v1/${kind}/export/`)) return new Response('csv', { status: 200, headers: { 'Content-Type': 'text/csv' } })
    throw new Error(url)
  })
  render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes><Route path={`/tools/${kind}`} element={<FinancialToolPage kind={kind} />} /><Route path="/projects/:id" element={<p>Project detail</p>} /></Routes></MemoryRouter></I18nProvider>)
  return fetch
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

describe('Financial tools', () => {
  it.each(['fund-items', 'budgets', 'expenses'] as const)('%s is read-only, linked, filtered, sorted and paginated', async (kind) => {
    const fetch = setup(kind)
    const user = userEvent.setup()
    const row = await screen.findByRole('row', { name: 'Ouvrir le détail' })
    expect(within(row).getByRole('link', { name: 'Atlas' })).toHaveAttribute('href', '/projects/3')
    expect(screen.queryByRole('button', { name: /Ajouter (un budget|une dépense|un fonds)|Modifier|Supprimer/ })).not.toBeInTheDocument()
    await user.click(row)
    expect(await screen.findByRole('dialog', { name: 'Détail' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await user.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await user.click(within(screen.getByRole('dialog', { name: 'Ajouter un filtre' })).getByRole('button', { name: 'Type de coût' }))
    await user.selectOptions(screen.getByLabelText('Type de coût'), '2')
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('type=2'))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Suivant' }))
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('offset=25'))).toBe(true))
  })

  it('shows only RH contract counts and opens the visible Contract sheet', async () => {
    const fetch = setup('fund-items')
    const user = userEvent.setup()
    const row = await screen.findByRole('row', { name: 'Ouvrir le détail' })
    await user.click(within(row).getByRole('button', { name: 'Voir les contrats (1)' }))
    const sheet = await screen.findByRole('dialog', { name: 'Contrats' })
    expect(within(sheet).getByText('Jean Dupont')).toBeInTheDocument()
    expect(fetch.mock.calls.some(([input]) => String(input) === '/api/v1/fund-items/10/contracts/')).toBe(true)
    expect(within(sheet).queryByRole('button', { name: /Modifier|Supprimer|Ajouter/ })).not.toBeInTheDocument()
  })

  it('keeps an empty tool accessible', async () => {
    setup('budgets', '/tools/budgets', true)
    expect(await screen.findByText('Aucun résultat.')).toBeInTheDocument()
  })

  it('keeps the Budget list and detail usable when an older response omits contract_types', async () => {
    setup('budgets', '/tools/budgets', false, true)
    const row = await screen.findByRole('row', { name: 'Ouvrir le détail' })
    expect(within(row).getByText('Budget RH')).toBeInTheDocument()
    await userEvent.setup().click(row)
    expect(await screen.findByRole('dialog', { name: 'Détail' })).toBeInTheDocument()
  })
})
