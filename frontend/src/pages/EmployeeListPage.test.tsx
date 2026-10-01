import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { AppRouter } from '../router/AppRouter'
import { authenticatedUser, jsonResponse, userWithoutNavigationCapabilities } from '../test/fixtures'
import type { EmployeeListItem, EmployeeListResponse } from '../api/employees'

const alice: EmployeeListItem = { id: 1, first_name: 'Alice', last_name: 'Martin', entry_date: '2020-01-02', exit_date: null, is_active: true, current_statuses: [{ id: 3, code: 'RES', name: 'Chercheuse' }, { id: 4, code: 'ENG', name: 'Ingénieure' }], superiors: [{ id: 9, first_name: 'Marie', last_name: 'Curie' }] }
const bob: EmployeeListItem = { ...alice, id: 2, first_name: 'Bob', last_name: 'Durand', is_active: false, current_statuses: [], superiors: [] }
const collection = (results = [alice, bob], extra: Partial<EmployeeListResponse> = {}): EmployeeListResponse => ({ count: results.length, next: null, previous: null, results, ...extra })

function mockApi(response: (url: string, init?: RequestInit) => Promise<Response> = async () => jsonResponse(collection()), user = authenticatedUser) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => String(input) === '/api/v1/me/' ? Promise.resolve(jsonResponse(user)) : String(input) === '/api/v1/employees/filter-options/' ? Promise.resolve(jsonResponse({ statuses: [{ id: 3, name: 'Chercheuse' }], teams: [{ id: 6, name: 'Recherche' }] })) : response(String(input), init))
}
function renderAt(path = '/app/employees/', language = 'fr-FR') {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: [language] })
  window.history.replaceState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}
async function loaded() { return screen.findByRole('link', { name: 'Alice Martin' }) }
function row(name: string) { return screen.getByRole('link', { name }).closest('tr')! }
async function filterActivity(value: string) {
  if (!screen.queryByLabelText('Activité')) {
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.click(screen.getByRole('button', { name: /Activité/ }))
  }
  await userEvent.selectOptions(screen.getByLabelText('Activité'), value)
}
function query() { return new URLSearchParams(window.location.search) }

