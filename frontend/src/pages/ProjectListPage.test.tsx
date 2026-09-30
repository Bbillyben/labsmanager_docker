import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ProjectItem, ProjectListResponse } from '../api/projects'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { AppRouter } from '../router/AppRouter'
import { authenticatedUser, jsonResponse } from '../test/fixtures'

const alpha: ProjectItem = { id: 3, name: 'Alpha', start_date: '2026-01-01', end_date: null, status: true, institutions: ['Inserm', 'Université de Lille', 'CHU'], participants: ['François Pattou', 'Benjamin Legendre', 'Ada Byron'], funds: ['INSERM · ABC', 'ANR · XYZ', 'CHU · 42'], capabilities: { can_add: true, can_change: true, can_delete: true } }
const beta: ProjectItem = { ...alpha, id: 4, name: 'Beta', status: false, institutions: [], participants: [], funds: [], capabilities: { can_add: true, can_change: false, can_delete: false } }
const collection = (items: ProjectItem[]): ProjectListResponse => ({ count: items.length, next: null, previous: null, results: items })

function mockApi(paginated = false) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
    if (url.startsWith('/api/v1/projects/export/')) return new Response('file', { headers: { 'Content-Disposition': 'attachment; filename="Project_20260930-1200.xlsx"' } })
    if (url.startsWith('/api/v1/employees/?')) return jsonResponse({ count: 1, next: null, previous: null, results: [{ id: 7, first_name: 'Marie', last_name: 'Curie', is_active: true, entry_date: null, exit_date: null, current_statuses: [], superiors: [] }] })
    if (url === '/api/v1/employees/7/') return jsonResponse({ id: 7, first_name: 'Marie', last_name: 'Curie' })
    if (url.endsWith('/projects/capabilities/')) return jsonResponse({ can_add: true, can_change: false, can_delete: false })
    if (url.endsWith('/projects/filter-options/')) return jsonResponse({ funders: [], institutions: [], teams: [] })
    if (/\/projects\/\d+\/$/.test(url) && init?.method === 'GET') {
      const id = Number(url.split('/').at(-2))
      const project = id === 9 ? { ...alpha, id, name: 'Created' } : alpha
      const collection = { capabilities: { can_add: false, can_change: false, can_delete: false }, items: [] }
      return jsonResponse({ id: project.id, name: project.name, start_date: project.start_date, end_date: project.end_date, status: project.status, capabilities: project.capabilities, generic_info: collection, institutions: collection, participants: collection })
    }
    if (init?.method === 'POST') return jsonResponse({ id: 9, name: 'Created', start_date: null, end_date: null, status: true }, 201)
    if (init?.method === 'PATCH') return jsonResponse({ id: 3, name: 'Alpha', start_date: null, end_date: null, status: false })
    if (init?.method === 'DELETE') return new Response(null, { status: 204 })
    const params = new URL(url, 'http://localhost').searchParams
    const items = params.get('status') === 'true' ? [alpha] : params.get('status') === 'false' ? [beta] : [alpha, beta]
    return jsonResponse(paginated ? { ...collection(items), count: 30, next: params.has('offset') ? null : '/api/v1/projects/?offset=25', previous: params.has('offset') ? '/api/v1/projects/' : null } : collection(items))
  })
}
function mount(language = 'fr-FR', path = '/app/projects/') {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: [language] })
  window.history.replaceState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}

