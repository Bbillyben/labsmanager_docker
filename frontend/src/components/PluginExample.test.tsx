import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { Page, EmployeeTab } from '../../../data/plugins/ModelExample/frontend/src/main'

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })

describe('ModelExample in the host React tree', () => {
  it('uses the shared employee selector and host React hooks on its page', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.startsWith('/api/v1/employees/?')) return json({ results: [{ id: 7, first_name: 'Ada', last_name: 'Lovelace' }], next: null, count: 1 })
      if (url === '/api/v1/employees/7/') return json({ id: 7, first_name: 'Ada', last_name: 'Lovelace' })
      throw new Error(`Unexpected URL ${url}`)
    })
    render(<I18nProvider><Page context={{}} /></I18nProvider>)
    expect(screen.getByRole('heading', { name: 'Model Example' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Interactions React : 0' }))
    expect(screen.getByRole('button', { name: 'Interactions React : 1' })).toBeInTheDocument()
    await userEvent.type(screen.getByRole('combobox', { name: 'Employé' }), 'Ada')
    await userEvent.click(await screen.findByRole('option', { name: 'Ada Lovelace' }))
    await waitFor(() => expect(screen.getByText('7')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/^\/api\/v1\/employees\/\?/), expect.objectContaining({ credentials: 'include' }))
  })

  it('receives the authorized employee context in a tab', async () => {
    render(<I18nProvider><EmployeeTab context={{ entity: 'employee', objectId: 12 }} /></I18nProvider>)
    expect(screen.getByText('Contexte autorisé : employee #12')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Interactions React : 0' }))
    expect(screen.getByRole('button', { name: 'Interactions React : 1' })).toBeInTheDocument()
  })
})
