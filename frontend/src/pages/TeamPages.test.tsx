import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { TeamListPage } from './TeamListPage'
import { TeamDetailPage } from './TeamDetailPage'

const team = {
  id: 4, name: 'Atlas', leader: { id: 7, name: 'Ada Reader', can_view: true },
  mates: [{ id: 8, employee: { id: 9, name: 'Grace Member', can_view: false }, start_date: '2020-01-01', end_date: '2020-12-31', is_active: false, capabilities: { can_change: false, can_delete: false } }],
  capabilities: { can_view: true, can_change: false, can_manage_composition: false },
}
const projects = [{ id: 3, name: 'Project Alpha', start_date: '2026-01-01', end_date: null, status: true }]
const budgets = [{ id: 5, project: { id: 3, name: 'Project Alpha' }, fund: { id: 2, name: 'Fund 2' }, cost_type: { id: 6, short_name: 'HR', name: 'Human resources' }, desc: 'Researcher', amount: '100.00', expense: '25.00', available: '75.00', capabilities: { can_add: false, can_change: false, can_delete: false } }]

function mount(path: string) {
  return render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/teams/" element={<TeamListPage />} />
    <Route path="/teams/:teamId" element={<TeamDetailPage />} />
    <Route path="/teams/:teamId/projects" element={<TeamDetailPage />} />
    <Route path="/teams/:teamId/budget" element={<TeamDetailPage />} />
    <Route path="/teams/:teamId/notes" element={<TeamDetailPage />} />
    <Route path="/employees/:employeeId" element={<p>Employee profile</p>} />
    <Route path="/projects/:projectId" element={<p>Project profile</p>} />
  </Routes></MemoryRouter></I18nProvider>)
}