describe('React Project List', () => {
  it('exports all filtered projects as XLSX by default without changing the list URL', async () => {
    const fetchMock = mockApi()
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:project-export') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    mount('fr-FR', '/app/projects/?status=true&project_name=Alpha&ordering=-name&limit=10&offset=20')
    await screen.findByRole('link', { name: 'Alpha' }, { timeout: 8000 })
    const before = window.location.search
    await userEvent.click(screen.getByRole('button', { name: 'Exporter' }))
    expect(screen.getByRole('combobox', { name: 'Format' })).toHaveValue('xlsx')
    await userEvent.click(screen.getByRole('button', { name: 'Télécharger' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/projects/export/'))).toBe(true))
    const exportUrl = String(fetchMock.mock.calls.find(([url]) => String(url).startsWith('/api/v1/projects/export/'))?.[0])
    const params = new URL(exportUrl, 'http://localhost').searchParams
    expect(params.get('status')).toBe('true')
    expect(params.get('project_name')).toBe('Alpha')
    expect(params.get('ordering')).toBe('-name')
    expect(params.get('format')).toBe('xlsx')
    expect(params.has('limit')).toBe(false)
    expect(params.has('offset')).toBe(false)
    expect(window.location.search).toBe(before)
    expect(click).toHaveBeenCalled()
    click.mockRestore()
  })

  it('translates list controls and accessible text in English while preserving project data', async () => {
    mockApi()
    mount('en-US')
    expect(await screen.findByRole('link', { name: 'Alpha' }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Project table, horizontal scrolling' })).toBeInTheDocument()
    expect(screen.getByLabelText('Activity')).toHaveValue('true')
    expect(screen.getByText('Active', { selector: 'span[data-slot=badge]' })).toBeInTheDocument()
    expect(screen.getByText('Inserm, Université de Lille +1')).toBeInTheDocument()
  })

  afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

  it('shows the default active filter, compact relations, status and a name-only route', async () => {
    const fetchMock = mockApi()
    mount()
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Alpha' })).toBeInTheDocument(), { timeout: 5000 })
    const name = screen.getByRole('link', { name: 'Alpha' })
    expect(screen.getByLabelText('Activité')).toHaveValue('true')
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('status=true'))).toBe(true)
    expect(screen.getByText('Inserm, Université de Lille +1')).toHaveAttribute('title', 'Inserm, Université de Lille, CHU')
    expect(screen.getByText('François Pattou, Benjamin Legendre +1')).toBeInTheDocument()
    expect(screen.getByText('INSERM · ABC, ANR · XYZ +1')).toBeInTheDocument()
    expect(screen.getByText('Actif')).toBeInTheDocument()
    const row = name.closest('tr')!
    await userEvent.setup().click(row.querySelector('td')!)
    expect(window.location.pathname).toBe('/app/projects/')
    expect(row).toHaveAttribute('data-selected', 'true')
    await userEvent.setup().click(name)
    expect(window.location.pathname).toBe('/app/projects/3')
    expect(await screen.findByRole('heading', { name: 'Informations du projet' })).toBeInTheDocument()
  })

  it('removes Active, displays inactive projects and keeps name ordering', async () => {
    const fetchMock = mockApi()
    mount()
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Alpha' }), JSON.stringify(fetchMock.mock.calls.map(([url]) => String(url)))).toBeInTheDocument())
    await userEvent.setup().click(screen.getByRole('button', { name: 'Supprimer le filtre activité' }))
    expect(await screen.findByRole('link', { name: 'Beta' })).toBeInTheDocument()
    expect(screen.getByText('Inactif')).toBeInTheDocument()
    expect(new URLSearchParams(window.location.search).has('status')).toBe(false)
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/projects/?') && !String(url).includes('status='))).toBe(true)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Beta' }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir la fiche' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Supprimer' })).not.toBeInTheDocument()
  })

  it('sends search, filters, ordering and pagination to v1', async () => {
    const fetchMock = mockApi(true)
    mount()
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Alpha' })).toBeInTheDocument(), { timeout: 5000 })
    await userEvent.setup().type(screen.getByRole('searchbox'), 'Alpha{Enter}')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('search=Alpha'))).toBe(true))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Trier par projet, ordre décroissant' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('ordering=-name'))).toBe(true))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.setup().click(screen.getByRole('button', { name: /Référence de fonds/ }))
    await userEvent.setup().type(screen.getByLabelText('Référence de fonds'), 'ABC')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('fundref=ABC'))).toBe(true))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Suivant' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('offset=25'))).toBe(true))
  })

  it('keeps the existing filters, stale criterion, sort and page through a Project detail round trip', async () => {
    const fetchMock = mockApi(true)
    mount('fr-FR', '/app/projects/?status=true&stale=true&project_name=Alpha&ordering=-name&offset=25')
    const name = await screen.findByRole('link', { name: 'Alpha' }, { timeout: 8000 })
    expect(screen.getByLabelText('En retard')).toHaveValue('true')
    expect(screen.getByLabelText('Nom du projet')).toHaveValue('Alpha')
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('stale=true') && String(url).includes('ordering=-name') && String(url).includes('offset=25'))).toBe(true)
    await userEvent.click(name)
    const back = await screen.findByRole('link', { name: 'Retour aux projets' })
    await userEvent.click(back)
    expect(window.location.search).toContain('stale=true')
    expect(window.location.search).toContain('ordering=-name')
    expect(window.location.search).toContain('offset=25')
    expect(await screen.findByRole('link', { name: 'Alpha' })).toBeInTheDocument()
  })

  it('selects a participant with the shared Employee search and filters by ID', async () => {
    const fetchMock = mockApi()
    mount()
    await screen.findByRole('link', { name: 'Alpha' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.setup().click(screen.getByRole('button', { name: /Participant/ }))
    const search = screen.getByRole('combobox', { name: 'Participant' })
    await userEvent.setup().type(search, 'Marie')
    await screen.findByRole('option', { name: 'Marie Curie' })
    await userEvent.setup().keyboard('{ArrowDown}{Enter}')
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('participant')).toBe('7'))
    expect(new URLSearchParams(window.location.search).has('participant_name')).toBe(false)
    expect(fetchMock.mock.calls.some(([url]) => String(url) === '/api/v1/employees/?search=Marie&limit=10')).toBe(true)
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/projects/?') && String(url).includes('participant=7'))).toBe(true)
    expect(await screen.findByDisplayValue('Marie Curie')).toBeInTheDocument()
  })

  it('creates in a Sheet and navigates using the POST response', async () => {
    const fetchMock = mockApi()
    mount()
    await screen.findByRole('link', { name: 'Alpha' })
    const add = screen.getByRole('button', { name: 'Ajouter un projet' })
    expect(add.querySelector('svg.lucide-plus')).toHaveAttribute('aria-hidden', 'true')
    await userEvent.setup().click(add)
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().type(within(sheet).getByLabelText('Nom du projet'), 'Created')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(window.location.pathname).toBe('/app/projects/9'))
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/projects/9/'))).toBe(true))
  })

  it('gates row mutations by capabilities and confirms deletion', async () => {
    const fetchMock = mockApi()
    mount()
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Alpha' }), JSON.stringify(fetchMock.mock.calls.map(([url]) => String(url)))).toBeInTheDocument())
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Alpha' }))
    expect(await screen.findByRole('menuitem', { name: 'Modifier' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('menuitem', { name: 'Modifier' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Nom du projet')).toBeDisabled()
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Annuler' }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Alpha' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(screen.getByText(/Supprimer « Alpha »/)).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Supprimer', hidden: true }))
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(1))
  })
})
