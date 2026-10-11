import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser, jsonResponse } from '../test/fixtures'
import { EmailConfirmationBridgePage, EmailConfirmationPage } from './EmailConfirmationPage'

function renderAt(path: string) {
  window.history.replaceState({}, '', path)
  render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><Routes>
    <Route path="email/confirm/bridge/:key" element={<EmailConfirmationBridgePage />} />
    <Route path="email/confirm" element={<EmailConfirmationPage />} />
  </Routes></AuthProvider></BrowserRouter></I18nProvider>)
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] }))
afterEach(() => vi.restoreAllMocks())

it('exchanges the key, removes it from the URL, and confirms only after a click', async () => {
  let verified = false
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    if (url.endsWith('/bridge/')) return jsonResponse({ state: 'confirmation_required' })
    if (url.endsWith('/confirm/') && init?.method === 'POST') { verified = true; return jsonResponse({ state: 'confirmed' }) }
    if (url.endsWith('/confirm/')) return jsonResponse({ state: verified ? 'confirmed' : 'confirmation_required', email: 'ada@example.test' })
    throw new Error(url)
  })
  renderAt('/app/email/confirm/bridge/secret-key/')
  expect(await screen.findByRole('button', { name: 'Confirm email address' })).toBeInTheDocument()
  expect(window.location.pathname).toBe('/app/email/confirm/')
  expect(window.location.href).not.toContain('secret-key')
  expect(verified).toBe(false)
  expect(screen.getByText(/ada@example.test/)).toBeInTheDocument()
  expect(JSON.parse(String(fetchMock.mock.calls.find(([url]) => String(url).endsWith('/bridge/'))?.[1]?.body))).toEqual({ key: 'secret-key' })
  await userEvent.click(screen.getByRole('button', { name: 'Confirm email address' }))
  expect(await screen.findByText('Your email address is confirmed.')).toBeInTheDocument()
  expect(verified).toBe(true)
})

it('shows invalid and already-confirmed outcomes without a confirmation button', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    return jsonResponse({ state: 'already_confirmed' })
  })
  renderAt('/app/email/confirm/')
  expect(await screen.findByText('This email address is already confirmed.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Confirm email address' })).not.toBeInTheDocument()
})

it('replaces an invalid bridge URL and shows the error without exposing the key', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    if (String(input).endsWith('/bridge/')) return jsonResponse({ state: 'invalid' }, 400)
    throw new Error(String(input))
  })
  renderAt('/app/email/confirm/bridge/bad-key/')
  expect(await screen.findByText('This confirmation link is invalid or has expired.')).toBeInTheDocument()
  expect(window.location.pathname).toBe('/app/email/confirm/')
  expect(window.location.href).not.toContain('bad-key')
  expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/app/login')
})

it('shows an API failure separately from an invalid key', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input) === '/api/v1/me/') return jsonResponse({ is_authenticated: false })
    throw new Error('Network unavailable')
  })
  renderAt('/app/email/confirm/')
  expect(await screen.findByText('Could not confirm this address right now. Try again later.')).toBeInTheDocument()
})

it('keeps an authenticated user in the app after confirmation', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    if (String(input) === '/api/v1/me/') return jsonResponse({ ...authenticatedUser, is_authenticated: true })
    if (String(input).endsWith('/confirm/') && init?.method === 'POST') return jsonResponse({ state: 'confirmed' })
    if (String(input).endsWith('/confirm/')) return jsonResponse({ state: 'confirmation_required' })
    throw new Error(String(input))
  })
  renderAt('/app/email/confirm/')
  await userEvent.click(await screen.findByRole('button', { name: 'Confirm email address' }))
  expect(await screen.findByText('Your email address is confirmed.')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Go to LabsManager' })).toHaveAttribute('href', '/app')
  await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/confirm/') && init?.method === 'POST')).toBe(true))
})
