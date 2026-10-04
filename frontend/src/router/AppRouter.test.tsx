import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import * as djangoUrls from '../config/django'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser, jsonResponse, userWithoutNavigationCapabilities } from '../test/fixtures'
import { AppRouter } from './AppRouter'

vi.mock('../pages/OrganizationChartPage', () => ({ OrganizationChartPage: () => <h1>Organigramme interactif</h1> }))
vi.mock('../pages/GlobalCalendarsPage', () => ({ GlobalCalendarsPage: () => <h1>Calendrier général</h1> }))

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}

function showTools() {
  const toggle = screen.getByRole('button', { name: 'Outils' })
  if (toggle.getAttribute('aria-expanded') === 'false') fireEvent.click(toggle)
}

describe('AppRouter', () => {
  it('loads the shareable Global Search route inside the authenticated shell', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(userWithoutNavigationCapabilities)
      if (url === '/api/v1/search/schema/') return jsonResponse({ providers: [] })
      if (url.startsWith('/api/v1/search/?')) return jsonResponse({ query: 'atlas', results: [], groups: {} })
      throw new Error(url)
    })
    renderAt('/app/search?q=atlas')
    expect(await screen.findByRole('heading', { name: 'Résultats pour « atlas »' })).toBeInTheDocument()
    expect(await screen.findByText('Aucun résultat pour « atlas »')).toBeInTheDocument()
  })
  it('opens the personal Dashboard directly for an authenticated user without the legacy Dashboard capability', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(userWithoutNavigationCapabilities)
      if (url === '/api/v1/dashboards/') return jsonResponse([])
      if (url === '/api/v1/dashboards/catalog/') return jsonResponse({ scope: 'user', sources: [], definitions: [] })
      throw new Error(url)
    })
    renderAt('/app/dashboard')
    expect(await screen.findByText('Choisissez votre tableau de bord initial')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Tableau de bord' })).toHaveAttribute('href', '/app/dashboard')
  })
  it('opens the presentation route without Sidebar or Topbar', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(userWithoutNavigationCapabilities)
      if (url === '/api/v1/dashboards/7/') return jsonResponse({ id: 7, name: 'Projected dashboard', scope: 'user', widgets: [] })
      if (url === '/api/v1/dashboards/catalog/') return jsonResponse({ scope: 'user', sources: [], definitions: [] })
      throw new Error(url)
    })
    renderAt('/app/dashboard/7/present')
    expect(await screen.findByRole('heading', { name: 'Projected dashboard' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tableau de bord' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Quitter la présentation' })).toHaveAttribute('href', '/app/dashboard?selected=7')
  })
  it('loads Calendars directly as a main navigation entry', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(userWithoutNavigationCapabilities))
    renderAt('/app/calendars')
    expect(await screen.findByRole('heading', { name: 'Calendrier général' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Calendriers' })).toHaveAttribute('href', '/app/calendars')
  })
  it('loads the Import Hub route directly for a permitted user', async () => {
    const account = { ...authenticatedUser, capabilities: { ...authenticatedUser.capabilities, import_data: true } }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(account)
      if (url === '/api/v1/imports/profiles/') return jsonResponse({ items: [] })
      throw new Error(url)
    })
    renderAt('/app/tools/import')
    expect(await screen.findByText('Aucun profil d’import autorisé.')).toBeInTheDocument()
    showTools()
    expect(screen.getByRole('link', { name: 'Import' })).toHaveAttribute('href', '/app/tools/import')
  })
  it('loads the organization chart route directly for an authenticated user', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(userWithoutNavigationCapabilities))
    renderAt('/app/tools/organization-chart')
    expect(await screen.findByRole('heading', { name: 'Organigramme interactif' })).toBeInTheDocument()
    showTools()
    expect(screen.getByRole('link', { name: 'Organigramme' })).toHaveAttribute('href', '/app/tools/organization-chart')
  })
  beforeEach(() => {
    window.history.pushState({}, '', '/app/')
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    document.documentElement.classList.remove('dark')
    localStorage.removeItem('labsmanager-theme')
  })

  it.each(['fund-items', 'budgets', 'expenses'] as const)('loads the %s financial tool and its navigation for an authenticated user', async (kind) => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(userWithoutNavigationCapabilities)
      if (url === '/api/v1/financial/filter-options/') return jsonResponse({ cost_types: [], contract_types: [], employee_types: [], statuses: [] })
      if (url.startsWith(`/api/v1/${kind}/?`)) return jsonResponse({ count: 0, next: null, previous: null, results: [] })
      throw new Error(url)
    })
    renderAt(`/app/tools/${kind}`)
    expect(await screen.findByText('Aucun résultat.')).toBeInTheDocument()
    showTools()
    const label = kind === 'fund-items' ? 'Explorateur de fonds' : kind === 'budgets' ? 'Explorateur de budgets' : 'Dépenses'
    expect(screen.getByRole('link', { name: label })).toHaveAttribute('href', `/app/tools/${kind}`)
  })

  it.each(['institutions', 'funders'] as const)('loads the %s organization route directly', async (kind) => {
    const account = { ...authenticatedUser, capabilities: { ...authenticatedUser.capabilities, view_organizations: true } }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(account)
      if (url.startsWith(`/api/v1/organizations/${kind}/?`)) return jsonResponse({ count: 0, next: null, previous: null, results: [], capabilities: { can_add: false } })
      throw new Error(url)
    })
    renderAt(`/app/organizations/${kind}`)
    expect(await screen.findByRole('heading', { name: kind === 'institutions' ? 'Institutions' : 'Financeurs' })).toBeInTheDocument()
    expect(screen.queryByText('Page introuvable')).not.toBeInTheDocument()
  })

  it('protects the home page with the React login route', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ is_authenticated: false }))
    renderAt('/app/')

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/login')
    expect(screen.queryByRole('heading', { name: 'Accueil' })).not.toBeInTheDocument()
  })

  it('logs in and returns to the originally requested React route', async () => {
    const user = userEvent.setup()
    document.cookie = 'csrftoken=login-token'
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ is_authenticated: false }))
      .mockResolvedValueOnce(jsonResponse({ is_authenticated: true }))
      .mockResolvedValueOnce(jsonResponse(authenticatedUser))
    renderAt('/app/inconnue')

    await user.type(await screen.findByLabelText('Identifiant ou email'), 'ada')
    await user.type(screen.getByLabelText('Mot de passe'), 'secret')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/inconnue')
    const loginInit = fetchMock.mock.calls[1][1] as RequestInit
    expect(new Headers(loginInit.headers).get('X-CSRFToken')).toBe('login-token')
  })

  it('shows a generic error without leaving the login page', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ is_authenticated: false }))
      .mockResolvedValueOnce(jsonResponse({ error: { code: 'invalid_credentials' } }, 400))
    renderAt('/app/login')

    await user.type(await screen.findByLabelText('Identifiant ou email'), 'unknown')
    await user.type(screen.getByLabelText('Mot de passe'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Identifiant ou mot de passe incorrect.')
    expect(window.location.pathname).toBe('/app/login')
  })

  it('renders the authenticated shell and identity', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/')

    expect(await screen.findByRole('heading', { name: 'Bienvenue, Ada Lovelace' })).toBeInTheDocument()
    expect(screen.getByTitle('ada')).toHaveTextContent('Ada')
    expect(screen.getAllByText('Accueil', { selector: 'span' })).toHaveLength(2)
    const topbar = screen.getByRole('button', { name: 'Menu utilisateur : Ada' }).closest('header')!
    expect(within(topbar).queryByText('Interface historique')).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Accueil' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Aller au contenu principal' })).toHaveAttribute('href', '#main-content')
  })

  it('opens Settings from the user menu and preserves its nested route', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/settings/account/') return jsonResponse({
        username: 'ada', first_name: 'Ada', last_name: 'Lovelace', last_login: null,
        employee: { id: 42, name: 'Ada Lovelace' }, has_usable_password: true,
        can_add: true, emails: [],
      })
      if (url === '/api/v1/settings/lists/') return jsonResponse({ groups: [] })
      if (url === '/api/v1/settings/user/interface/') return jsonResponse({ settings: [] })
      if (url === '/api/v1/settings/user/notifications/') return jsonResponse({ settings: [] })
      if (url === '/api/v1/settings/user/stale/') return jsonResponse({ settings: [] })
      if (url === '/api/v1/favorites/' || url === '/api/v1/subscriptions/') return jsonResponse([])
      throw new Error(url)
    })
    renderAt('/app/settings')
    expect(await screen.findByText('Changer le mot de passe', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/settings/user')
    await user.click(screen.getByRole('button', { name: 'Menu utilisateur : Ada' }))
    expect(await screen.findByRole('menuitem', { name: 'Paramètres' })).toHaveAttribute('href', '/app/settings/user')
    await user.click(screen.getByRole('link', { name: 'Interface' }))
    expect(window.location.pathname).toBe('/app/settings/interface')
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/v1/settings/user/interface/')).toBe(true)
    await user.click(screen.getByRole('link', { name: 'Notifications' }))
    expect(window.location.pathname).toBe('/app/settings/notifications')
    await user.click(screen.getByRole('link', { name: 'Favoris et abonnements' }))
    expect(window.location.pathname).toBe('/app/settings/common')
    await user.click(screen.getByRole('link', { name: 'Alertes d’échéance' }))
    expect(window.location.pathname).toBe('/app/settings/stale')
    expect(screen.queryByRole('link', { name: /Dashboard Settings/i })).not.toBeInTheDocument()
  }, 10000)

  it('loads a LabsManager list group directly through Settings Hub', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/settings/lists/') return jsonResponse({ groups: [{ key: 'fund', label: 'Fund', lists: [{ key: 'cost-types', group: 'fund', label: 'Cost Types', columns: ['name'], fields: [{ key: 'name', label: 'Name', type: 'text', required: true, readonly: false, choices: [] }], capabilities: { can_view: true, can_add: false, can_change: false, can_delete: false } }] }] })
      if (url === '/api/v1/settings/lists/cost-types/') return jsonResponse({ list: { key: 'cost-types', group: 'fund', label: 'Cost Types', columns: ['name'], fields: [{ key: 'name', label: 'Name', type: 'text', required: true, readonly: false, choices: [] }], capabilities: { can_view: true, can_add: false, can_change: false, can_delete: false } }, rows: [] })
      throw new Error(url)
    })
    renderAt('/app/settings/lists/fund')
    expect(await screen.findByRole('link', { name: 'Fund' }, { timeout: 10000 })).toHaveAttribute('href', '/app/settings/lists/fund')
    expect(await screen.findByRole('heading', { name: 'Cost Types' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Page introuvable' })).not.toBeInTheDocument()
  }, 15000)

  it('saves a typed personal stale setting and reports validation errors', async () => {
    const user = userEvent.setup()
    let attempts = 0
    const setting = { key: 'DASHBOARD_PROJECT_STALE_TO_MONTH', name: 'Project stale month', description: 'Months', type: 'integer', value: 3, default: 3, choices: [], can_change: true }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/settings/user/stale/' && init?.method === 'GET') return jsonResponse({ settings: [setting] })
      if (url.endsWith('/DASHBOARD_PROJECT_STALE_TO_MONTH/')) {
        attempts += 1
        return attempts === 1 ? jsonResponse({ value: ['Invalid value'] }, 400) : jsonResponse({ ...setting, value: 5 })
      }
      throw new Error(url)
    })
    renderAt('/app/settings/stale')
    const field = await screen.findByLabelText('Project stale month')
    expect(field).toHaveValue(3)
    await user.clear(field)
    await user.type(field, '5')
    expect(screen.queryByRole('button', { name: 'Enregistrer' })).not.toBeInTheDocument()
    fireEvent.blur(field)
    expect(await screen.findByText('Invalid value')).toBeInTheDocument()
    fireEvent.focus(field)
    fireEvent.blur(field)
    expect(await screen.findByText('Enregistré')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/DASHBOARD_PROJECT_STALE_TO_MONTH/'))).toHaveLength(2)
  })

  it('autosaves interface controls and keeps the server value when a choice fails', async () => {
    const user = userEvent.setup()
    const toggle = { key: 'SHOW_PAST_ORG', name: 'Current organisation only', description: 'Display', type: 'boolean', value: false, default: false, choices: [], can_change: true }
    const choice = { key: 'MAP_PROVIDER', name: 'Map provider', description: 'Maps', type: 'choice', value: 'gmap', default: 'gmap', choices: [{ value: 'gmap', label: 'Google Map' }, { value: 'opensm', label: 'OpenStreetMap' }], can_change: true }
    let resolveToggle: ((response: Response) => void) | undefined
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/settings/user/interface/' && init?.method === 'GET') return jsonResponse({ settings: [toggle, choice] })
      if (url.endsWith('/SHOW_PAST_ORG/')) return new Promise<Response>((resolve) => { resolveToggle = resolve })
      if (url.endsWith('/MAP_PROVIDER/')) return jsonResponse({ value: ['Unsupported provider'] }, 400)
      throw new Error(url)
    })
    renderAt('/app/settings/interface')
    const switchField = await screen.findByRole('switch', { name: 'Current organisation only' })
    expect(screen.queryByRole('button', { name: 'Enregistrer' })).not.toBeInTheDocument()
    await user.click(switchField)
    expect(screen.getByText('Enregistrement…')).toBeInTheDocument()
    expect(switchField).not.toBeChecked()
    resolveToggle?.(jsonResponse({ ...toggle, value: true }))
    expect(await screen.findByText('Enregistré')).toBeInTheDocument()
    expect(switchField).toBeChecked()
    const select = screen.getByLabelText('Map provider')
    await user.selectOptions(select, 'opensm')
    expect(await screen.findByText('Unsupported provider')).toBeInTheDocument()
    expect(select).toHaveValue('gmap')
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/MAP_PROVIDER/'))).toHaveLength(1)
  })

  it('shows existing favorites and subscriptions with their R2.21 removal action', async () => {
    const user = userEvent.setup()
    const item = { type: 'project', group: 'projects', id: 7, label: 'Atlas', url: '/projects/7', legacy: false }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/favorites/' || url === '/api/v1/subscriptions/') return jsonResponse([item])
      if (url === '/api/v1/preferences/project/7/') return jsonResponse({ favorite: false, subscription: true })
      throw new Error(url)
    })
    renderAt('/app/settings/common')
    expect(await screen.findAllByRole('link', { name: 'Atlas' })).toHaveLength(2)
    const favorites = screen.getByRole('heading', { name: 'Favoris' }).closest('section')!
    const subscriptions = screen.getByRole('heading', { name: 'Abonnements' }).closest('section')!
    expect(favorites.parentElement).toBe(subscriptions.parentElement)
    expect(favorites.parentElement?.className).toMatch(/preferenceGrid/)
    expect(within(favorites).getByText('Projets')).toBeInTheDocument()
    expect(within(subscriptions).getByText('Projets')).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Retirer' })[0])
    expect(fetchMock.mock.calls.some(([url, init]) => url === '/api/v1/preferences/project/7/' && init?.method === 'PUT')).toBe(true)
  })

  it('submits password and new email through the React account forms', async () => {
    const user = userEvent.setup()
    const account = {
      username: 'ada', first_name: 'Ada', last_name: 'Lovelace', last_login: null,
      employee: null, has_usable_password: true, can_add: true, emails: [],
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/settings/account/') return jsonResponse(account)
      if (url === '/api/v1/settings/account/password/') return jsonResponse({ saved: true, logged_out: false })
      if (url === '/api/v1/settings/account/emails/') return jsonResponse({ can_add: true, emails: [{ id: 9, email: 'ada@example.test', verified: false, primary: false, can_delete: true, can_make_primary: false, can_resend: true }] }, 201)
      throw new Error(url)
    })
    renderAt('/app/settings/user')
    expect(await screen.findByRole('button', { name: 'Changer le mot de passe' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Mot de passe actuel')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Changer le mot de passe' }))
    await user.type(await screen.findByLabelText('Mot de passe actuel'), 'old-secret')
    await user.type(screen.getByLabelText('Nouveau mot de passe'), 'New-secret-456!')
    await user.type(screen.getByLabelText('Confirmer le nouveau mot de passe'), 'New-secret-456!')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('Mot de passe enregistré.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Mot de passe actuel')).not.toBeInTheDocument()
    await user.type(screen.getByLabelText('Ajouter une adresse e-mail'), 'ada@example.test')
    await user.click(screen.getByRole('button', { name: 'Ajouter une adresse e-mail' }))
    expect(await screen.findByText('ada@example.test')).toBeInTheDocument()
    expect(screen.getByText('Secondaire')).toBeInTheDocument()
    expect(screen.getByText('Non vérifiée')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url, init]) => url === '/api/v1/settings/account/password/' && init?.method === 'POST')).toBe(true)
    expect(fetchMock.mock.calls.some(([url, init]) => url === '/api/v1/settings/account/emails/' && init?.method === 'POST')).toBe(true)
  }, 10000)

  it('shows email states and offers only the allauth actions allowed for each address', async () => {
    const user = userEvent.setup()
    const primary = { id: 1, email: 'primary@example.test', primary: true, verified: true, can_delete: true, can_make_primary: false, can_resend: false }
    const unverified = { id: 2, email: 'new@example.test', primary: false, verified: false, can_delete: true, can_make_primary: false, can_resend: true }
    const verified = { id: 3, email: 'verified@example.test', primary: false, verified: true, can_delete: true, can_make_primary: true, can_resend: false }
    let emails = [primary, unverified, verified]
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/settings/account/') return jsonResponse({ username: 'ada', first_name: 'Ada', last_name: 'Lovelace', last_login: null, employee: null, has_usable_password: true, can_add: false, emails })
      if (url === '/api/v1/settings/account/emails/2/' && init?.method === 'PATCH') return jsonResponse({ can_add: false, emails })
      if (url === '/api/v1/settings/account/emails/3/' && init?.method === 'PATCH') {
        emails = [{ ...primary, primary: false, can_delete: true, can_make_primary: true }, unverified, { ...verified, primary: true, can_delete: false, can_make_primary: false }]
        return jsonResponse({ can_add: false, emails })
      }
      if (url === '/api/v1/settings/account/emails/2/' && init?.method === 'DELETE') {
        emails = emails.filter((row) => row.id !== 2)
        return jsonResponse({ can_add: false, emails })
      }
      throw new Error(url)
    })
    renderAt('/app/settings/user')
    expect(await screen.findByText('primary@example.test')).toBeInTheDocument()
    expect(screen.getAllByText('Principale')).toHaveLength(1)
    expect(screen.getAllByText('Secondaire')).toHaveLength(2)
    expect(screen.getAllByText('Vérifiée')).toHaveLength(2)
    expect(screen.getByText('Non vérifiée')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour primary@example.test' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Actions pour new@example.test' }))
    expect(screen.queryByRole('menuitem', { name: 'Définir comme principale' })).not.toBeInTheDocument()
    await user.click(await screen.findByRole('menuitem', { name: 'Renvoyer la vérification' }))
    expect(await screen.findByText('E-mail de vérification demandé.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Actions pour verified@example.test' }))
    expect(screen.queryByRole('menuitem', { name: 'Renvoyer la vérification' })).not.toBeInTheDocument()
    await user.click(await screen.findByRole('menuitem', { name: 'Définir comme principale' }))
    expect(await screen.findByText('Adresse principale mise à jour.')).toBeInTheDocument()
    expect(screen.getByText('verified@example.test').closest('li')).toHaveTextContent('Principale')
    expect(screen.getByText('primary@example.test').closest('li')).toHaveTextContent('Secondaire')

    await user.click(screen.getByRole('button', { name: 'Actions pour new@example.test' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Supprimer' }))
    expect(await screen.findByText('Adresse supprimée.')).toBeInTheDocument()
    expect(screen.queryByText('new@example.test')).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url, init]) => url === '/api/v1/settings/account/emails/2/' && init?.method === 'DELETE')).toBe(true)
  }, 15000)

  it('opens an empty Contract Hub from Tools without a global Contract permission', async () => {
    const account = { ...authenticatedUser, capabilities: { ...authenticatedUser.capabilities, view_contract_list: false } }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(account)
      if (url === '/api/v1/contracts/filter-options/') return jsonResponse({ contract_types: [], statuses: [], funders: [], institutions: [] })
      if (url.startsWith('/api/v1/contracts/?')) return jsonResponse({ count: 0, next: null, previous: null, results: [] })
      throw new Error(`Unexpected ${url}`)
    })
    renderAt('/app/tools/contracts')
    expect(await screen.findByRole('heading', { name: 'Contrats' })).toBeInTheDocument()
    expect(screen.getByText('Outils')).toBeInTheDocument()
    showTools()
    expect(screen.getByRole('link', { name: 'Contrats' })).toHaveAttribute('href', '/app/tools/contracts')
    expect(await screen.findByText('Aucun contrat visible.')).toBeInTheDocument()
    expect(screen.queryByText('Page introuvable')).not.toBeInTheDocument()
  })

  it('shows visible Contracts in the Hub without a global Contract permission', async () => {
    const account = { ...authenticatedUser, capabilities: { ...authenticatedUser.capabilities, view_contract_list: false } }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(account)
      if (url === '/api/v1/contracts/filter-options/') return jsonResponse({ contract_types: [], statuses: [], funders: [], institutions: [] })
      if (url.startsWith('/api/v1/contracts/?')) return jsonResponse({ count: 1, next: null, previous: null, results: [{
        id: 7, admin_url: null,
        employee: { id: 12, first_name: 'Jean', last_name: 'Dupont', can_view: true },
        contract_type: { id: 2, name: 'CDD Recherche' },
        fund: { id: 20, reference: 'REF-20', project: { id: 3, name: 'Atlas', can_view: true } },
        status: { code: 'effe', label: 'Effective' }, is_active: true,
        start_date: '2026-01-01', end_date: '2026-12-31', quotity: '0.500', total_amount: '25.00',
        capabilities: { can_change: false }, notes: { visible_count: 0, can_add: false },
      }] })
      throw new Error(`Unexpected ${url}`)
    })
    renderAt('/app/tools/contracts')
    expect(await screen.findByRole('row', { name: /Jean Dupont/ })).toBeInTheDocument()
    showTools()
    expect(screen.getByRole('link', { name: 'Contrats' })).toHaveAttribute('href', '/app/tools/contracts')
    expect(screen.queryByRole('button', { name: /Actions pour Jean Dupont/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Aucun contrat visible.')).not.toBeInTheDocument()
  })

  it('logs out through the API and returns to React login', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (String(input) === '/api/v1/search/schema/') return jsonResponse({ providers: [] })
      if (String(input) === '/api/v1/auth/logout/') return jsonResponse({ is_authenticated: false })
      throw new Error(String(input))
    })
    renderAt('/app/')

    await user.click(await screen.findByRole('button', { name: 'Menu utilisateur : Ada' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Se déconnecter' }))

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    const logoutCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/v1/auth/logout/')
    expect(logoutCall?.[1]).toEqual(expect.objectContaining({ method: 'POST' }))
  })

  it('links the user menu to the associated Employee profile', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/')

    await user.click(await screen.findByRole('button', { name: 'Menu utilisateur : Ada' }))

    expect(await screen.findByRole('menuitem', { name: 'Ma fiche' })).toHaveAttribute('href', '/app/employees/42')
    await user.click(screen.getByRole('menuitem', { name: 'Apparence : thème sombre' }))
    expect(document.documentElement).toHaveClass('dark')
    expect(localStorage.getItem('labsmanager-theme')).toBe('dark')
  })

  it('shows the Django Admin link only when the backend grants access', async () => {
    const user = userEvent.setup()
    const resolveDjangoUrl = vi.spyOn(djangoUrls, 'getDjangoUrl').mockReturnValue('http://django.example:7000/admin/')
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ ...authenticatedUser, can_access_admin: true, admin_url: '/admin/' }))
    renderAt('/app/')
    const trigger = await screen.findByRole('button', { name: 'Menu utilisateur : Ada' })
    await user.click(trigger)
    if (trigger.getAttribute('aria-expanded') === 'false') await user.click(trigger)
    expect(await screen.findByRole('menuitem', { name: 'Admin' })).toHaveAttribute('href', 'http://django.example:7000/admin/')
    expect(resolveDjangoUrl).toHaveBeenCalledWith('/admin/')
    resolveDjangoUrl.mockRestore()
  })

  it('does not show Admin without the backend capability', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ ...authenticatedUser, can_access_admin: false, admin_url: null }))
    renderAt('/app/')
    await user.click(await screen.findByRole('button', { name: 'Menu utilisateur : Ada' }))
    expect(screen.queryByRole('menuitem', { name: 'Admin' })).not.toBeInTheDocument()
  })

  it('does not fall back to a relative Admin path when the backend omits admin_url', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ ...authenticatedUser, can_access_admin: true, admin_url: null }))
    renderAt('/app/')
    await user.click(await screen.findByRole('button', { name: 'Menu utilisateur : Ada' }))
    expect(screen.queryByRole('menuitem', { name: 'Admin' })).not.toBeInTheDocument()
  })

  it('uses the User fallback and omits My profile without an associated Employee', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ ...authenticatedUser, employee: null }))
    renderAt('/app/')

    await user.click(await screen.findByRole('button', { name: 'Menu utilisateur : Ada Lovelace' }))

    expect(screen.queryByRole('menuitem', { name: 'Ma fiche' })).not.toBeInTheDocument()
  })

  it('translates the topbar and user menu from the browser language', async () => {
    const user = userEvent.setup()
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US', 'fr-FR'] })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/')

    expect(await screen.findByRole('link', { name: 'Home' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'User menu : Ada' }))
    expect(await screen.findByRole('menuitem', { name: 'My profile' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Appearance: dark theme' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Sign out' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
  })

  it('exposes React Employees and historical domains allowed by current capabilities', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/')

    expect(await screen.findByRole('link', { name: 'Employés' })).toHaveAttribute('href', '/app/employees/')
    expect(screen.getByRole('link', { name: 'Projets' })).toHaveAttribute('href', '/app/projects/')
    expect(screen.queryByRole('link', { name: 'Équipes' })).not.toBeInTheDocument()
  })

  it('omits the historical domain group when no navigation capability is available', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(userWithoutNavigationCapabilities))
    renderAt('/app/')

    expect(await screen.findByRole('heading', { name: 'Bienvenue, Ada Lovelace' })).toBeInTheDocument()
    expect(screen.queryByText('Interface historique', { selector: 'p' })).not.toBeInTheDocument()
  })

  it('opens and reduces the navigation from an accessible button', async () => {
    const user = userEvent.setup()
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/')

    const toggle = await screen.findByRole('button', { name: 'Réduire la navigation' })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    await user.click(toggle)
    expect(screen.getByRole('button', { name: 'Ouvrir la navigation' })).toHaveAttribute('aria-expanded', 'false')
    expect(document.getElementById('primary-navigation')).toHaveAttribute('data-expanded', 'false')
  })

  it('renders a React 404 for an unknown /app route', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/inconnue')

    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
  })

  it.each([['budgets', 'Budgets', 'Contributions'], ['contributions', 'Contributions', 'Budgets']])('loads the Project %s route directly', async (route, heading, other) => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/projects/3/') return jsonResponse({
        id: 3, name: 'Atlas', status: true, start_date: null, end_date: null,
        funding_visible: true, capabilities: { can_change: false },
      })
      if (url === '/api/v1/projects/3/budgets/' || url === '/api/v1/projects/3/contributions/') {
        return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, items: [] })
      }
      if (url === '/api/v1/projects/3/budgets/options/' || url === '/api/v1/projects/3/contributions/options/') {
        return jsonResponse({ funds: [], cost_types: [], employee_types: [], contract_types: [], employees: [] })
      }
      throw new Error(`Unexpected ${url}`)
    })
    renderAt(`/app/projects/3/${route}`)

    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: other })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Page introuvable' })).not.toBeInTheDocument()
  })

  it('loads Project Contracts directly instead of the React 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/projects/3/') return jsonResponse({
        id: 3, name: 'Atlas', status: true, start_date: null, end_date: null,
        funding_visible: true, capabilities: { can_change: false },
      })
      if (url === '/api/v1/projects/3/contracts/') return jsonResponse({ items: [], capabilities: { can_add: false, can_change: false, can_delete: false } })
      throw new Error(`Unexpected ${url}`)
    })
    renderAt('/app/projects/3/contracts')
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(await screen.findByText('Aucun contrat visible.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Page introuvable' })).not.toBeInTheDocument()
  })

  it('loads Project Calendar directly instead of the React 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url === '/api/v1/projects/3/') return jsonResponse({
        id: 3, name: 'Atlas', status: true, start_date: null, end_date: null,
        funding_visible: true, capabilities: { can_change: false },
      })
      if (url.includes('/calendar/participants/')) return jsonResponse([])
      if (url.includes('/calendar/filters/')) return jsonResponse([])
      if (url.includes('/calendar/?')) return jsonResponse([])
      throw new Error(`Unexpected ${url}`)
    })
    renderAt('/app/projects/3/calendar')
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Ressources' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Page introuvable' })).not.toBeInTheDocument()
  })

  it('loads Team list and Team detail routes directly', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (url.startsWith('/api/v1/teams/?')) return jsonResponse({ count: 1, next: null, previous: null, results: [{ id: 4, name: 'Atlas', leader: { id: 7, name: 'Ada', can_view: true }, mates: [], capabilities: { can_view: true, can_change: false, can_manage_composition: false } }], capabilities: { can_add: false, can_choose_leader: false, default_leader: null } })
      if (url === '/api/v1/teams/4/') return jsonResponse({ id: 4, name: 'Atlas', leader: { id: 7, name: 'Ada', can_view: true }, mates: [], capabilities: { can_view: true, can_change: false, can_manage_composition: false } })
      if (url === '/api/v1/preferences/team/4/') return jsonResponse({ favorite: false, subscription: false })
      throw new Error(`Unexpected ${url}`)
    })
    renderAt('/app/teams/')
    expect(await screen.findByRole('heading', { name: 'Équipes' })).toBeInTheDocument()
    await waitFor(() => expect(fetchMock.mock.calls.map(([input]) => String(input))).toContain('/api/v1/teams/?'))
    expect(await screen.findByRole('link', { name: 'Atlas' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Atlas' }))
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Page introuvable' })).not.toBeInTheDocument()
  })
})