describe('Team pages', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }) })
  afterEach(() => vi.restoreAllMocks())

  it('keeps Team filters and ordering in the URL and links to detail', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => jsonResponse({ count: 1, next: null, previous: null, results: [team], capabilities: { can_add: false, can_choose_leader: false, default_leader: null } }))
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:team-export') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    mount('/teams/?name=Atlas&leader=7&mate=9&ordering=-name&limit=10&offset=20')
    expect(await screen.findByRole('link', { name: 'Atlas' })).toHaveAttribute('href', '/teams/4')
    expect(screen.getByRole('columnheader', { name: /Équipe/i })).toHaveAttribute('aria-sort', 'descending')
    const url = String(fetch.mock.calls.find(([input]) => String(input).startsWith('/api/v1/teams/?'))?.[0])
    expect(url).toContain('mate=9')
    expect(url).toContain('leader=7')
    expect(url).toContain('ordering=-name')
    await userEvent.click(screen.getByRole('button', { name: 'Exporter' }))
    await userEvent.click(screen.getByRole('button', { name: 'Télécharger' }))
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).startsWith('/api/v1/teams/export/'))).toBe(true))
    const exportUrl = String(fetch.mock.calls.find(([input]) => String(input).startsWith('/api/v1/teams/export/'))?.[0])
    expect(exportUrl).toContain('format=xlsx')
    expect(exportUrl).toContain('mate=9')
    expect(exportUrl).not.toContain('offset=')
    expect(exportUrl).not.toContain('limit=')
    expect(screen.queryByRole('button', { name: 'Ajouter une équipe' })).not.toBeInTheDocument()
    click.mockRestore()
  })

  it('shows readable composition, linked leader and no mutation for a reader', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(team))
    mount('/teams/4')
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ada Reader' })).toHaveAttribute('href', '/employees/7')
    expect(screen.getByText('Grace Member')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Grace Member' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter un membre' })).not.toBeInTheDocument()
    expect(screen.getByText('Inactif')).toBeInTheDocument()
    expect(screen.getAllByText(/2020/)).toHaveLength(2)
  })

  it('shows Project and Budget contextual read-only lists with Project links', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      return jsonResponse(url.endsWith('/projects/') ? projects : url.endsWith('/budgets/') ? budgets : team)
    })
    const user = userEvent.setup()
    mount('/teams/4/projects')
    expect(await screen.findByRole('link', { name: 'Project Alpha' })).toHaveAttribute('href', '/projects/3')
    await user.click(screen.getByRole('link', { name: 'Budget' }))
    expect(await screen.findByText('Fund 2')).toBeInTheDocument()
    expect(screen.getByText(/75,00/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /ajouter un budget|modifier le budget|supprimer le budget/i })).not.toBeInTheDocument()
  })

  it('allows authorized composition through the existing Sheet', async () => {
    const editable = { ...team, mates: team.mates.map((mate) => ({ ...mate, capabilities: { can_change: true, can_delete: true } })), capabilities: { can_view: true, can_change: true, can_manage_composition: true } }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.startsWith('/api/v1/employees/?')) return jsonResponse({ count: 1, next: null, previous: null, results: [{ id: 10, first_name: 'Marie', last_name: 'Curie' }] })
      if (init?.method === 'POST') return jsonResponse({ id: 12 }, 201)
      return jsonResponse(editable)
    })
    mount('/teams/4')
    await screen.findByRole('button', { name: 'Ajouter un membre' })
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter un membre' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Rechercher et sélectionner un employé')
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/api/v1/teams/4/'))).toBe(true)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Enregistrer' })).toBeDisabled())
  })

  it('confirms member removal and keeps the Team mutation scoped', async () => {
    const editable = { ...team, mates: team.mates.map((mate) => ({ ...mate, capabilities: { can_change: true, can_delete: true } })), capabilities: { can_view: true, can_change: true, can_manage_composition: true } }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (init?.method === 'DELETE') return new Response(null, { status: 204 })
      return jsonResponse(editable)
    })
    mount('/teams/4')
    await screen.findByRole('button', { name: 'Actions pour Grace Member' })
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Grace Member' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('Retirer Grace Member')
    expect(fetch.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => String(url) === '/api/v1/teams/4/mates/8/' && init?.method === 'DELETE')).toBe(true))
  })

  it('creates a Team from the list using backend capabilities', async () => {
    const capabilities = { can_add: true, can_choose_leader: false, default_leader: { id: 7, name: 'Ada Reader' } }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => init?.method === 'POST' ? jsonResponse(team, 201) : jsonResponse({ count: 1, next: null, previous: null, results: [team], capabilities }))
    mount('/teams/')
    await userEvent.click(await screen.findByRole('button', { name: 'Ajouter une équipe' }))
    expect(screen.getByRole('dialog')).toHaveTextContent('Ada Reader')
    await userEvent.type(screen.getByRole('textbox', { name: 'Équipe' }), 'Beta')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => String(url) === '/api/v1/teams/' && init?.method === 'POST' && String(init.body).includes('"leader_id":7'))).toBe(true))
  })

  it('edits TeamMate dates through its action menu and keeps active status visible', async () => {
    const editable = { ...team, mates: team.mates.map((mate) => ({ ...mate, is_active: true, capabilities: { can_change: true, can_delete: true } })), capabilities: { can_view: true, can_change: true, can_manage_composition: true } }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => init?.method === 'PATCH' ? jsonResponse(editable.mates[0]) : jsonResponse(editable))
    mount('/teams/4')
    await screen.findByText('Grace Member')
    expect(screen.getByText('Actif')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Grace Member' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('Date de début')
    await userEvent.clear(screen.getByLabelText('Date de fin'))
    await userEvent.type(screen.getByLabelText('Date de fin'), '2027-12-31')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetch.mock.calls.some(([url, init]) => String(url) === '/api/v1/teams/4/mates/8/' && init?.method === 'PATCH' && String(init.body).includes('"end_date":"2027-12-31"'))).toBe(true))
  })
})
