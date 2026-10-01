import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { ObjectPreferenceActions } from './ObjectPreferenceActions'

describe('ObjectPreferenceActions', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }) })
  afterEach(() => vi.restoreAllMocks())

  it.each(['project', 'employee', 'team'] as const)('loads and updates both preferences for %s', async (type) => {
    let state = { favorite: false, subscription: false }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'PUT') state = { ...state, ...JSON.parse(String(init.body)) }
      return jsonResponse(state)
    })
    render(<I18nProvider><ObjectPreferenceActions type={type} objectId={42} /></I18nProvider>)
    expect(await screen.findByRole('button', { name: 'Ajouter aux favoris' })).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter aux favoris' }))
    expect(await screen.findByRole('button', { name: 'Retirer des favoris' })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'S’abonner' }))
    expect(await screen.findByRole('button', { name: 'Se désabonner' })).toHaveAttribute('aria-pressed', 'true')
    expect(fetch.mock.calls.some(([url, init]) => String(url) === `/api/v1/preferences/${type}/42/` && init?.method === 'PUT')).toBe(true)
  })

  it('disables actions while loading and restores state on failure', async () => {
    let fail = false
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'PUT' && fail) return jsonResponse({ detail: 'Failed' }, 500)
      return jsonResponse({ favorite: false, subscription: false })
    })
    render(<I18nProvider><ObjectPreferenceActions type="team" objectId={7} /></I18nProvider>)
    expect(screen.getByRole('button', { name: 'Ajouter aux favoris' })).toBeDisabled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ajouter aux favoris' })).toBeEnabled())
    fail = true
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter aux favoris' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible d’enregistrer')
    expect(screen.getByRole('button', { name: 'Ajouter aux favoris' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('uses English accessible labels when the browser language is English', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ favorite: false, subscription: true }))
    render(<I18nProvider><ObjectPreferenceActions type="employee" objectId={1} /></I18nProvider>)
    expect(await screen.findByRole('button', { name: 'Add to favorites' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Unsubscribe' })).toHaveAttribute('aria-pressed', 'true')
  })
})
