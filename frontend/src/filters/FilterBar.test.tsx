import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, useSearchParams } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { FilterBar } from './FilterBar'
import type { EntitySearchSource, SupportedFilter } from './types'

const catalogue: SupportedFilter[] = [
  { id: 'flag', label: 'État', category: 'Situation', description: 'Ouvert ou fermé', type: 'static-choice', parameter: 'flag', options: [{ value: 'open', label: 'Ouvert' }, { value: 'closed', label: 'Fermé' }] },
  { id: 'owner', label: 'Responsable', category: 'Relations', type: 'entity-search', parameter: 'owner', source: 'people' },
]
function setup(path = '/?search=other&offset=25', overrides: Partial<EntitySearchSource> = {}) {
  const source: EntitySearchSource = {
    search: vi.fn().mockResolvedValue({ options: [{ value: '42', label: 'Camille Test' }, { value: '43', label: 'Alex Test' }], hasMore: true }),
    resolve: vi.fn().mockResolvedValue({ value: '42', label: 'Camille Test' }),
    ...overrides,
  }
  const sources = { people: source }
  function Example() {
    const [query, setQuery] = useSearchParams()
    return <><FilterBar catalogue={catalogue} sources={sources} query={query} onChange={setQuery} resetParameters={['offset']} /><button>Autre commande</button></>
  }
  window.history.replaceState({}, '', path)
  render(<BrowserRouter><Example /></BrowserRouter>)
  return source
}
const openGallery = async () => userEvent.click(screen.getByRole('button', { name: 'Ajouter un filtre' }))
const query = () => new URLSearchParams(window.location.search)

describe('common filter engine', () => {
  it('opens a categorized gallery with search focus, local search and keyboard dismissal', async () => {
    setup()
    await openGallery()
    expect(screen.getByRole('dialog', { name: 'Ajouter un filtre' })).toBeInTheDocument()
    const search = screen.getByRole('searchbox', { name: 'Rechercher un filtre' })
    expect(search).toHaveFocus()
    expect(screen.getByRole('region', { name: 'Situation' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Relations' })).toBeInTheDocument()
    await userEvent.type(search, 'etat')
    expect(screen.getByRole('button', { name: /État/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Responsable' })).not.toBeInTheDocument()
    await userEvent.clear(search)
    await userEvent.type(search, 'absent')
    expect(screen.getByText('Aucun filtre correspondant.')).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter un filtre' })).toHaveFocus()
  })

  it('adds an empty control, closes the gallery and prevents duplicate instances', async () => {
    setup()
    await openGallery()
    await userEvent.click(screen.getByRole('button', { name: /État/ }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByLabelText('État')).toHaveFocus()
    expect(screen.getByLabelText('État')).toHaveValue('')
    expect(query().has('flag')).toBe(true)
    expect(query().get('flag')).toBe('')
    expect(query().has('offset')).toBe(false)
    await openGallery()
    expect(screen.getByRole('button', { name: /État.*Déjà ajouté/ })).toBeDisabled()
    expect(within(screen.getByRole('dialog')).queryByRole('option')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Fermer la galerie' }))
    await userEvent.selectOptions(screen.getByLabelText('État'), 'closed')
    expect(query().get('flag')).toBe('closed')
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer le filtre état' }))
    expect(query().has('flag')).toBe(false)
    expect(query().get('search')).toBe('other')
  })

  it('closes on outside interaction and restores URL controls across browser history', async () => {
    setup('/?flag=open')
    expect(screen.getByLabelText('État')).toHaveValue('open')
    await openGallery()
    await userEvent.click(screen.getByRole('button', { name: 'Autre commande' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('État'), 'closed')
    act(() => window.history.back())
    await waitFor(() => expect(screen.getByLabelText('État')).toHaveValue('open'))
    act(() => window.history.forward())
    await waitFor(() => expect(screen.getByLabelText('État')).toHaveValue('closed'))
    await userEvent.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }))
    expect(screen.queryByLabelText('État')).not.toBeInTheDocument()
  })

  it('resolves an URL ID, searches with debounce, chooses with keyboard and resets', async () => {
    const source = setup('/?owner=42&flag=open&search=other')
    expect(await screen.findByDisplayValue('Camille Test')).toBeInTheDocument()
    expect(source.resolve).toHaveBeenCalledWith('42', expect.any(AbortSignal))
    const input = screen.getByRole('combobox', { name: 'Responsable' })
    input.focus()
    fireEvent.change(input, { target: { value: 'Alex' } })
    expect(source.search).not.toHaveBeenCalled()
    expect(screen.getByText('Valeur appliquée : Camille Test')).toBeInTheDocument()
    expect(await screen.findByRole('option', { name: 'Alex Test' })).toBeInTheDocument()
    expect(source.search).toHaveBeenCalledTimes(1)
    expect(source.search).toHaveBeenCalledWith('Alex', expect.any(AbortSignal))
    expect(screen.getByText('Affinez la recherche pour voir d’autres résultats.')).toBeInTheDocument()
    await userEvent.keyboard('{ArrowDown}{ArrowDown}{Enter}')
    expect(query().get('owner')).toBe('43')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Responsable' })).toHaveFocus()
    await userEvent.click(screen.getByRole('button', { name: 'Réinitialiser les filtres' }))
    expect(window.location.search).toBe('?search=other')
  })

  it('handles unresolved IDs without silently dropping the applied filter', async () => {
    setup('/?owner=99', { resolve: vi.fn().mockResolvedValue(null) })
    expect(await screen.findByText(/Valeur indisponible \(ID 99\)/)).toBeInTheDocument()
    expect(query().get('owner')).toBe('99')
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer le filtre responsable' }))
    expect(query().has('owner')).toBe(false)
  })

  it('handles search failures, retries and empty results locally', async () => {
    const search = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ options: [], hasMore: false })
    setup('/?owner=', { search })
    await userEvent.type(screen.getByRole('combobox', { name: 'Responsable' }), 'Nobody')
    expect(await screen.findByRole('alert')).toHaveTextContent('Recherche indisponible')
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer la recherche' }))
    expect(await screen.findByText('Aucun résultat.')).toBeInTheDocument()
    expect(query().get('owner')).toBe('')
  })

  it('ignores an old response after the search text changes', async () => {
    let complete!: (value: { options: { value: string; label: string }[]; hasMore: boolean }) => void
    const search = vi.fn().mockImplementationOnce(() => new Promise((resolve) => { complete = resolve })).mockResolvedValue({ options: [{ value: '2', label: 'Recent' }], hasMore: false })
    setup('/?owner=', { search })
    const input = screen.getByRole('combobox', { name: 'Responsable' })
    await userEvent.type(input, 'Old')
    await waitFor(() => expect(search).toHaveBeenCalledTimes(1))
    fireEvent.change(input, { target: { value: 'New' } })
    expect(await screen.findByRole('option', { name: 'Recent' })).toBeInTheDocument()
    await act(async () => complete({ options: [{ value: '1', label: 'Obsolete' }], hasMore: false }))
    expect(screen.queryByRole('option', { name: 'Obsolete' })).not.toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    expect(input).toHaveAttribute('aria-expanded', 'false')
  })
})
