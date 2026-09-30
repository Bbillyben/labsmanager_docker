import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeGenericInfo } from './EmployeeGenericInfo'

const type = { id: 2, name: 'Badge', icon: 'Badge' }
const item = { id: 3, type, value: 'old value' }
const full = { can_add: true, can_change: true, can_delete: true }
type Options = {
  capabilities?: typeof full; empty?: boolean; icon?: string | null
  failure?: number | 'network'; refreshFailure?: boolean; pending?: boolean
  errors?: object
}
function setup(options: Options = {}) {
  let reads = 0
  let items = options.empty ? [] : [{ ...item, type: { ...type, icon: options.icon === undefined ? 'Badge' : options.icon } }]
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (method !== 'GET') {
      if (options.pending) return new Promise<Response>(() => {})
      if (options.failure === 'network') throw new TypeError('offline')
      if (options.failure) return jsonResponse(options.errors ?? { detail: 'Refus serveur' }, options.failure)
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      if (method === 'DELETE') { items = []; return new Response(null, { status: 204 }) }
      const saved = { ...item, id: method === 'POST' ? 4 : 3, value: body.value }
      items = [saved]
      return jsonResponse(saved, method === 'POST' ? 201 : 200)
    }
    if (url === '/api/v1/generic-info-types/') return jsonResponse([type])
    reads++
    if (reads > 1 && options.refreshFailure) return jsonResponse({}, 503)
    return jsonResponse({ capabilities: options.capabilities ?? full, items })
  })
  render(<I18nProvider><EmployeeGenericInfo employeeId="1" /></I18nProvider>)
  const writes = () => fetch.mock.calls.filter(([, init]) => init?.method && init.method !== 'GET')
  return { fetch, writes }
}
async function createForm() {
  await userEvent.click(await screen.findByRole('button', { name: 'Ajouter une information' }))
  await userEvent.selectOptions(await screen.findByRole('combobox'), '2')
  return screen.getByRole('textbox', { name: 'Valeur (facultative)' })
}
async function action(name: 'Modifier' | 'Supprimer') {
  await userEvent.click(await screen.findByRole('button', { name: 'Actions pour Badge' }))
  await userEvent.click(await screen.findByRole('menuitem', { name }))
}

beforeEach(() => Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr'] }))
afterEach(() => vi.restoreAllMocks())

describe('GenericInfo mutations', () => {
  it('renders a reader without mutation controls and uses known icons', async () => {
    setup({ capabilities: { can_add: false, can_change: false, can_delete: false } })
    expect(await screen.findByText('old value')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter une information' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Badge' })).not.toBeInTheDocument()
    expect(document.querySelector('.lucide-badge')).toBeInTheDocument()
  })
  it.each([['Badge', 'badge'], ['Contact', 'contact'], ['Search', 'search'], ['Columns3', 'columns-3'], ['Stethoscope', 'stethoscope']])('renders the configured %s icon', async (icon, className) => {
    setup({ icon })
    await screen.findByText('old value')
    expect(document.querySelector(`.lucide-${className}`)).toBeInTheDocument()
  })
  it.each(['unknown', 'style:fas,icon:unknown', null, ''])('uses CircleQuestionMark for %s', async (icon) => {
    setup({ icon })
    await screen.findByText('old value')
    expect(document.querySelector('.lucide-circle-question-mark')).toBeInTheDocument()
  })
  it('allows add-only users to create without exposing item actions', async () => {
    const { writes } = setup({ capabilities: { can_add: true, can_change: false, can_delete: false } })
    await screen.findByText('old value')
    expect(screen.queryByRole('button', { name: 'Actions pour Badge' })).not.toBeInTheDocument()
    await userEvent.type(await createForm(), 'new value')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('new value')).toBeInTheDocument()
    expect(writes()).toHaveLength(1)
    expect(JSON.parse(String(writes()[0][1]?.body))).toEqual({ type_id: 2, value: 'new value' })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ajouter une information' })).toHaveFocus())
  })
  it('creates a presence-only value in an empty collection', async () => {
    const { writes } = setup({ empty: true })
    await createForm()
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(writes()).toHaveLength(1))
    expect(JSON.parse(String(writes()[0][1]?.body)).value).toBe('')
  })
  it('updates only value, with no type selector', async () => {
    const { writes } = setup()
    await action('Modifier')
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    const input = screen.getByRole('textbox')
    await userEvent.clear(input)
    await userEvent.type(input, 'updated')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('updated')).toBeInTheDocument()
    expect(writes()[0][1]?.method).toBe('PATCH')
    expect(JSON.parse(String(writes()[0][1]?.body))).toEqual({ value: 'updated' })
  })
  it('returns focus to the canonical menu trigger after closing the edit Sheet', async () => {
    setup()
    await action('Modifier')
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Actions pour Badge' })).toHaveFocus())
  })
  it('returns focus to the canonical menu trigger after cancelling deletion', async () => {
    const { writes } = setup()
    await action('Supprimer')
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Annuler' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Actions pour Badge' })).toHaveFocus())
    expect(writes()).toHaveLength(0)
  })
  it('falls back to the section when the deleted item has no add button', async () => {
    setup({ capabilities: { can_add: false, can_change: true, can_delete: true } })
    await action('Supprimer')
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(screen.getByRole('region', { name: 'Informations complémentaires' })).toHaveFocus())
  })
  it('cancels without DELETE, then confirms deletion and restores focus', async () => {
    const { writes } = setup()
    await action('Supprimer')
    expect(writes()).toHaveLength(0)
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(writes()).toHaveLength(0)
    await action('Supprimer')
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(screen.queryByText('old value')).not.toBeInTheDocument())
    expect(writes()).toHaveLength(1)
    expect(writes()[0][1]?.method).toBe('DELETE')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ajouter une information' })).toHaveFocus())
  })
  it.each([400, 403, 404, 500, 'network'] as const)('keeps values and Sheet on failure %s', async (failure) => {
    setup({ failure, errors: failure === 400 ? { value: ['Valeur invalide'], non_field_errors: ['Erreur globale'] } : undefined })
    const input = await createForm()
    await userEvent.type(input, 'keep me')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(input).toHaveValue('keep me')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    if (failure === 400) { expect(screen.getByText('Valeur invalide')).toBeInTheDocument(); expect(screen.getByText('Erreur globale')).toBeInTheDocument() }
  })
  it('keeps successful data when refresh fails and retries only GET', async () => {
    const { writes } = setup({ refreshFailure: true })
    await userEvent.type(await createForm(), 'saved despite refresh')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('saved despite refresh')).toBeInTheDocument()
    const warning = await screen.findByText(/La modification a été enregistrée/)
    expect(warning).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(writes()).toHaveLength(1)
  })
  it('blocks double submissions while pending', async () => {
    const { writes } = setup({ pending: true })
    await createForm()
    const form = screen.getByRole('textbox').closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)
    expect(writes()).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Enregistrement…' })).toBeDisabled()
  })
  it('supports keyboard selection and opening actions', async () => {
    setup()
    const row = (await screen.findByText('old value')).closest('dd')!.parentElement!
    row.focus()
    await userEvent.keyboard('{Enter}')
    expect(row.className).toContain('selected')
    const trigger = screen.getByRole('button', { name: 'Actions pour Badge' })
    trigger.focus()
    await userEvent.keyboard('{Enter}')
    expect(await screen.findByRole('menuitem', { name: 'Modifier' })).toBeInTheDocument()
  })
})
