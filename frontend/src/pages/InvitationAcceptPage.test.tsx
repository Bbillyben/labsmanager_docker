import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser, jsonResponse } from '../test/fixtures'
import { InvitationAcceptPage, InvitationBridgePage } from './InvitationAcceptPage'

const invitation = { state: 'valid', email: 'invited@example.test', fields: { username: true, password2: true }, password_hints: [] }

function renderAt(path: string) {
  window.history.replaceState({}, '', path)
  render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><Routes>
    <Route path="invitations/accept/:token" element={<InvitationBridgePage />} />
    <Route path="invitations/accept" element={<InvitationAcceptPage />} />
    <Route path="/" element={<h1>Home</h1>} />
  </Routes></AuthProvider></BrowserRouter></I18nProvider>)
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

it('exchanges the token once, replaces the URL and displays the configured signup form', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    if (url.endsWith('/bridge/')) return jsonResponse(invitation)
    if (url.endsWith('/current/') && init?.method === 'GET') return jsonResponse(invitation)
    throw new Error(url)
  })
  renderAt('/app/invitations/accept/secret-token/')
  expect(await screen.findByRole('heading', { name: 'Accepter l’invitation' })).toBeInTheDocument()
  expect(await screen.findByLabelText('Adresse email')).toHaveValue(invitation.email)
  expect(screen.getByLabelText('Adresse email')).toHaveAttribute('readonly')
  expect(screen.getByLabelText('Identifiant')).toBeInTheDocument()
  expect(screen.getByLabelText('Confirmer le mot de passe')).toBeInTheDocument()
  expect(window.location.pathname).toBe('/app/invitations/accept/')
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/bridge/'))).toHaveLength(1)
  expect(JSON.parse(String(fetchMock.mock.calls.find(([url]) => String(url).endsWith('/bridge/'))?.[1]?.body))).toEqual({ token: 'secret-token' })
})

it.each([
  ['invalid', 'Cette invitation est invalide.'],
  ['expired', 'Cette invitation a expiré.'],
  ['accepted', 'Cette invitation a déjà été utilisée.'],
  ['account_exists', 'Un compte existe déjà pour cette adresse email.'],
] as const)('shows %s without retaining the token', async (state, message) => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    if (String(input).endsWith('/bridge/')) return jsonResponse({ state }, state === 'invalid' ? 400 : 409)
    throw new Error(String(input))
  })
  renderAt('/app/invitations/accept/secret-token/')
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
  expect(window.location.pathname).toBe('/app/invitations/accept/')
  expect(window.location.search).toBe(`?state=${state}`)
})

it('keeps the form after validation errors and prevents duplicate submission', async () => {
  let writes = 0
  let finishWrite: (() => void) | undefined
  const delayedWrite = new Promise<void>((resolve) => { finishWrite = resolve })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    if (url.endsWith('/current/') && init?.method === 'GET') return jsonResponse(invitation)
    if (url.endsWith('/current/') && init?.method === 'POST') {
      writes += 1
      await delayedWrite
      return jsonResponse({ password1: ['Too short.'] }, 400)
    }
    throw new Error(url)
  })
  renderAt('/app/invitations/accept/')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Identifiant'), 'new-user')
  await user.type(screen.getByLabelText('Nouveau mot de passe'), 'Short-123!')
  await user.type(screen.getByLabelText('Confirmer le mot de passe'), 'Short-123!')
  await user.dblClick(screen.getByRole('button', { name: 'Créer mon compte' }))
  expect(writes).toBe(1)
  finishWrite?.()
  expect(await screen.findByRole('alert')).toHaveTextContent('Too short.')
  expect(screen.getByRole('heading', { name: 'Accepter l’invitation' })).toBeInTheDocument()
})

it('refreshes the Django session and enters the app after allauth signup', async () => {
  let signedIn = false
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v1/me/') return jsonResponse(signedIn ? authenticatedUser : { is_authenticated: false })
    if (url.endsWith('/current/') && init?.method === 'GET') return jsonResponse(invitation)
    if (url.endsWith('/current/') && init?.method === 'POST') { signedIn = true; return jsonResponse({ state: 'complete', authenticated: true, redirect_url: '/app/' }) }
    throw new Error(url)
  })
  renderAt('/app/invitations/accept/')
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Identifiant'), 'new-user')
  await user.type(screen.getByLabelText('Nouveau mot de passe'), 'Good-password-123!')
  await user.type(screen.getByLabelText('Confirmer le mot de passe'), 'Good-password-123!')
  await user.click(screen.getByRole('button', { name: 'Créer mon compte' }))
  expect(await screen.findByRole('heading', { name: 'Home' })).toBeInTheDocument()
  expect(window.location.pathname).toBe('/app')
})

it('does not exchange the invitation of an already authenticated user', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input) === '/api/v1/me/') return jsonResponse(authenticatedUser)
    throw new Error(String(input))
  })
  renderAt('/app/invitations/accept/secret-token/')
  expect(await screen.findByText(/Vous êtes déjà connecté/)).toBeInTheDocument()
  await waitFor(() => expect(window.location.pathname).toBe('/app/invitations/accept/'))
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/bridge/'))).toBe(false)
})
