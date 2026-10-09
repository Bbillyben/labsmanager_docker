import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { EmployeeDetail, EmployeeHierarchy } from '../api/employees'
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
const relation = { id: 7, employee: { id: 3, first_name: 'Marie', last_name: 'Martin' }, start_date: '2021-01-01', end_date: null, is_active: true }

function setup(canChange = true, saveError = false) {
  let hierarchy: EmployeeHierarchy = {
    capabilities: { can_add: canChange, can_change: canChange, can_delete: canChange },
    superiors: [relation], subordinates: [],
  }
  let reads = 0
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    const method = init?.method ?? 'GET'
    if (url.endsWith('/statuses/options/')) return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, types: [], contractuality: [] })
    if (url.endsWith('/statuses/')) return jsonResponse([])
    if (url.endsWith('/generic-info/')) return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, items: [] })
    if (url.includes('/hierarchy/candidates/')) return jsonResponse({ results: [{ id: 4, name: 'Bea Beta' }], has_more: false })
    if (url.endsWith('/hierarchy/') && method === 'GET') { reads += 1; return jsonResponse(hierarchy) }
    if (url.endsWith('/hierarchy/') && method === 'POST') {
      const body = JSON.parse(String(init?.body))
      const created = { id: 8, employee: { id: 4, first_name: 'Bea', last_name: 'Beta' }, start_date: body.start_date, end_date: body.end_date, is_active: true }
      hierarchy = { ...hierarchy, [body.direction === 'superior' ? 'superiors' : 'subordinates']: [...hierarchy[body.direction === 'superior' ? 'superiors' : 'subordinates'], created] }
      return jsonResponse({ id: 8 }, 201)
    }
    if (url.endsWith('/hierarchy/7/') && method === 'PATCH') return saveError ? jsonResponse({ end_date: ['end_before_start'] }, 400) : jsonResponse({ id: 7 })
    if (url.endsWith('/hierarchy/7/') && method === 'DELETE') {
      hierarchy = { ...hierarchy, superiors: [] }
      return new Response(null, { status: 204 })
    }
    throw new Error(`Unexpected URL ${url}`)
  })
  render(<I18nProvider><MemoryRouter><EmployeeDetailContext.Provider value={{ employee: { ...employee, capabilities: { ...employee.capabilities!, can_change: canChange } }, employeeId: '12' }}><EmployeeOverview /></EmployeeDetailContext.Provider></MemoryRouter></I18nProvider>)
  return { fetchMock, reads: () => reads }
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

it('keeps hierarchy strictly read-only without the backend capability', async () => {
  setup(false)
  expect(await screen.findByRole('link', { name: 'Marie Martin' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Ajouter un supérieur' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Ajouter un subordonné' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Actions pour Marie Martin' })).not.toBeInTheDocument()
})

it('opens both lateral create flows, searches eligible Employees and refreshes after adding', async () => {
  const { fetchMock, reads } = setup()
  const user = userEvent.setup()
  await screen.findByRole('link', { name: 'Marie Martin' })
  await user.click(screen.getByRole('button', { name: 'Ajouter un supérieur' }))
  let sheet = await screen.findByRole('dialog')
  expect(within(sheet).getByRole('heading', { name: 'Ajouter un supérieur' })).toBeInTheDocument()
  await user.type(within(sheet).getByRole('combobox', { name: 'Sélectionner un employé' }), 'Bea')
  expect(await screen.findByRole('option', { name: 'Bea Beta' })).toBeInTheDocument()
  expect(screen.queryByRole('option', { name: 'Jean Dupont' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('option', { name: 'Bea Beta' }))
  await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
  await waitFor(() => expect(reads()).toBeGreaterThan(1))
  expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/hierarchy/') && init?.method === 'POST')).toBe(true)
  await user.click(screen.getByRole('button', { name: 'Ajouter un subordonné' }))
  sheet = await screen.findByRole('dialog')
  expect(within(sheet).getByRole('heading', { name: 'Ajouter un subordonné' })).toBeInTheDocument()
})

it('edits dates in the Sheet, preserves errors and confirms deletion before refresh', async () => {
  const { fetchMock, reads } = setup(true, true)
  const user = userEvent.setup()
  await screen.findByRole('link', { name: 'Marie Martin' })
  await user.click(screen.getByRole('button', { name: 'Actions pour Marie Martin' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
  const sheet = await screen.findByRole('dialog')
  expect(within(sheet).getByRole('heading', { name: 'Modifier le supérieur' })).toBeInTheDocument()
  expect(within(sheet).getByDisplayValue('2021-01-01')).toBeInTheDocument()
  await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
  expect(await within(sheet).findByText('La date de fin doit suivre la date de début.')).toBeInTheDocument()
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  await user.click(within(sheet).getByRole('button', { name: 'Annuler' }))
  await user.click(screen.getByRole('button', { name: 'Actions pour Marie Martin' }))
  await user.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
  expect(screen.getByText(/Cette action retire également cette relation de l’historique/)).toBeInTheDocument()
  expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/hierarchy/7/') && init?.method === 'DELETE')).toBe(false)
  await user.click(screen.getByRole('button', { name: 'Supprimer' }))
  await waitFor(() => expect(reads()).toBeGreaterThan(1))
  expect(screen.queryByRole('link', { name: 'Marie Martin' })).not.toBeInTheDocument()
})
