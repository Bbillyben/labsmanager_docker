import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import type { GenericNote } from '../api/notes'
import { GenericNotes } from './GenericNotes'

vi.mock('./ProseEditor', () => ({ ProseEditor: ({ initialHtml, onChange }: { initialHtml: string; onChange: (value: string) => void }) => <div data-testid="wysiwyg"><input aria-label="Editor" defaultValue={initialHtml} onChange={(event) => onChange(event.target.value)} /></div> }))

const capabilities = { can_add: true, can_change: true, can_rename: true, can_delete: true, can_change_visibility: true }
const date = '2026-01-01T12:00:00Z'
const first: GenericNote = { id: 1, name: 'Général', note: '<p>Hello</p>', visibility: 'object', creator: { id: 2, name: 'Alice' }, created_at: date, updated_at: date, capabilities }
const second: GenericNote = { ...first, id: 2, name: 'Privé', note: '<p>Secret</p>', visibility: 'creator' }

function setup(scope: 'project' | 'employee' = 'project', readonly = false, collision = false, adminUrl: string | null = null) {
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr'] })
  const rows = structuredClone([first, second]).map((note) => readonly ? { ...note, admin_url: adminUrl, capabilities: { ...capabilities, can_change: false, can_rename: false, can_delete: false, can_change_visibility: false } } : { ...note, admin_url: adminUrl })
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (method === 'GET') return jsonResponse({ capabilities: { can_add: !readonly }, items: rows })
    if (method === 'POST') {
      if (collision) return jsonResponse({ name: ['already_exists'] }, 400)
      const created = { ...first, ...JSON.parse(String(init?.body)), id: 3, note: '' }
      rows.push(created)
      return jsonResponse(created, 201)
    }
    if (method === 'PATCH') {
      const note = rows.find((item) => url.endsWith(`/${item.id}/`))!
      Object.assign(note, JSON.parse(String(init?.body)))
      return jsonResponse(note)
    }
    if (method === 'DELETE') { rows.splice(rows.findIndex((item) => url.endsWith(`/${item.id}/`)), 1); return new Response(null, { status: 204 }) }
    throw new Error(`${method} ${url}`)
  })
  render(<I18nProvider><GenericNotes scope={scope} objectId="42" /></I18nProvider>)
  return { fetchMock }
}

afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('GenericNotes', () => {
  it('uses the common Admin action when a visible note has an Admin URL', async () => {
    setup('project', true, false, '/admin/infos/genericnote/1/change/')
    await screen.findByRole('tab', { name: 'Général' })
    await userEvent.click(screen.getByRole('button', { name: 'Actions sur la note' }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })).toHaveAttribute('href', '/admin/infos/genericnote/1/change/')
  })
  it.each(['project', 'employee'] as const)('uses the same tabs and create workflow for %s', async (scope) => {
    const { fetchMock } = setup(scope)
    expect(await screen.findByRole('tab', { name: 'Général' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Hello')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Privé/ }))
    expect(screen.getByText('Secret')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter une note' }))
    await userEvent.type(screen.getByLabelText('Nom'), 'Réunion')
    await userEvent.selectOptions(screen.getByLabelText('Visibilité'), 'creator')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByTestId('wysiwyg')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Réunion/ })).toHaveAttribute('aria-selected', 'true')
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).includes(`/notes/${scope}/42/`) && init?.method === 'POST')).toBe(true)
  }, 12000)

  it('autosaves content and saves before changing tabs', async () => {
    const { fetchMock } = setup()
    await screen.findByRole('tab', { name: 'Général' })
    await userEvent.click(screen.getByRole('button', { name: 'Modifier' }))
    await userEvent.clear(screen.getByLabelText('Editor'))
    await userEvent.type(screen.getByLabelText('Editor'), '<p>Updated</p>')
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PATCH' && String(init.body).includes('Updated'))).toBe(true), { timeout: 3500 })
    expect(await screen.findByText('Enregistré')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Privé/ }))
    expect(screen.getByText('Secret')).toBeInTheDocument()
  })

  it('keeps actions and Add hidden for read-only viewers', async () => {
    setup('employee', true)
    expect(await screen.findByRole('tab', { name: 'Général' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter une note' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions sur la note' })).not.toBeInTheDocument()
  })

  it('translates a duplicate name error without closing the create dialog', async () => {
    setup('project', false, true)
    await screen.findByRole('tab', { name: 'Général' })
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter une note' }))
    await userEvent.type(screen.getByLabelText('Nom'), 'Général')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('Une note porte déjà ce nom.')).toBeInTheDocument()
    expect(screen.getByLabelText('Nom')).toHaveValue('Général')
  })

  it('renames separately and confirms deletion', async () => {
    const { fetchMock } = setup()
    await screen.findByRole('tab', { name: 'Général' })
    await userEvent.click(screen.getByRole('button', { name: 'Actions sur la note' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Renommer' }))
    const input = screen.getByLabelText('Nom')
    await userEvent.clear(input)
    await userEvent.type(input, 'Autre')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByRole('tab', { name: 'Autre' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Actions sur la note' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(screen.getByText(/définitivement supprimée/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Actions sur la note' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true))
  }, 12000)
})
