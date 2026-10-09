import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { EmployeeDetail, EmployeeStatusHistoryItem } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeDetailContext } from './employeeDetailContext'
import { EmployeeOverview } from './EmployeeOverview'

const employee: EmployeeDetail = {
  id: 12, first_name: 'Jean', last_name: 'Dupont', birth_date: null, email: null,
  entry_date: '2020-01-01', exit_date: null, is_active: true, current_statuses: [], superiors: [],
  contract_quotity: null, project_quotity: null, contribution_quotity: null, active_milestones_count: 0,
  capabilities: { can_change: true, can_export_word: false, can_export_pdf: false },
}
const current: EmployeeStatusHistoryItem = { id: 7, type: { id: 4, code: 'ENG', name: 'Engineer' }, start_date: '2020-01-01', end_date: null, contractuality: { code: 'c', label: 'Contractuel' }, is_active: true }
const old: EmployeeStatusHistoryItem = { ...current, id: 8, end_date: '2021-01-01', is_active: false }

function setup(allowed = true, patchError = false) {
  let items = [current, old]
  let reads = 0
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (url.endsWith('/statuses/options/')) return jsonResponse({ capabilities: { can_add: allowed, can_change: allowed, can_delete: allowed }, types: [{ id: 4, name: 'Engineer', shortname: 'ENG' }], contractuality: [{ code: 'c', label: 'Contractuel' }, { code: 's', label: 'Statutaire' }] })
    if (url.endsWith('/statuses/') && method === 'GET') { reads += 1; return jsonResponse(items) }
    if (url.endsWith('/statuses/') && method === 'POST') {
      items = [...items, { ...current, id: 9 }]
      return jsonResponse(items.at(-1), 201)
    }
    if (url.endsWith('/statuses/7/') && method === 'PATCH') {
      if (patchError) return jsonResponse({ end_date: ['end_before_start'] }, 400)
      items = items.map((item) => item.id === 7 ? { ...item, end_date: '2022-01-01', is_active: false } : item)
      return jsonResponse(items[0])
    }
    if (url.endsWith('/statuses/7/') && method === 'DELETE') {
      items = items.filter((item) => item.id !== 7)
      return new Response(null, { status: 204 })
    }
    if (url.endsWith('/hierarchy/')) return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, superiors: [], subordinates: [] })
    if (url.endsWith('/generic-info/')) return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, items: [] })
    throw new Error(`Unexpected URL ${url}`)
  })
  render(<I18nProvider><MemoryRouter><EmployeeDetailContext.Provider value={{ employee, employeeId: '12' }}><EmployeeOverview /></EmployeeDetailContext.Provider></MemoryRouter></I18nProvider>)
  return { fetchMock, reads: () => reads }
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

it('keeps current and previous rendering read-only when backend denies mutations', async () => {
  setup(false)
  expect(await screen.findByText('Engineer')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Ajouter un statut' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Actions pour Engineer' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: '↳ 1 précédent' })).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '↳ 1 précédent' }))
  expect(screen.getAllByText('Engineer')).toHaveLength(2)
  expect(screen.queryByRole('button', { name: 'Actions pour Engineer' })).not.toBeInTheDocument()
})

it('creates a status in the Sheet and refreshes only the statuses', async () => {
  const { fetchMock, reads } = setup()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Ajouter un statut' }))
  const sheet = await screen.findByRole('dialog')
  expect(within(sheet).getByRole('heading', { name: 'Ajouter un statut' })).toBeInTheDocument()
  await user.selectOptions(within(sheet).getByLabelText('Type de statut'), '4')
  await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
  await waitFor(() => expect(reads()).toBeGreaterThan(1))
  expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/statuses/') && init?.method === 'POST')).toBe(true)
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/hierarchy/'))).toHaveLength(1)
})

it('keeps previous collapsed, exposes its menu after expansion and moves edited current status into history', async () => {
  const { reads } = setup()
  const user = userEvent.setup()
  expect(await screen.findByRole('button', { name: 'Actions pour Engineer' })).toBeInTheDocument()
  expect(screen.getAllByText('Engineer')).toHaveLength(1)
  expect(screen.getByRole('button', { name: '↳ 1 précédent' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '↳ 1 précédent' }))
  expect(screen.getAllByRole('button', { name: 'Actions pour Engineer' })).toHaveLength(2)
  await user.click(screen.getAllByRole('button', { name: 'Actions pour Engineer' })[0])
  await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
  const sheet = await screen.findByRole('dialog')
  expect(within(sheet).getByRole('heading', { name: 'Modifier le statut' })).toBeInTheDocument()
  expect(within(sheet).getByLabelText('Type de statut')).toBeDisabled()
  expect(within(sheet).getByDisplayValue('2020-01-01')).toBeInTheDocument()
  await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
  await waitFor(() => expect(reads()).toBeGreaterThan(1))
  expect(within(screen.getByRole('region', { name: 'Statuts' })).getByText('Aucun actuellement')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: '↟ Réduire' })).toBeInTheDocument()
})

it('keeps the Sheet open on validation error and confirms deletion before mutation', async () => {
  const { fetchMock, reads } = setup(true, true)
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Actions pour Engineer' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
  const sheet = await screen.findByRole('dialog')
  await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
  expect(await within(sheet).findByText('La date de fin doit suivre la date de début.')).toBeInTheDocument()
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  await user.click(within(sheet).getByRole('button', { name: 'Annuler' }))
  await user.click(screen.getByRole('button', { name: 'Actions pour Engineer' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
  expect(screen.getByText(/Supprimer le statut Engineer/)).toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/statuses/7/') && init?.method === 'DELETE')).toBe(false)
  await user.click(screen.getByRole('button', { name: 'Supprimer' }))
  await waitFor(() => expect(reads()).toBeGreaterThan(1))
})
