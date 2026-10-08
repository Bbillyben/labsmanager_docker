import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import type { SearchResult } from '../api/globalSearch'
import { ApiError } from '../api/errors'
import { GlobalSearch } from './GlobalSearch'
import { SearchPage } from './SearchPage'

const { getSchema, searchApi, getAutocomplete } = vi.hoisted(() => ({ getSchema: vi.fn(), searchApi: vi.fn(), getAutocomplete: vi.fn() }))
vi.mock('../api/globalSearch', () => ({ getSearchSchema: getSchema, search: searchApi, getSearchAutocomplete: getAutocomplete }))

const provider = { key: 'publication', label: 'Publications', icon: 'UnknownIcon', fields: [], supports_generic_info: false, autocomplete: false }
const result: SearchResult = { provider_key: 'publication', object_id: '7', title: 'Precise paper', subtitle: 'Research', url: '/app/projects/7', score: 100, icon: 'UnknownIcon', match_reason: 'Title: precise', metadata: {} }
const organizationProvider = { key: 'organization', label: 'Organizations', icon: 'Building2', fields: [], supports_generic_info: true, autocomplete: true }
const organizationResult: SearchResult = { provider_key: 'organization', object_id: 'institutions:9', title: 'Northern Research Institute', subtitle: 'Institution', url: '/app/organizations/institutions/9', score: 100, icon: 'Building2', match_reason: 'Name: Northern Research Institute', metadata: { role: 'institution' } }

function renderSearch(path = '/app/') {
  window.history.pushState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><GlobalSearch /><Routes><Route path="/" element={<p>Home</p>} /><Route path="search" element={<SearchPage />} /><Route path="projects/:id" element={<p>Project detail</p>} /><Route path="organizations/institutions/:id" element={<p>Organization detail</p>} /></Routes></BrowserRouter></I18nProvider>)
}

beforeEach(() => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  getSchema.mockResolvedValue({ providers: [provider] })
  searchApi.mockResolvedValue({ query: 'precise', results: [result], groups: { publication: 1 } })
  getAutocomplete.mockResolvedValue({ context: 'key', replace_start: 0, replace_end: 0, suggestions: [], incomplete: false })
})
afterEach(() => { vi.clearAllMocks(); window.history.pushState({}, '', '/app/') })

