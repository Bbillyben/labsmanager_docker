import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { favoritesChangedEvent } from '../api/preferences'
import { FavoritesMenu } from './FavoritesMenu'

function mount() { return render(<I18nProvider><MemoryRouter><FavoritesMenu /></MemoryRouter></I18nProvider>) }

describe('FavoritesMenu', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }) })
  afterEach(() => vi.restoreAllMocks())

  it('opens grouped links and keeps Institutions on the Django route', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse([
      { type: 'project', group: 'projects', id: 1, label: 'Alpha', url: '/projects/1', legacy: false },
      { type: 'employee', group: 'employees', id: 2, label: 'Ada Reader', url: '/employees/2', legacy: false },
      { type: 'team', group: 'teams', id: 3, label: 'Readers', url: '/teams/3', legacy: false },
      { type: 'institution', group: 'institutions', id: 4, label: 'UNI', url: '/infos/project/institution/4', legacy: true },
    ]))
    mount()
    await userEvent.click(screen.getByRole('button', { name: 'Favoris' }))
    expect(screen.getByRole('button', { name: 'Favoris' })).toHaveAttribute('aria-expanded', 'true')
    expect(await screen.findByRole('link', { name: 'Alpha' })).toHaveAttribute('href', '/projects/1')
    expect(screen.getByRole('link', { name: 'Ada Reader' })).toHaveAttribute('href', '/employees/2')
    expect(screen.getByRole('link', { name: 'Readers' })).toHaveAttribute('href', '/teams/3')
    expect(screen.getByRole('link', { name: 'UNI' }).getAttribute('href')).toContain('/infos/project/institution/4')
    expect(screen.getByText('Institutions')).toBeInTheDocument()
  })

  it('shows an empty state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse([]))
    mount()
    await userEvent.click(screen.getByRole('button', { name: 'Favoris' }))
    expect(await screen.findByText('Aucun favori')).toBeInTheDocument()
  })

  it('requests sidebar expansion before showing the list', async () => {
    const onRequestExpand = vi.fn()
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse([]))
    const view = render(<I18nProvider><MemoryRouter><FavoritesMenu expanded={false} onRequestExpand={onRequestExpand} /></MemoryRouter></I18nProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Favoris' }))
    expect(onRequestExpand).toHaveBeenCalledOnce()
    view.rerender(<I18nProvider><MemoryRouter><FavoritesMenu expanded onRequestExpand={onRequestExpand} /></MemoryRouter></I18nProvider>)
    expect(await screen.findByText('Aucun favori')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledOnce()
  })

  it('refreshes an open menu after a favorite mutation', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse([{ type: 'project', group: 'projects', id: 1, label: 'Alpha', url: '/projects/1', legacy: false }]))
    mount()
    await userEvent.click(screen.getByRole('button', { name: 'Favoris' }))
    expect(await screen.findByText('Aucun favori')).toBeInTheDocument()
    act(() => window.dispatchEvent(new Event(favoritesChangedEvent)))
    expect(await screen.findByRole('link', { name: 'Alpha' })).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
