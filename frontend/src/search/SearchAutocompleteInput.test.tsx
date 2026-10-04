import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useRef, useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { SearchAutocompleteInput } from './SearchAutocompleteInput'

const { getAutocomplete } = vi.hoisted(() => ({ getAutocomplete: vi.fn() }))
vi.mock('../api/globalSearch', () => ({ getSearchAutocomplete: getAutocomplete }))

function TestInput({ initial = '' }: { initial?: string }) {
  const [value, setValue] = useState(initial)
  const ref = useRef<HTMLInputElement>(null)
  return <I18nProvider><SearchAutocompleteInput inputRef={ref} value={value} onChange={setValue} /></I18nProvider>
}

beforeEach(() => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  getAutocomplete.mockReset()
  getAutocomplete.mockResolvedValue({ context: 'key', replace_start: 0, replace_end: 0, suggestions: [], incomplete: false })
})

describe('Search autocomplete input', () => {
  it('inserts a key with arrows and Enter and keeps focus', async () => {
    getAutocomplete.mockResolvedValue({ context: 'key', replace_start: 0, replace_end: 3,
      suggestions: [{ kind: 'provider', label: 'project', insert_text: 'project:', detail: 'Projects' }], incomplete: false })
    const user = userEvent.setup()
    render(<TestInput />)
    const input = screen.getByRole('combobox', { name: 'Rechercher' })
    await user.type(input, 'pro')
    expect(await screen.findByRole('option', { name: /project/ })).toBeInTheDocument()
    await user.keyboard('{ArrowDown}{Enter}')
    expect(input).toHaveValue('project:')
    expect(input).toHaveFocus()
    await waitFor(() => expect((input as HTMLInputElement).selectionStart).toBe(8))
  })

  it('replaces the token at the caret without changing the rest of the query', async () => {
    getAutocomplete.mockResolvedValue({ context: 'key', replace_start: 16, replace_end: 20,
      suggestions: [{ kind: 'field', label: 'leader', insert_text: 'leader:', detail: 'Leader' }], incomplete: false })
    render(<TestInput initial="project:Foo AND lea:Dupont" />)
    const input = screen.getByRole('combobox', { name: 'Rechercher' }) as HTMLInputElement
    input.focus()
    input.setSelectionRange(19, 19)
    fireEvent.select(input)
    expect(await screen.findByRole('option', { name: /leader/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('option', { name: /leader/ }))
    expect(input).toHaveValue('project:Foo AND leader:Dupont')
    expect(input).toHaveFocus()
    await waitFor(() => expect(input.selectionStart).toBe(23))
  })

  it('supports GenericInfo insertion, Tab acceptance and Escape dismissal', async () => {
    getAutocomplete.mockImplementation(async (query: string) => ({ context: 'generic_info_type', replace_start: 5, replace_end: query.length,
      suggestions: [{ kind: 'generic_info_type', label: 'Matricule CHU', insert_text: '"Matricule CHU"=', detail: '' }], incomplete: true }))
    const user = userEvent.setup()
    render(<TestInput initial="info:mat" />)
    const input = screen.getByRole('combobox', { name: 'Rechercher' })
    await user.click(input)
    expect(await screen.findByRole('option', { name: /Matricule CHU/ })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    await user.type(input, 'r')
    expect(await screen.findByRole('option', { name: /Matricule CHU/ })).toBeInTheDocument()
    await user.keyboard('{Tab}')
    expect(input).toHaveValue('info:"Matricule CHU"=')
  })

  it('ignores a superseded suggestion response', async () => {
    const pending = new Map<string, (value: unknown) => void>()
    getAutocomplete.mockImplementation((query: string) => new Promise((resolve) => pending.set(query, resolve)))
    const user = userEvent.setup()
    render(<TestInput />)
    const input = screen.getByRole('combobox', { name: 'Rechercher' })
    await user.type(input, 'pr')
    await waitFor(() => expect(pending.has('pr')).toBe(true))
    await user.type(input, 'o')
    await waitFor(() => expect(pending.has('pro')).toBe(true))
    pending.get('pro')?.({ context: 'key', replace_start: 0, replace_end: 3,
      suggestions: [{ kind: 'provider', label: 'project', insert_text: 'project:', detail: 'Projects' }], incomplete: false })
    expect(await screen.findByRole('option', { name: /project/ })).toBeInTheDocument()
    pending.get('pr')?.({ context: 'key', replace_start: 0, replace_end: 2,
      suggestions: [{ kind: 'provider', label: 'stale', insert_text: 'stale:', detail: '' }], incomplete: false })
    expect(screen.queryByRole('option', { name: /stale/ })).not.toBeInTheDocument()
  })
})
