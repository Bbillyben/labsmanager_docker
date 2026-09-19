import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { authenticatedUser, jsonResponse, userWithoutNavigationCapabilities } from '../test/fixtures'
import { AppRouter } from './AppRouter'

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter>)
}

describe('AppRouter', () => {
  beforeEach(() => { window.history.pushState({}, '', '/app/') })

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
    expect(screen.getByTitle('ada')).toHaveTextContent('Ada Lovelace')
    expect(screen.getByRole('link', { name: 'Interface historique' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Accueil' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Aller au contenu principal' })).toHaveAttribute('href', '#main-content')
  })

  it('logs out through the API and returns to React login', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(authenticatedUser))
      .mockResolvedValueOnce(jsonResponse({ is_authenticated: false }))
    renderAt('/app/')

    await user.click(await screen.findByRole('button', { name: 'Se déconnecter' }))

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/auth/logout/')
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: 'POST' }))
  })

  it('exposes React Employees and historical domains allowed by current capabilities', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    renderAt('/app/')

    expect(await screen.findByRole('link', { name: 'Employés' })).toHaveAttribute('href', '/app/employees/')
    expect(screen.getByRole('link', { name: 'Projets' })).toHaveAttribute('href', '/project/')
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
})
