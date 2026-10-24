import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { AdminPluginDetailPage } from './AdminSettingsPage'

const detail = { key: 'demo', human_name: 'Demo plugin', description: '', author: '', pub_date: null,
  version: null, website: null, license: null, mixins: ['token'], active: true, is_builtin: false, error: false }

describe('Admin plugin token section', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] }) })
  afterEach(() => vi.restoreAllMocks())

  for (const enabled of [true, false]) {
    it(`${enabled ? 'shows' : 'hides'} technical tokens according to the backend capability`, async () => {
      const calls: string[] = []
      vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
        const url = String(input)
        calls.push(url)
        if (url === '/api/v1/settings/admin/plugins/demo/') return jsonResponse({ ...detail, sections: enabled ? { tokens: true } : {} })
        if (url === '/api/v1/plugins/demo/tokens/plugin/') return jsonResponse({ scopes: [], tokens: [] })
        throw Error(url)
      })
      render(<I18nProvider><MemoryRouter initialEntries={['/settings/admin/plugins/demo']}><Routes><Route path="/settings/admin/plugins/:pluginKey" element={<AdminPluginDetailPage />} /></Routes></MemoryRouter></I18nProvider>)
      expect(await screen.findByRole('heading', { name: 'Demo plugin' })).toBeInTheDocument()
      if (enabled) {
        expect(await screen.findByRole('region', { name: 'Plugin tokens' })).toBeInTheDocument()
        expect(calls).toContain('/api/v1/plugins/demo/tokens/plugin/')
      } else {
        expect(screen.queryByRole('region', { name: 'Plugin tokens' })).not.toBeInTheDocument()
        expect(calls).not.toContain('/api/v1/plugins/demo/tokens/plugin/')
      }
    })
  }
})
