import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser, jsonResponse, userWithoutNavigationCapabilities } from '../test/fixtures'
import { AppRouter } from './AppRouter'

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}

describe('AppRouter', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/app/')
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    document.documentElement.classList.remove('dark')
    localStorage.removeItem('labsmanager-theme')
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
    expect(screen.getByRole('link', { name: 'Contrats' })).toHaveAttribute('href', '/app/tools/contracts')
    expect(screen.queryByRole('button', { name: /Actions pour Jean Dupont/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Aucun contrat visible.')).not.toBeInTheDocument()
  })

  it('logs out through the API and returns to React login', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(authenticatedUser))
      .mockResolvedValueOnce(jsonResponse({ is_authenticated: false }))
    renderAt('/app/')

    await user.click(await screen.findByRole('button', { name: 'Menu utilisateur : Ada' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Se déconnecter' }))

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/auth/logout/')
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: 'POST' }))
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
    expect(fetchMock.mock.calls.map(([input]) => String(input))).toContain('/api/v1/teams/?')
    expect(await screen.findByRole('link', { name: 'Atlas' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Atlas' }))
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Page introuvable' })).not.toBeInTheDocument()
  })
})
