import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { ImportPage } from './ImportPage'

const structure = { expected: ['Expense Id', 'Amount'], recognized: ['Expense Id', 'Amount'], missing: [], extra: [], columns: 2, rows: 2 }
const columns = [
  { key: 'desc', label: 'Description' }, { key: 'amount', label: 'Montant' },
  { key: 'date', label: 'Date de dépense' },
]
const preview = { import_token: 'preview-token', summary: { new: 1, update: 0, unchanged: 0, error: 1 }, rows: [
  { row_number: 2, state: 'new', identity: 'EXP-1', summary: 'Expense', error_message: '', diff: [], values: { desc: 'Travel', amount: '10.00', date: '2026-03-01' } },
  { row_number: 3, state: 'error', identity: 'EXP-2', summary: '', error_message: 'Cost type not found', diff: [], values: { desc: 'Hotel', amount: '20.00', date: '2026-03-02' } },
], global_errors: [], can_commit: true, structure, sheet: 'Second' }

function setup(empty = false, generic = false, result: unknown = preview) {
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url === '/api/v1/imports/profiles/') return jsonResponse({ items: empty ? [] : [{ key: 'expense', label: 'Dépenses', description: 'Importer les dépenses', formats: ['csv', 'xlsx'], template_formats: ['csv', 'xlsx'], preview_columns: generic ? [] : columns }] })
    if (url === '/api/v1/imports/expense/upload/') return jsonResponse({ import_token: 'upload-token', filename: 'expenses.xlsx', size: 200, format: 'xlsx', sheets: ['First', 'Second'], structure, sheet_structures: { First: structure, Second: { ...structure, rows: 2 } } })
    if (url === '/api/v1/imports/expense/preview/') return jsonResponse(result)
    if (url === '/api/v1/imports/expense/commit/') return jsonResponse(result)
    throw new Error(url)
  })
  render(<I18nProvider><ImportPage /></I18nProvider>)
  return fetch
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

describe('Import Hub', () => {
  it('uses backend profiles and has a safe empty state', async () => {
    setup(true)
    expect(await screen.findByText('Aucun profil d’import autorisé.')).toBeInTheDocument()
  })

  it('uploads, selects a sheet, previews, filters, commits and shows the final result', async () => {
    const fetch = setup()
    const user = userEvent.setup()
    await user.selectOptions(await screen.findByLabelText('Type d’import'), 'expense')
    await user.upload(screen.getByLabelText('Choisir un fichier'), new File(['content'], 'expenses.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
    await user.selectOptions(await screen.findByLabelText('Feuille à importer'), 'Second')
    await user.click(screen.getByRole('button', { name: 'Vérifier l’import' }))
    await screen.findByText('Cost type not found')
    const table = screen.getByRole('table')
    expect(within(table).getAllByRole('columnheader').map((header) => header.textContent)).toEqual([
      'État', 'Ligne', 'Identifiant', 'Description', 'Montant', 'Date de dépense', 'Détail',
    ])
    expect(within(table).getByText('Travel')).toBeInTheDocument()
    expect(within(table).getByText('2026-03-01')).toBeInTheDocument()
    expect(within(table).getByText('Hotel')).toBeInTheDocument()
    expect(table.parentElement).toHaveClass('overflow-x-auto')
    await user.click(screen.getByRole('button', { name: 'Erreurs (1)' }))
    expect(screen.queryByText('EXP-1')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Confirmer l’import' }))
    expect(await screen.findByText('Import terminé')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('Travel')).toBeInTheDocument()
    await waitFor(() => expect(fetch.mock.calls.some(([input, init]) => String(input).endsWith('/preview/') && String(init?.body).includes('Second'))).toBe(true))
  })

  it('keeps the generic table when a profile has no preview columns', async () => {
    setup(false, true)
    const user = userEvent.setup()
    await user.selectOptions(await screen.findByLabelText('Type d’import'), 'expense')
    await user.upload(screen.getByLabelText('Choisir un fichier'), new File(['content'], 'expenses.xlsx'))
    await user.click(await screen.findByRole('button', { name: 'Vérifier l’import' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.getAllByRole('columnheader').map((header) => header.textContent)).toEqual([
      'État', 'Ligne', 'Identifiant', 'Détail',
    ])
  })

  it('shows business columns alongside the update diff', async () => {
    setup(false, false, { ...preview, summary: { new: 0, update: 1, unchanged: 0, error: 0 }, rows: [{
      row_number: 2, state: 'update', identity: 'EXP-1', summary: 'Expense', error_message: '',
      diff: [{ field: 'Amount', old: '5', new: '10' }], values: { desc: 'Travel', amount: '10', date: '2026-03-01' },
    }] })
    const user = userEvent.setup()
    await user.selectOptions(await screen.findByLabelText('Type d’import'), 'expense')
    await user.upload(screen.getByLabelText('Choisir un fichier'), new File(['content'], 'expenses.xlsx'))
    await user.click(await screen.findByRole('button', { name: 'Vérifier l’import' }))
    expect(await screen.findByText('Travel')).toBeInTheDocument()
    expect(screen.getByText(/Amount:/)).toBeInTheDocument()
  })

  it('invalidates a preview when the file or Excel sheet changes', async () => {
    setup()
    const user = userEvent.setup()
    await user.selectOptions(await screen.findByLabelText('Type d’import'), 'expense')
    const input = screen.getByLabelText('Choisir un fichier')
    await user.upload(input, new File(['first'], 'expenses.xlsx'))
    await user.click(await screen.findByRole('button', { name: 'Vérifier l’import' }))
    await screen.findByRole('button', { name: 'Confirmer l’import' })
    await user.selectOptions(screen.getByLabelText('Feuille à importer'), 'Second')
    expect(screen.queryByRole('button', { name: 'Confirmer l’import' })).not.toBeInTheDocument()
    await user.upload(input, new File(['second'], 'replacement.xlsx'))
    expect(screen.queryByRole('button', { name: 'Confirmer l’import' })).not.toBeInTheDocument()
  })
})