describe('Employee R1', () => {
  it('adds the backend-provided Admin link to the Employee row menu', async () => {
    mockApi(async () => jsonResponse(collection([{ ...alice, admin_url: '/admin/staff/employee/1/change/' }])))
    renderAt()
    await screen.findByRole('link', { name: 'Alice Martin' }, { timeout: 8000 })
    await userEvent.click(within(row('Alice Martin')).getByRole('button', { name: 'Actions pour Alice Martin' }))
    const link = await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })
    expect(link).toHaveAttribute('href', '/admin/staff/employee/1/change/')
    expect(link).toHaveAttribute('target', '_blank')
  })
  it('exports the full filtered list with the chosen format without changing its URL', async () => {
    const fetchMock = mockApi(async (url) => url.startsWith('/api/v1/employees/export/')
      ? new Response('file', { headers: { 'Content-Disposition': 'attachment; filename="Employee_20260930-1200.csv"' } })
      : jsonResponse(collection([alice])))
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:employee-export') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    renderAt('/app/employees/?is_active=true&status=3&ordering=-entry_date&limit=10&offset=20')
    await screen.findByRole('link', { name: 'Alice Martin' }, { timeout: 8000 })
    const before = window.location.search
    await userEvent.click(screen.getByRole('button', { name: 'Exporter' }))
    expect(screen.getByRole('combobox', { name: 'Format' })).toHaveValue('xlsx')
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Exporter' }))
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Format' }), 'csv')
    await userEvent.click(screen.getByRole('button', { name: 'Télécharger' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/employees/export/'))).toBe(true))
    const exportUrl = String(fetchMock.mock.calls.find(([url]) => String(url).startsWith('/api/v1/employees/export/'))?.[0])
    const params = new URL(exportUrl, 'http://localhost').searchParams
    expect(params.get('is_active')).toBe('true')
    expect(params.get('status')).toBe('3')
    expect(params.get('ordering')).toBe('-entry_date')
    expect(params.get('format')).toBe('csv')
    expect(params.has('limit')).toBe(false)
    expect(params.has('offset')).toBe(false)
    expect(params.has('filters_initialized')).toBe(false)
    expect(window.location.search).toBe(before)
    expect(click).toHaveBeenCalled()
    click.mockRestore()
  })

  it('translates list controls and status in English while retaining Employee data', async () => {
    mockApi(async () => jsonResponse(collection([alice])))
    renderAt('/app/employees/', 'en-US')
    expect(await screen.findByRole('link', { name: 'Alice Martin' }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByLabelText('Activity')).toHaveValue('true')
    expect(screen.getByText('Active', { selector: 'span[data-slot=badge]' })).toBeInTheDocument()
    expect(screen.getByText('Chercheuse')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('shows Active=true as a removable first-load filter', async () => {
    const fetchMock = mockApi(async (url) => jsonResponse(collection(url.includes('is_active=true') ? [alice] : [alice, bob])))
    renderAt()
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Alice Martin' })).toBeInTheDocument(), { timeout: 5000 })
    expect(screen.getByLabelText('Activité')).toHaveValue('true')
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('is_active=true'))).toBe(true)
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer le filtre activité' }))
    expect(await screen.findByRole('link', { name: 'Bob Durand' })).toBeInTheDocument()
    expect(query().has('is_active')).toBe(false)
    expect(screen.getByText('Inactif')).toBeInTheDocument()
  })

  it('opens the protected route, keeps loading local, and renders the v1 contract', async () => {
    let resolve!: (response: Response) => void
    mockApi(() => new Promise((done) => { resolve = done }))
    renderAt()
    expect(await screen.findByText('Chargement des employés…')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Employés' })).toHaveAttribute('aria-current', 'page')
    await waitFor(() => expect(resolve).toBeTypeOf('function'))
    await act(async () => resolve(jsonResponse(collection())))
    expect(await loaded()).toHaveAttribute('href', '/app/employees/1')
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('Chercheuse')).toBeInTheDocument()
    expect(screen.getByText('Ingénieure')).toBeInTheDocument()
    expect(screen.getByText('Marie Curie')).toBeInTheDocument()
    expect(screen.getByText('Actif')).toBeInTheDocument()
    expect(screen.getByText('Inactif')).toBeInTheDocument()
    expect(screen.getAllByText('02/01/2020')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Précédent' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Suivant' })).toBeDisabled()
  })

  it('navigates from the sidebar to the React list', async () => {
    mockApi()
    renderAt('/app/')
    await userEvent.click(await screen.findByRole('link', { name: 'Employés' }))
    expect(await loaded()).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/employees/')
  })

  it('leaves scope decisions to the API even without a navigation capability', async () => {
    mockApi(undefined, userWithoutNavigationCapabilities)
    renderAt()
    expect(await loaded()).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Employés' })).not.toBeInTheDocument()
  })

  it('distinguishes an empty accessible collection', async () => {
    mockApi(async () => jsonResponse(collection([])))
    renderAt()
    expect(await screen.findByRole('heading', { name: 'Aucun résultat' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Effacer les critères' })).toBeInTheDocument()
  })

  it('distinguishes no results and clears search and filters', async () => {
    mockApi(async (url) => jsonResponse(url.includes('search=') ? collection([]) : collection()))
    renderAt('/app/employees/?search=inconnu&is_active=false')
    expect(await screen.findByRole('heading', { name: 'Aucun résultat' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Effacer les critères' }))
    expect(await loaded()).toBeInTheDocument()
    expect(query().has('search')).toBe(false)
    expect(query().has('is_active')).toBe(false)
  })

  it('shows a local network error and retries without losing the shell or URL', async () => {
    let failing = true
    mockApi(async () => { if (failing) throw new TypeError('Network error'); return jsonResponse(collection()) })
    renderAt('/app/employees/?search=Alice')
    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de charger')
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument()
    failing = false
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(await loaded()).toBeInTheDocument()
    expect(query().get('search')).toBe('Alice')
  })

  it('submits search to the server and resets offset without client filtering', async () => {
    const fetchMock = mockApi()
    renderAt('/app/employees/?offset=25')
    await loaded()
    await userEvent.type(screen.getByRole('searchbox'), 'Alice{Enter}')
    await loaded()
    expect(query().get('search')).toBe('Alice')
    expect(query().has('offset')).toBe(false)
    expect(fetchMock).toHaveBeenLastCalledWith('/api/v1/employees/?search=Alice&is_active=true', expect.objectContaining({ credentials: 'include' }))
    expect(screen.getByRole('link', { name: 'Bob Durand' })).toBeInTheDocument()
  })

  it('filters activity and resets criteria while preserving ordering', async () => {
    const fetchMock = mockApi()
    renderAt('/app/employees/?search=Alice&ordering=-entry_date&offset=25')
    await loaded()
    await filterActivity('false')
    await loaded()
    expect(query().get('is_active')).toBe('false')
    expect(query().has('offset')).toBe(false)
    expect(fetchMock.mock.calls.at(-1)?.[0]).toBe('/api/v1/employees/?search=Alice&is_active=false&ordering=-entry_date')
    await userEvent.click(screen.getByRole('button', { name: 'Réinitialiser la recherche et les filtres' }))
    await loaded()
    expect(window.location.search).toBe('?ordering=-entry_date&filters_initialized=1')
    expect(screen.getByRole('searchbox')).toHaveValue('')
    expect(screen.queryByLabelText('Activité')).not.toBeInTheDocument()
  })

  it('restores URL state and paginates using limit/offset only', async () => {
    mockApi(async () => jsonResponse(collection([alice], { count: 75, next: 'http://django/api/v1/employees/?offset=50', previous: 'http://django/api/v1/employees/' })))
    renderAt('/app/employees/?search=Alice&is_active=true&ordering=-entry_date&limit=10&offset=10')
    await loaded()
    expect(screen.getByRole('searchbox')).toHaveValue('Alice')
    expect(screen.getByLabelText('Activité')).toHaveValue('true')
    expect(screen.getByText('Page 2 sur 8')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: /Entrée/ })).toHaveAttribute('aria-sort', 'descending')
    await userEvent.click(screen.getByRole('button', { name: 'Suivant' }))
    await loaded()
    expect(query().get('offset')).toBe('20')
    expect(query().get('search')).toBe('Alice')
    await userEvent.click(screen.getByRole('button', { name: 'Précédent' }))
    await loaded()
    expect(query().get('offset')).toBe('10')
  })

  it('sorts accessible headers in both directions and resets pagination', async () => {
    mockApi()
    renderAt('/app/employees/?offset=25')
    await loaded()
    await userEvent.click(screen.getByRole('button', { name: 'Trier par entrée, ordre croissant' }))
    await loaded()
    expect(query().get('ordering')).toBe('entry_date')
    expect(query().has('offset')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Trier par entrée, ordre décroissant' }))
    await loaded()
    expect(query().get('ordering')).toBe('-entry_date')
    expect(screen.getByRole('columnheader', { name: 'Statuts actuels' })).not.toHaveAttribute('aria-sort')
  })

  it('restores search and filters on browser back and forward', async () => {
    mockApi()
    renderAt()
    await loaded()
    await userEvent.type(screen.getByRole('searchbox'), 'Alice{Enter}')
    await loaded()
    await filterActivity('false')
    await loaded()
    act(() => window.history.back())
    await waitFor(() => expect(screen.getByLabelText('Activité')).toHaveValue('true'))
    act(() => window.history.back())
    await waitFor(() => expect(screen.getByRole('searchbox')).toHaveValue(''))
    expect(screen.getByLabelText('Activité')).toHaveValue('true')
    act(() => window.history.forward())
    await waitFor(() => expect(screen.getByRole('searchbox')).toHaveValue('Alice'))
  })

  it('selects one row with the keyboard, changes selection and deselects without navigation', async () => {
    mockApi()
    renderAt()
    await loaded()
    const user = userEvent.setup()
    const first = row('Alice Martin')
    first.focus()
    await user.keyboard(' ')
    expect(first).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Sélection : Alice Martin')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/employees/')
    await user.click(row('Bob Durand'))
    expect(first).toHaveAttribute('aria-selected', 'false')
    expect(screen.queryByText('Sélection : Alice Martin')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Actions pour Bob Durand' }))
    expect(await screen.findByRole('menuitem', { name: /Ouvrir la fiche/ })).toHaveAttribute('href', '/app/employees/2')
    await user.click(screen.getByRole('menuitem', { name: 'Désélectionner' }))
    expect(screen.queryByText(/^Sélection :/)).not.toBeInTheDocument()
    await user.click(first)
    await user.click(first)
    expect(first).toHaveAttribute('aria-selected', 'false')
  })

  it('opens the row menu in one click, selects its row and supports keyboard dismissal', async () => {
    mockApi()
    renderAt()
    await loaded()
    const user = userEvent.setup()
    const trigger = screen.getByRole('button', { name: 'Actions pour Alice Martin' })
    await user.click(trigger)
    await waitFor(() => expect(row('Alice Martin')).toHaveAttribute('aria-selected', 'true'))
    expect(await screen.findAllByRole('menuitem')).toHaveLength(2)
    expect(await screen.findByRole('menuitem', { name: /Ouvrir la fiche/ })).toHaveAttribute('href', '/app/employees/1')
    await user.keyboard('{Escape}')
    await waitFor(() => expect(trigger).toHaveFocus())
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('menu')).toBeInTheDocument()
    await user.click(screen.getByRole('menuitem', { name: 'Désélectionner' }))
    expect(row('Alice Martin')).toHaveAttribute('aria-selected', 'false')
  })

  it('keeps name navigation separate and clears selection when the view changes', async () => {
    mockApi()
    renderAt()
    const link = await loaded()
    const preventNavigation = (event: MouseEvent) => event.preventDefault()
    link.addEventListener('click', preventNavigation)
    fireEvent.click(link)
    expect(link).toHaveAttribute('href', '/app/employees/1')
    expect(row('Alice Martin')).toHaveAttribute('aria-selected', 'false')
    await userEvent.click(row('Alice Martin'))
    await filterActivity('false')
    await loaded()
    expect(screen.queryByText(/^Sélection :/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Admin/ })).not.toBeInTheDocument()
  })

  it('adds filters progressively, removes them and supports closing with Escape', async () => {
    mockApi()
    renderAt()
    await loaded()
    expect(screen.getByLabelText('Activité')).toHaveValue('true')
    const trigger = screen.getByRole('button', { name: 'Ajouter un filtre' })
    await userEvent.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Activité.*Déjà ajouté/ })).toBeDisabled()
    await userEvent.selectOptions(screen.getByLabelText('Activité'), 'false')
    await loaded()
    expect(screen.getByLabelText('Activité')).toHaveValue('false')
    await userEvent.click(trigger)
    expect(screen.getByRole('button', { name: /Activité.*Déjà ajouté/ })).toBeDisabled()
    screen.getByRole('button', { name: 'Fermer la galerie' }).focus()
    await userEvent.keyboard('{Escape}')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer le filtre activité' }))
    await loaded()
    expect(query().has('is_active')).toBe(false)
    expect(screen.queryByLabelText('Activité')).not.toBeInTheDocument()
  })

  it('selects by clicking a cell and ignores keyboard events from the name link', async () => {
    mockApi()
    renderAt()
    const link = await loaded()
    expect(screen.queryByRole('button', { name: /Sélectionner/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('Chercheuse'))
    expect(row('Alice Martin')).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(link, { key: 'Enter' })
    expect(row('Alice Martin')).toHaveAttribute('aria-selected', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Alice Martin' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Désélectionner' }))
    await waitFor(() => expect(row('Alice Martin')).toHaveFocus())
    await userEvent.keyboard('{Enter}')
    expect(row('Alice Martin')).toHaveAttribute('aria-selected', 'true')
  })

  it('aborts superseded requests and ignores late responses', async () => {
    let resolve!: (response: Response) => void
    let signal: AbortSignal | null | undefined
    mockApi((url, init) => {
      if (url.includes('is_active=false')) return Promise.resolve(jsonResponse(collection([bob])))
      signal = init?.signal
      return new Promise((done) => { resolve = done })
    })
    renderAt('/app/employees/?filters_initialized=1')
    await screen.findByText('Chargement des employés…')
    await filterActivity('false')
    expect(await screen.findByRole('link', { name: 'Bob Durand' })).toBeInTheDocument()
    expect(signal?.aborted).toBe(true)
    await act(async () => resolve(jsonResponse(collection([alice]))))
    expect(screen.queryByRole('link', { name: 'Alice Martin' })).not.toBeInTheDocument()
  })

  it('offers recovery from a now-empty page', async () => {
    mockApi(async (url) => jsonResponse(url.includes('offset') ? collection([], { count: 2, previous: '/api/v1/employees/' }) : collection()))
    renderAt('/app/employees/?offset=50')
    expect(await screen.findByRole('heading', { name: 'Cette page est vide' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Première page' }))
    expect(await loaded()).toBeInTheDocument()
    expect(query().has('offset')).toBe(false)
  })

  it('normalizes unsupported and malformed URL parameters before requesting', async () => {
    const fetchMock = mockApi()
    renderAt('/app/employees/?limit=999&offset=-4&is_active=oops&ordering=email&page=2')
    await loaded()
    expect(window.location.search).toBe('?limit=250&filters_initialized=1')
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/v1/employees/?limit=250')).toBe(true)
  })

  it('searches visible superiors with v1 and sends only their selected ID to the list', async () => {
    const fetchMock = mockApi(async (url) => {
      if (url === '/api/v1/employees/9/') return jsonResponse({ ...alice, id: 9, first_name: 'Marie', last_name: 'Curie' })
      const params = new URL(url, 'http://localhost').searchParams
      if (params.get('limit') === '10') return jsonResponse(collection([{ ...alice, id: 9, first_name: 'Marie', last_name: 'Curie' }]))
      return jsonResponse(collection())
    })
    renderAt('/app/employees/?is_active=true&offset=25')
    await loaded()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.click(screen.getByRole('button', { name: /Supérieur/ }))
    expect(query().get('superior')).toBe('')
    expect(screen.getByRole('combobox', { name: 'Supérieur' })).toHaveFocus()
    await userEvent.type(screen.getByRole('combobox', { name: 'Supérieur' }), 'Marie')
    await screen.findByRole('option', { name: 'Marie Curie' })
    await userEvent.keyboard('{ArrowDown}{Enter}')
    expect(await screen.findByDisplayValue('Marie Curie')).toBeInTheDocument()
    expect(query().get('superior')).toBe('9')
    expect(query().get('is_active')).toBe('true')
    expect(query().has('offset')).toBe(false)
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/v1/employees/?search=Marie&is_active=true&limit=10')).toBe(true)
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/v1/employees/?is_active=true&superior=9')).toBe(true)
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('superior=' + '&'))).toBe(false)
    await loaded()
  })

  it('restores a superior label from detail without downloading the employee collection', async () => {
    const fetchMock = mockApi(async (url) => url === '/api/v1/employees/9/' ? jsonResponse({ ...alice, id: 9, first_name: 'Marie', last_name: 'Curie' }) : jsonResponse(collection()))
    renderAt('/app/employees/?superior=9')
    expect(await screen.findByDisplayValue('Marie Curie')).toBeInTheDocument()
    await loaded()
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(expect.arrayContaining(['/api/v1/employees/9/', '/api/v1/employees/?is_active=true&superior=9']))
    expect(fetchMock.mock.calls.map(([url]) => url)).toContain('/api/v1/employees/filter-options/')
  })

  it('restores cumulative status, Team and Project filters with sort and pagination from the URL', async () => {
    const fetchMock = mockApi(async (url) => url === '/api/v1/projects/8/'
      ? jsonResponse({ id: 8, name: 'Atlas' })
      : jsonResponse(collection([alice], { count: 75, next: '/api/v1/employees/?offset=50', previous: '/api/v1/employees/?offset=0' })))
    renderAt('/app/employees/?is_active=true&status=3&current_status=3&team=6&project=8&ordering=-entry_date&limit=10&offset=10')
    await screen.findByRole('link', { name: 'Alice Martin' }, { timeout: 8000 })
    expect(screen.getByLabelText('Statut')).toHaveValue('3')
    expect(screen.getByLabelText('Statut actuel')).toHaveValue('3')
    expect(screen.getByLabelText('Équipe')).toHaveValue('6')
    expect(await screen.findByDisplayValue('Atlas')).toBeInTheDocument()
    expect(screen.getByText('Page 2 sur 8')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Suivant' }))
    await waitFor(() => expect(query().get('offset')).toBe('20'))
    expect(query().get('project')).toBe('8')
    expect(query().get('ordering')).toBe('-entry_date')
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('current_status=3') && String(url).includes('project=8') && String(url).includes('offset=20'))).toBe(true)
  })

  it('uses the shared searchable selector to choose a Project and resets only pagination', async () => {
    const fetchMock = mockApi(async (url) => {
      if (url.startsWith('/api/v1/projects/?')) return jsonResponse({ count: 1, next: null, previous: null, results: [{ id: 8, name: 'Atlas' }] })
      if (url === '/api/v1/projects/8/') return jsonResponse({ id: 8, name: 'Atlas' })
      return jsonResponse(collection([alice]))
    })
    renderAt('/app/employees/?is_active=true&ordering=-entry_date&offset=25')
    await loaded()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.click(screen.getByRole('button', { name: /^Projet$/ }))
    const project = screen.getByRole('combobox', { name: 'Projet' })
    await userEvent.type(project, 'Atlas')
    await screen.findByRole('option', { name: 'Atlas' })
    await userEvent.keyboard('{ArrowDown}{Enter}')
    await waitFor(() => expect(query().get('project')).toBe('8'))
    expect(query().has('offset')).toBe(false)
    expect(query().get('ordering')).toBe('-entry_date')
    expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/projects/?search=Atlas') && String(url).includes('limit=10'))).toBe(true)
    expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/employees/?') && String(url).includes('project=8'))).toBe(true)
  })

  it('offers Name, status, current status and Team in the filter gallery', async () => {
    mockApi()
    renderAt()
    await loaded()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    for (const label of ['Nom', 'Statut', 'Statut actuel', 'Équipe', 'Projet']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
    await userEvent.click(screen.getByRole('button', { name: /^Nom$/ }))
    await userEvent.type(screen.getByLabelText('Nom'), 'Alice')
    await waitFor(() => expect(query().get('search')).toBe('Alice'))
    expect(screen.getByRole('searchbox')).toHaveValue('Alice')
  })

  it('applies status and Team choices together while preserving sort and resetting the page', async () => {
    const fetchMock = mockApi()
    renderAt('/app/employees/?is_active=true&ordering=-entry_date&offset=25')
    await loaded()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.click(screen.getByRole('button', { name: 'Statut' }))
    await userEvent.selectOptions(screen.getByLabelText('Statut'), '3')
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
    await userEvent.click(screen.getByRole('button', { name: 'Équipe' }))
    await userEvent.selectOptions(screen.getByLabelText('Équipe'), '6')
    await waitFor(() => expect(query().get('team')).toBe('6'))
    expect(query().get('status')).toBe('3')
    expect(query().get('ordering')).toBe('-entry_date')
    expect(query().has('offset')).toBe(false)
    expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/employees/?') && String(url).includes('status=3') && String(url).includes('team=6'))).toBe(true)
  })

  it('returns from an Employee detail to the exact filtered list URL', async () => {
    mockApi(async (url) => {
      if (url === '/api/v1/employees/1/') return jsonResponse({ ...alice, birth_date: null, email: null, contract_quotity: null, project_quotity: null, contribution_quotity: null, active_milestones_count: 0 })
      if (url.endsWith('/statuses/')) return jsonResponse([])
      if (url.endsWith('/hierarchy/')) return jsonResponse({ superiors: [], subordinates: [] })
      if (url.endsWith('/generic-info/')) return jsonResponse({ capabilities: { can_add: false }, items: [] })
      return jsonResponse(collection([alice]))
    })
    renderAt('/app/employees/?is_active=true&team=6&ordering=-entry_date&offset=25')
    await userEvent.click(await loaded())
    await userEvent.click(await screen.findByRole('link', { name: 'Retour aux employés' }))
    expect(query().get('team')).toBe('6')
    expect(query().get('ordering')).toBe('-entry_date')
    expect(query().get('offset')).toBe('25')
  })

  it('redirects a 401 to React login with the original list URL', async () => {
    mockApi(async () => jsonResponse({}, 401))
    renderAt('/app/employees/?search=Alice')
    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/login')
    expect(window.history.state.usr.from).toBe('/employees/?search=Alice')
  })

  it('keeps a 403 local and preserves the authenticated shell', async () => {
    mockApi(async () => jsonResponse({}, 403))
    renderAt()
    expect(await screen.findByRole('alert')).toHaveTextContent('Accès interdit')
    expect(screen.getByRole('button', { name: 'Menu utilisateur : Ada' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/employees/')
  })
})
