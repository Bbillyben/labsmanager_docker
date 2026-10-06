import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { AppRouter } from '../router/AppRouter'

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}

describe('React password reset', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark')
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  })
  afterEach(() => vi.restoreAllMocks())

  it('exchanges the token through the API and stays on the React origin', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
      if (String(input) === '/api/v1/auth/password/reset/bridge/uid-token/') return jsonResponse({ valid: true, uid: 'i' })
      if (String(input) === '/api/v1/auth/password/reset/i/') return jsonResponse({ valid: true, password_hints: [] })
      throw new Error(String(input))
    })
    renderAt('/app/password/reset/bridge/uid-token')
    expect(await screen.findByRole('heading', { name: 'Nouveau mot de passe' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/password/reset/i/')
    const bridgeCall = fetchMock.mock.calls.find(([url]) => url === '/api/v1/auth/password/reset/bridge/uid-token/')
    expect(bridgeCall?.[1]?.credentials).toBe('include')
    expect(fetchMock.mock.calls.every(([url]) => !String(url).includes('/app/password/reset/'))).toBe(true)
  })

  it('replaces an invalid emailed link with the React invalid-link page', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
      if (String(input) === '/api/v1/auth/password/reset/bridge/invalid-token/') return jsonResponse({ valid: false }, 400)
      if (String(input) === '/api/v1/auth/password/reset/invalid/') return jsonResponse({ valid: false }, 400)
      throw new Error(String(input))
    })
    renderAt('/app/password/reset/bridge/invalid-token')
    await waitFor(() => expect(window.location.pathname).toBe('/app/password/reset/invalid/'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Ce lien de réinitialisation n’est plus valide.')
  })

  it('keeps request and confirmation in React without disclosing the address', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
      if (String(input) === '/api/v1/auth/password/reset/') return jsonResponse({ sent: true })
      throw new Error(String(input))
    })
    renderAt('/app/login')
    await user.click(await screen.findByRole('link', { name: 'Mot de passe oublié ?' }))
    expect(await screen.findByRole('heading', { name: 'Réinitialiser le mot de passe' })).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Adresse email' }), 'ada@example.test')
    await user.click(screen.getByRole('button', { name: 'Envoyer le lien' }))
    expect(await screen.findByText(/Si cette adresse correspond à un compte/)).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/v1/auth/password/reset/')).toBe(true)
    expect(window.location.pathname).toBe('/app/password/reset')
  })

  it('shows server hints and validation, then returns to Login', async () => {
    const user = userEvent.setup()
    let attempts = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
      if (String(input) === '/api/v1/auth/password/reset/abc/' && init?.method === 'GET') return jsonResponse({ valid: true, password_hints: ['Au moins 10 caractères.'] })
      if (String(input) === '/api/v1/auth/password/reset/abc/' && init?.method === 'POST') {
        attempts++
        return attempts === 1 ? jsonResponse({ password1: ['Mot de passe trop court.'] }, 400) : jsonResponse({ saved: true })
      }
      throw new Error(String(input))
    })
    renderAt('/app/password/reset/abc')
    expect(await screen.findByRole('heading', { name: 'Nouveau mot de passe' })).toBeInTheDocument()
    await user.click(screen.getByText('Exigences du mot de passe'))
    expect(screen.getByText('Au moins 10 caractères.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Nouveau mot de passe', { selector: 'input' }), 'short')
    await user.type(screen.getByLabelText('Confirmer le mot de passe', { selector: 'input' }), 'short')
    await user.click(screen.getByRole('button', { name: 'Définir le mot de passe' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Mot de passe trop court.')
    await user.click(screen.getByRole('button', { name: 'Définir le mot de passe' }))
    expect(await screen.findByText('Votre mot de passe a été modifié.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Se connecter' })).toHaveAttribute('href', '/app/login')
  })

  it('offers a new request for an invalid link', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
      if (String(input) === '/api/v1/auth/password/reset/invalid/') return jsonResponse({ valid: false }, 400)
      throw new Error(String(input))
    })
    renderAt('/app/password/reset/invalid')
    expect(await screen.findByRole('alert')).toHaveTextContent('Ce lien de réinitialisation n’est plus valide.')
    expect(screen.getByRole('link', { name: 'Demander un nouveau lien' })).toHaveAttribute('href', '/app/password/reset')
  })
})
