import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { UserPluginDetailPage, UserPluginsPage } from './UserPluginsPage'

const plugins = [
  { key: 'demo', human_name: 'Demo plugin', description: 'Personal features', user_settings: true, user_tokens: true },
  { key: 'token-only', human_name: 'Token only', description: '', user_settings: false, user_tokens: true },
]
const setting = { key: 'COLOUR', name: 'Colour', description: 'Display colour', type: 'choice', value: 'blue', default: 'blue', choices: [{ value: 'blue', label: 'Blue' }, { value: 'red', label: 'Red' }], can_change: true }

function mount(path: string) {
  render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/settings/my-plugins" element={<UserPluginsPage />} />
    <Route path="/settings/my-plugins/:pluginKey" element={<UserPluginDetailPage />} />
  </Routes></MemoryRouter></I18nProvider>)
}

describe('Personal plugin settings pages', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] }) })
  afterEach(() => vi.restoreAllMocks())

  it('does not show origin badges in personal settings', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/plugins/mine/') return jsonResponse({ results: [
        { ...plugins[0], key: 'sample', human_name: 'Sample plugin' },
        { ...plugins[0], key: 'builtin', human_name: 'Built-in plugin' },
        { ...plugins[0], key: 'external', human_name: 'External plugin' },
      ] })
      throw Error(String(input))
    })
    mount('/settings/my-plugins')
    const sample = await screen.findByRole('link', { name: 'Sample plugin' })
    const builtin = screen.getByRole('link', { name: 'Built-in plugin' })
    const external = screen.getByRole('link', { name: 'External plugin' })
    for (const link of [sample, builtin, external]) expect(within(link.parentElement!).queryByText(/^(Sample|Built-in)$/)).not.toBeInTheDocument()
  })

  it('lists only the personal plugins supplied by active capability discovery and opens a dedicated page', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/plugins/mine/') return jsonResponse({ results: plugins })
      if (url === '/api/v1/plugins/demo/user-settings/') return jsonResponse({ settings: [setting] })
      if (url === '/api/v1/plugins/demo/tokens/user/') return jsonResponse({ scopes: [], tokens: [] })
      throw Error(url)
    })
    mount('/settings/my-plugins')
    expect(await screen.findByRole('link', { name: 'Demo plugin' })).toHaveAttribute('href', '/settings/my-plugins/demo')
    expect(screen.queryByText('Technical only')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Demo plugin' }))
    expect(await screen.findByRole('heading', { name: 'My preferences' })).toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'My tokens' })).toBeInTheDocument()
    expect(screen.getByLabelText('Colour')).toHaveValue('blue')
  })

  it('updates a personal preference and restores its default through the existing setting row', async () => {
    const calls: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url === '/api/v1/plugins/mine/') return jsonResponse({ results: plugins })
      if (url === '/api/v1/plugins/demo/user-settings/') return jsonResponse({ settings: [setting] })
      if (url === '/api/v1/plugins/demo/tokens/user/') return jsonResponse({ scopes: [], tokens: [] })
      if (url === '/api/v1/plugins/demo/user-settings/COLOUR/' && init?.method === 'PATCH') return jsonResponse({ ...setting, value: 'red' })
      if (url === '/api/v1/plugins/demo/user-settings/COLOUR/' && init?.method === 'DELETE') return jsonResponse(setting)
      throw Error(url)
    })
    mount('/settings/my-plugins/demo')
    const select = await screen.findByLabelText('Colour')
    await userEvent.selectOptions(select, 'red')
    expect(await screen.findByRole('button', { name: 'Reset' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(await screen.findByLabelText('Colour')).toHaveValue('blue')
    expect(calls).toContain('PATCH /api/v1/plugins/demo/user-settings/COLOUR/')
    expect(calls).toContain('DELETE /api/v1/plugins/demo/user-settings/COLOUR/')
  })

  it('shows only tokens for a token-only plugin and hides a plugin removed from discovery', async () => {
    let active = true
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/plugins/mine/') return jsonResponse({ results: active ? plugins : [] })
      if (url === '/api/v1/plugins/token-only/tokens/user/') return jsonResponse({ scopes: [], tokens: [] })
      throw Error(url)
    })
    const view = render(<I18nProvider><MemoryRouter initialEntries={['/settings/my-plugins/token-only']}><Routes><Route path="/settings/my-plugins/:pluginKey" element={<UserPluginDetailPage />} /></Routes></MemoryRouter></I18nProvider>)
    expect(await screen.findByRole('region', { name: 'My tokens' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'My preferences' })).not.toBeInTheDocument()
    view.unmount()
    active = false
    mount('/settings/my-plugins/token-only')
    expect(await screen.findByText('This plugin is no longer available.')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'My tokens' })).not.toBeInTheDocument()
    expect(within(screen.getByRole('alert')).getByText('This plugin is no longer available.')).toBeInTheDocument()
  })

  it('opens the generic page for an action-only plugin', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/plugins/mine/') return jsonResponse({ results: [{ key: 'actions', human_name: 'Actions plugin', description: '', user_settings: false, user_tokens: false, ui_actions: true }] })
      if (url === '/api/v1/ui-contributions/user-plugin/actions/') return jsonResponse({ contributions: [{ id: 'plugin:actions:one', plugin_slug: 'actions', slot: 'user.plugin.settings.actions', type: 'action', label: 'Copy link', behavior: 'copy_url', icon: null, confirm: false, priority: 0 }] })
      throw Error(url)
    })
    mount('/settings/my-plugins/actions')
    expect(await screen.findByRole('heading', { name: 'Actions plugin' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Plugin actions' })).toBeInTheDocument()
    screen.getByRole('button', { name: 'Plugin actions' }).focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('menuitem', { name: 'Copy link' })).toBeInTheDocument()
  })
})
