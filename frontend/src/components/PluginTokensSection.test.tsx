import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { PluginTokensSection } from './PluginTokensSection'

const stamp = '2026-10-01T10:00:00Z'
const token = (id: string, name: string) => ({ public_id: id, name, kind: 'plugin', scopes: [], created_at: stamp, expires_at: null, revoked_at: null, last_used_at: null })
const mount = (kind: 'plugin' | 'user' = 'plugin') => render(<I18nProvider><PluginTokensSection pluginKey="demo" kind={kind} /></I18nProvider>)

describe('Shared plugin token management', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] }) })
  afterEach(() => vi.restoreAllMocks())

  it('creates multiple technical tokens, reveals each secret once and supports manual HTTP copy fallback', async () => {
    const rows = [token('existing', 'Existing')]
    let created = 0
    const copied = vi.fn(() => true)
    Object.defineProperty(document, 'execCommand', { configurable: true, value: copied })
    Object.defineProperty(window.navigator, 'clipboard', { configurable: true, value: undefined })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/plugins/demo/tokens/plugin/' && init?.method === 'GET') return jsonResponse({ scopes: [], tokens: rows })
      if (url === '/api/v1/plugins/demo/tokens/plugin/' && init?.method === 'POST') {
        const payload = JSON.parse(String(init.body)) as { name: string; scopes: string[]; expires_at: string | null }
        expect(payload.scopes).toEqual([])
        expect(payload.expires_at).toBeNull()
        created += 1
        const row = token(`new-${created}`, payload.name)
        rows.unshift(row)
        return jsonResponse({ ...row, token: `new-${created}.private-${created}` }, 201)
      }
      throw Error(url)
    })
    mount()
    expect(await screen.findByText('Existing')).toBeInTheDocument()
    for (const count of [1, 2]) {
      await userEvent.click(screen.getByRole('button', { name: 'Create token' }))
      expect(screen.queryByRole('group', { name: 'Permissions' })).not.toBeInTheDocument()
      await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), `Service ${count}`)
      await userEvent.click(screen.getByRole('button', { name: 'Save' }))
      const field = await screen.findByRole('textbox', { name: 'New token' })
      expect(field).toHaveValue(`new-${count}.private-${count}`)
      await userEvent.click(screen.getByRole('button', { name: 'Copy token' }))
      expect(copied).toHaveBeenCalledWith('copy')
      expect(screen.getByText('Token copied.')).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: 'Close' }))
      expect(screen.queryByDisplayValue(`new-${count}.private-${count}`)).not.toBeInTheDocument()
    }
    expect(screen.getByText('Service 1')).toBeInTheDocument()
    expect(screen.getByText('Service 2')).toBeInTheDocument()
  })

  it('shows only declared scopes and supports rename, confirmed revoke and backend errors', async () => {
    const rows = [token('first', 'Service')]
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/plugins/demo/tokens/user/' && init?.method === 'GET') return jsonResponse({ scopes: [{ name: 'read', label: 'Read', description: 'Read records' }], tokens: rows })
      if (url === '/api/v1/plugins/demo/tokens/user/' && init?.method === 'POST') return jsonResponse({ detail: 'Scope refused' }, 400)
      if (url === '/api/v1/plugins/demo/tokens/user/first/' && init?.method === 'PATCH') return jsonResponse({ ...rows[0], name: 'Renamed' })
      if (url === '/api/v1/plugins/demo/tokens/user/first/' && init?.method === 'DELETE') return jsonResponse({ ...rows[0], name: 'Renamed', revoked_at: stamp })
      throw Error(url)
    })
    mount('user')
    expect(await screen.findByText('Service')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Create token' }))
    expect(screen.getByRole('group', { name: 'Permissions' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /Read/ })).toBeInTheDocument()
    await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), 'Failed')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Scope refused')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await userEvent.click(screen.getByRole('button', { name: 'Rename' }))
    const nameField = screen.getByRole('textbox', { name: 'Name' })
    await userEvent.clear(nameField)
    await userEvent.type(nameField, 'Renamed')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Renamed')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Revoke' }))
    const dialog = screen.getByRole('alertdialog')
    expect(within(dialog).getByText(/Revoke token/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Revoke' }))
    expect(await screen.findByText('Revoked')).toBeInTheDocument()
  })

  it('sends selected scopes and a future local expiration as UTC', async () => {
    const future = new Date(Date.now() + 86_400_000)
    future.setSeconds(0, 0)
    const localValue = `${future.getFullYear()}-${String(future.getMonth() + 1).padStart(2, '0')}-${String(future.getDate()).padStart(2, '0')}T${String(future.getHours()).padStart(2, '0')}:${String(future.getMinutes()).padStart(2, '0')}`
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/plugins/demo/tokens/user/' && init?.method === 'GET') return jsonResponse({ scopes: [{ name: 'read', label: 'Read' }], tokens: [] })
      if (url === '/api/v1/plugins/demo/tokens/user/' && init?.method === 'POST') {
        const payload = JSON.parse(String(init.body)) as { scopes: string[]; expires_at: string }
        expect(payload.scopes).toEqual(['read'])
        expect(payload.expires_at).toBe(future.toISOString())
        return jsonResponse({ ...token('future', 'Service'), token: 'future.private' }, 201)
      }
      throw Error(url)
    })
    mount('user')
    await screen.findByText('No tokens.')
    await userEvent.click(screen.getByRole('button', { name: 'Create token' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), 'Service')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Read' }))
    fireEvent.change(screen.getByLabelText('Expiration (optional)'), { target: { value: localValue } })
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('textbox', { name: 'New token' })).toHaveValue('future.private')
  })
})
