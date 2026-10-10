import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { UserSettingsSection } from './SettingsHubPage'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ status: 'unauthenticated' }) }))

const sendUrl = '/api/v1/settings/notifications/test-email/send/'
const previewUrl = '/api/v1/settings/notifications/test-email/preview/'
const mount = () => render(<I18nProvider><UserSettingsSection section="notifications" /></I18nProvider>)

describe('Settings notification tests', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
  })
  afterEach(() => vi.restoreAllMocks())

  it('sends for the current session, blocks double clicks, and reports success', async () => {
    let complete!: (value: Response) => void
    const pending = new Promise<Response>((resolve) => { complete = resolve })
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url) === sendUrl ? pending : jsonResponse({ settings: [] }))
    mount()
    const button = await screen.findByRole('button', { name: 'Send test notification' })
    expect(screen.getByRole('button', { name: 'Preview notification' })).toBeInTheDocument()
    await userEvent.click(button)
    expect(button).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Preview notification' })).toBeDisabled()
    expect(fetch.mock.calls.filter(([url]) => String(url) === sendUrl)).toHaveLength(1)
    const call = fetch.mock.calls.find(([url]) => String(url) === sendUrl)?.[1]
    expect(call?.method).toBe('POST')
    expect(call?.credentials).toBe('include')
    expect(call?.body).toBeUndefined()
    complete(jsonResponse({ sent: true }))
    expect(await screen.findByRole('status')).toHaveTextContent('Test notification sent.')
    await waitFor(() => expect(button).toBeEnabled())
  })

  it('opens preview synchronously, writes backend HTML and handles errors', async () => {
    let complete!: (value: Response) => void
    const pending = new Promise<Response>((resolve) => { complete = resolve })
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url) === previewUrl ? pending : jsonResponse({ settings: [] }))
    const popup = {
      document: { open: vi.fn(), write: vi.fn(), close: vi.fn(), title: '', body: { style: { backgroundColor: '' } } },
      close: vi.fn(),
    }
    const open = vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window)
    mount()
    await userEvent.click(await screen.findByRole('button', { name: 'Preview notification' }))
    expect(open).toHaveBeenCalledOnce()
    expect(fetch.mock.calls.find(([url]) => String(url) === previewUrl)?.[1]?.body).toBeUndefined()
    complete(new Response('<html><body>Mail preview</body></html>', { headers: { 'content-type': 'text/html' } }))
    await waitFor(() => expect(popup.document.write).toHaveBeenCalledWith('<html><body>Mail preview</body></html>'))
    expect(popup.document.title).toBe('LabsManager Test Mail')
    expect(popup.document.body.style.backgroundColor).toBe('white')

    fetch.mockImplementation(async (url) => String(url) === previewUrl ? jsonResponse({ detail: 'Preview failed' }, 500) : jsonResponse({ settings: [] }))
    await userEvent.click(screen.getByRole('button', { name: 'Preview notification' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to generate the notification preview.')
    expect(popup.close).toHaveBeenCalledOnce()
  })

  it('reports a send error and keeps the controls usable', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url) === sendUrl ? jsonResponse({ detail: 'No verified primary email' }, 400) : jsonResponse({ settings: [] }))
    mount()
    const button = await screen.findByRole('button', { name: 'Send test notification' })
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('No verified primary email')
    expect(button).toBeEnabled()
  })
})