describe('Global Search UI', () => {
  it('shows one Organization type, opens its existing detail route and clears the topbar query', async () => {
    const user = userEvent.setup()
    getSchema.mockResolvedValue({ providers: [organizationProvider] })
    searchApi.mockResolvedValue({ query: 'Northern', results: [organizationResult], groups: { organization: 1 }, counts: { organization: 1 } })
    renderSearch()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    await user.type(screen.getByRole('combobox', { name: 'Rechercher' }), 'Northern')
    expect(await screen.findByRole('group', { name: 'Organizations' })).toBeInTheDocument()
    expect(screen.getAllByRole('option', { name: /Northern Research Institute/ })).toHaveLength(1)
    expect(screen.getByText('Institution / gestionnaire')).toBeInTheDocument()
    await user.click(screen.getByRole('option', { name: /Northern Research Institute/ }))
    expect(screen.getByText('Organization detail')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rechercher (/)' })).toHaveAttribute('aria-expanded', 'false')
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    expect(screen.getByRole('combobox', { name: 'Rechercher' })).toHaveValue('')
  })

  it('clears only the topbar query after opening the full results page', async () => {
    const user = userEvent.setup()
    renderSearch()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    await user.type(screen.getByRole('combobox', { name: 'Rechercher' }), 'precise')
    await user.click(await screen.findByRole('option', { name: 'Voir tous les résultats' }))
    expect(window.location.pathname).toBe('/app/search')
    expect(new URLSearchParams(window.location.search).get('q')).toBe('precise')
    expect(screen.getByRole('button', { name: 'Rechercher (/)' })).toHaveAttribute('aria-expanded', 'false')
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    const inputs = screen.getAllByRole('combobox', { name: 'Rechercher' })
    expect(inputs[0]).toHaveValue('')
    expect(inputs[1]).toHaveValue('precise')
  })

  it('uses the same Organization result group and role-specific routes on the full results page', async () => {
    getSchema.mockResolvedValue({ providers: [organizationProvider] })
    searchApi.mockResolvedValue({ query: 'Northern', results: [organizationResult, {
      ...organizationResult, object_id: 'funders:12', url: '/app/organizations/funders/12',
      subtitle: 'Funder', metadata: { role: 'funder' },
    }], groups: { organization: 2 }, counts: { organization: 2 } })
    renderSearch('/app/search?q=Northern')
    expect(await screen.findByRole('region', { name: 'Organizations' })).toBeInTheDocument()
    const links = screen.getAllByRole('link', { name: /Northern Research Institute/ })
    expect(links).toHaveLength(2)
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      '/app/organizations/institutions/9', '/app/organizations/funders/12',
    ])
    expect(screen.getByText('Institution / gestionnaire')).toBeInTheDocument()
    expect(screen.getByText('Financeur')).toBeInTheDocument()
  })

  it('opens discreetly, focuses, searches after debounce, groups a plugin provider and follows result.url', async () => {
    const user = userEvent.setup()
    renderSearch()
    expect(screen.getByRole('button', { name: 'Rechercher (/)' })).toHaveAttribute('aria-expanded', 'false')
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    const input = screen.getByPlaceholderText('Rechercher dans LabsManager…')
    expect(input).toHaveFocus()
    await user.type(input, 'precise')
    expect(searchApi).not.toHaveBeenCalled()
    expect(await screen.findByRole('group', { name: 'Publications' })).toBeInTheDocument()
    expect(screen.getByText('Title: precise')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Precise paper/ })).toHaveAttribute('href', '/app/projects/7')
    await user.click(screen.getByRole('option', { name: /Precise paper/ }))
    expect(screen.getByText('Project detail')).toBeInTheDocument()
  })

  it('handles arrows, Enter, Escape and the slash shortcut outside inputs', async () => {
    const user = userEvent.setup()
    renderSearch()
    fireEvent.keyDown(window, { key: '/' })
    const input = await screen.findByPlaceholderText('Rechercher dans LabsManager…')
    await waitFor(() => expect(input).toHaveFocus())
    await user.type(input, 'precise')
    await screen.findByRole('option', { name: /Precise paper/ })
    await user.keyboard('{ArrowDown}')
    expect(input).toHaveAttribute('aria-activedescendant')
    await user.keyboard('{ArrowUp}')
    await user.keyboard('{Enter}')
    expect(window.location.pathname).toBe('/app/search')
    expect(window.location.search).toBe('?q=precise')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rechercher (/)' })).toHaveAttribute('aria-expanded', 'false')
    const pageInput = screen.getByRole('combobox', { name: 'Rechercher' })
    pageInput.focus()
    fireEvent.keyDown(pageInput, { key: '/' })
    expect(screen.queryByPlaceholderText('Rechercher dans LabsManager…')).toBe(pageInput)
  })

  it('closes preview on first Escape and the field on second Escape', async () => {
    const user = userEvent.setup()
    renderSearch()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    const input = screen.getByPlaceholderText('Rechercher dans LabsManager…')
    await user.type(input, 'precise')
    await screen.findByRole('listbox')
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByPlaceholderText('Rechercher dans LabsManager…')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Rechercher (/)' })).toHaveFocus()
  })

  it('keeps query on outside click, shows empty state, and opens the full page from Enter', async () => {
    const user = userEvent.setup()
    searchApi.mockResolvedValue({ query: 'none', results: [], groups: {} })
    renderSearch()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    const input = screen.getByPlaceholderText('Rechercher dans LabsManager…')
    await user.type(input, 'none')
    expect(await screen.findByText('Aucun résultat')).toBeInTheDocument()
    fireEvent.pointerDown(document.body)
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(input).toHaveValue('none')
    await user.click(input)
    await user.keyboard('{Enter}')
    expect(window.location.pathname).toBe('/app/search')
  })

  it('reads q and provider from the page URL and offers schema-driven tabs', async () => {
    searchApi.mockResolvedValue({ query: 'precise', results: [result], groups: { publication: 1 }, counts: { publication: 5 } })
    renderSearch('/app/search?q=precise&provider=publication')
    expect(await screen.findByRole('heading', { name: 'Résultats pour « precise »' })).toBeInTheDocument()
    await waitFor(() => expect(searchApi).toHaveBeenCalledWith('precise', expect.objectContaining({ provider: 'publication', limit: 25 })))
    expect(await screen.findByRole('link', { name: 'Publications (5)' })).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByRole('link', { name: /Precise paper/ })).toHaveAttribute('href', '/app/projects/7')
  })

  it('ignores a superseded request even when its promise resolves late', async () => {
    const user = userEvent.setup()
    const pending = new Map<string, (value: unknown) => void>()
    searchApi.mockImplementation((query: string) => new Promise((resolve) => pending.set(query, resolve)))
    renderSearch()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    const input = screen.getByPlaceholderText('Rechercher dans LabsManager…')
    await user.type(input, 'pre')
    await waitFor(() => expect(pending.has('pre')).toBe(true))
    await user.type(input, 'ci')
    await waitFor(() => expect(pending.has('preci')).toBe(true))
    pending.get('preci')?.({ query: 'preci', results: [{ ...result, title: 'Current result' }], groups: {} })
    expect(await screen.findByText('Current result')).toBeInTheDocument()
    pending.get('pre')?.({ query: 'pre', results: [{ ...result, title: 'Stale result' }], groups: {} })
    expect(screen.queryByText('Stale result')).not.toBeInTheDocument()
  })

  it('shows a full-page empty state for a shareable query', async () => {
    searchApi.mockResolvedValue({ query: 'nothing', results: [], groups: {} })
    renderSearch('/app/search?q=nothing')
    expect(await screen.findByText('Aucun résultat pour « nothing »')).toBeInTheDocument()
    expect(window.location.search).toBe('?q=nothing')
  })

  it('preserves advanced syntax in the URL, submits on Enter and keeps provider counts', async () => {
    const query = '(project:"Precise IT" OR project:BariBoul) AND NOT leader:Dupont'
    searchApi.mockResolvedValue({ query, results: [result], groups: { publication: 1 }, counts: { publication: 2 } })
    renderSearch(`/app/search?q=${encodeURIComponent(query)}`)
    await waitFor(() => expect(searchApi).toHaveBeenCalledWith(query, expect.any(Object)))
    expect(screen.getByRole('link', { name: 'Publications (2)' })).toBeInTheDocument()
    expect(new URLSearchParams(window.location.search).get('q')).toBe(query)
    const input = screen.getByRole('combobox', { name: 'Rechercher' })
    fireEvent.submit(input.closest('form')!)
    expect(new URLSearchParams(window.location.search).get('q')).toBe(query)
  })

  it('shows structured syntax errors on the page and in the preview', async () => {
    searchApi.mockRejectedValue(new ApiError(400, { error: 'invalid_search_query', message: 'Expected value after colon', position: 8 }))
    renderSearch('/app/search?q=project%3A')
    expect(await screen.findByRole('alert')).toHaveTextContent('Requête invalide : Expected value after colon')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    await user.type(screen.getAllByPlaceholderText('Rechercher dans LabsManager…')[0], 'project:')
    expect((await screen.findAllByRole('alert')).at(-1)).toHaveTextContent('Expected value after colon')
  })

  it('gives completion priority over result navigation and then restores the preview', async () => {
    getAutocomplete.mockImplementation(async (query: string) => query === 'pro'
      ? { context: 'key', replace_start: 0, replace_end: 3, suggestions: [{ kind: 'provider', label: 'publication', insert_text: 'publication:', detail: 'Publications' }], incomplete: false }
      : { context: 'value', replace_start: query.length, replace_end: query.length, suggestions: [], incomplete: false })
    const user = userEvent.setup()
    renderSearch()
    await user.click(screen.getByRole('button', { name: 'Rechercher (/)' }))
    const input = screen.getByRole('combobox', { name: 'Rechercher' })
    await user.type(input, 'pro')
    expect(await screen.findByRole('option', { name: /publication/ })).toBeInTheDocument()
    expect(screen.queryByText('Precise paper')).not.toBeInTheDocument()
    await user.keyboard('{Enter}')
    expect(input).toHaveValue('publication:')
    expect(window.location.pathname).toBe('/app/')
    await user.type(input, 'precise')
    expect(await screen.findByText('Precise paper')).toBeInTheDocument()
  })
})
