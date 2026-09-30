import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { AppRouter } from '../router/AppRouter'
import { authenticatedUser, jsonResponse } from '../test/fixtures'
import type { ProjectOverview } from '../api/projects'

vi.mock('../gantt/LabsManagerGantt', () => ({ LabsManagerGantt: () => <div data-testid="project-gantt" /> }))

const full = { can_add: true, can_change: true, can_delete: true }
const readonly = { can_add: false, can_change: false, can_delete: false }
const planningItem = { id: 21, name: 'Project task', desc: null, start_date: '2026-01-01', end_date: null, status: false, type: 'o', quotity: '0.000', display_state: 'in_progress', days_to_due: null, work_kind: 'task', project: { id: 3, name: 'Atlas', can_view: true }, employees: [{ id: 7, first_name: 'Marie', last_name: 'Curie', can_view: true }], dependencies: [] }
const base: ProjectOverview = {
  id: 3, name: 'Atlas', start_date: '2026-01-01', end_date: null, status: true,
  capabilities: full, funding_visible: true,
  generic_info: { capabilities: full, items: [{ id: 8, type: { id: 2, name: 'URL', icon: 'Contact' }, value: 'old' }] },
  institutions: { capabilities: full, items: [{ id: 9, institution: { id: 4, short_name: 'UL', name: 'Université de Lille' }, status: 'p', status_label: 'Participant' }] },
  participants: { capabilities: full, items: [{ id: 10, employee: { id: 7, first_name: 'Marie', last_name: 'Curie', is_active: true, can_view: true }, status: 'p', status_label: 'Participant', start_date: null, end_date: null, quotity: '0.500', is_active: true }] },
}

function mount(path = '/app/projects/3', language = 'fr-FR') {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: [language] })
  window.history.replaceState({}, '', path)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}

function mockApi(initial: ProjectOverview = base, detailStatus = 200, options: { writeError?: boolean; refreshError?: boolean } = {}) {
  const state = structuredClone(initial)
  const projectSettings = [
    { key: 'EXPENSE_CALCULATION', name: 'Mode de calcul des dépenses', description: 'Source des dépenses.', type: 'choice', value: 's', default: 's', choices: [{ value: 's', label: 'Simple' }, { value: 'e', label: 'Dépenses individuelles' }, { value: 'h', label: 'Hybride' }] },
    { key: 'LEADER_EDIT_FUND', name: 'Le responsable peut modifier les financements', description: 'Autorise le responsable.', type: 'boolean', value: true, default: true, choices: [] },
  ]
  let writes = 0
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    const body = init?.body ? JSON.parse(String(init.body)) : {}
    if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
    if (url === '/api/v1/notes/project/3/') return jsonResponse({ capabilities: { can_add: false }, items: [] })
    if (url === '/api/v1/projects/3/settings/' && method === 'GET') return jsonResponse({ settings: projectSettings })
    const settingKey = url.match(/^\/api\/v1\/projects\/3\/settings\/([^/]+)\/$/)?.[1]
    if (settingKey && method === 'PATCH') {
      const setting = projectSettings.find((entry) => entry.key === settingKey)
      if (!setting) return jsonResponse({ detail: 'Not found' }, 404)
      Object.assign(setting, { value: body.value })
      return jsonResponse(setting)
    }
    if (url.startsWith('/api/v1/reports/project/')) return jsonResponse({ templates: [{ id: 7, name: 'Rapport projet' }] })
    if (method !== 'GET' && options.writeError) return jsonResponse({ detail: 'Refus serveur' }, 400)
    if (method !== 'GET') writes++
    if (url === '/api/v1/projects/3/' && method === 'GET') return options.refreshError && writes ? jsonResponse({ detail: 'Lecture impossible' }, 503) : jsonResponse(detailStatus === 200 ? state : { detail: 'Not found' }, detailStatus)
    if (url === '/api/v1/projects/3/funding/' && method === 'GET') return jsonResponse({ capabilities: { can_add: projectSettings[1].value }, project_dates: { start_date: state.start_date, end_date: state.end_date }, funds: [], overview: { rows: [], fund_totals: {}, grand_total: { amount: '0.00', expense: '0.00', available: '0.00' } } })
    if (url === '/api/v1/projects/3/funding/options/' && method === 'GET') return jsonResponse({ funders: [], institutions: [], cost_types: [], project_dates: { start_date: state.start_date, end_date: state.end_date } })
    if (url.startsWith('/api/v1/projects/3/planning/') && method === 'GET') return jsonResponse({ capabilities: state.capabilities, participants: [{ id: 7, first_name: 'Marie', last_name: 'Curie' }], items: [planningItem] })
    if (url === '/api/v1/projects/3/planning/' && method === 'POST') return jsonResponse({ ...planningItem, ...body, id: 22, start_date: body.start_date ?? null }, 201)
    if (url === '/api/v1/projects/3/planning/21/' && method === 'PATCH') return jsonResponse({ ...planningItem, ...body })
    if (url === '/api/v1/projects/3/planning/21/' && method === 'DELETE') return new Response(null, { status: 204 })
    if (url === '/api/v1/planning/items/21/dependencies/') return jsonResponse({ can_add: false, predecessors: [], successors: [] })
    if (url === '/api/v1/projects/3/overview-options/') return jsonResponse({ generic_info_types: [{ id: 2, name: 'URL', icon: 'Contact' }], institutions: [{ id: 4, short_name: 'UL', name: 'Université de Lille' }, { id: 5, short_name: 'IN', name: 'Inserm' }] })
    if (url.startsWith('/api/v1/employees/?')) return jsonResponse({ count: 1, next: null, previous: null, results: [{ id: 11, first_name: 'Ada', last_name: 'Lovelace' }] })
    if (url === '/api/v1/employees/11/') return jsonResponse({ id: 11, first_name: 'Ada', last_name: 'Lovelace' })
    if (url === '/api/v1/projects/3/' && method === 'PATCH') { Object.assign(state, body); return jsonResponse({ id: 3, name: state.name, start_date: state.start_date, end_date: state.end_date, status: state.status }) }
    const resource = url.match(/^\/api\/v1\/projects\/3\/(generic-info|institutions|participants)\/(\d+\/)?$/)
    if (resource) {
      const key = resource[1] === 'generic-info' ? 'generic_info' : resource[1] as 'institutions' | 'participants'
      const items = state[key].items as Array<{ id: number }>
      const id = resource[2] ? Number(resource[2].replace('/', '')) : 0
      if (method === 'DELETE') { state[key].items = items.filter((item) => item.id !== id) as never; return new Response(null, { status: 204 }) }
      if (method === 'POST' || method === 'PATCH') {
        const saved = key === 'generic_info'
          ? { id: id || 12, type: { id: 2, name: 'URL', icon: 'Contact' }, value: body.value }
          : key === 'institutions'
            ? { id: id || 13, institution: { id: body.institution_id || 4, short_name: body.institution_id === 5 ? 'IN' : 'UL', name: body.institution_id === 5 ? 'Inserm' : 'Université de Lille' }, status: body.status, status_label: body.status === 'c' ? 'Coordinator' : 'Participant' }
            : { id: id || 14, employee: { id: body.employee_id || 7, first_name: body.employee_id === 11 ? 'Ada' : 'Marie', last_name: body.employee_id === 11 ? 'Lovelace' : 'Curie', is_active: true, can_view: true }, status: body.status, status_label: 'Participant', start_date: body.start_date, end_date: body.end_date, quotity: body.quotity, is_active: true }
        state[key].items = [...items.filter((item) => item.id !== id), saved] as never
        return jsonResponse(saved, method === 'POST' ? 201 : 200)
      }
    }
    return jsonResponse({ detail: `Unexpected ${method} ${url}` }, 404)
  })
  return { fetchMock, state }
}

afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

describe('ProjectSingle Overview', () => {
  it('places Project Settings after Edit and refreshes the active Planning panel on close', async () => {
    const { fetchMock } = mockApi({ ...base, capabilities: { ...full, can_change_settings: true, can_export_word: true, can_export_pdf: true } })
    mount('/app/projects/3/tasks')
    const user = userEvent.setup()
    const trigger = await screen.findByRole('button', { name: 'Actions pour Atlas' }, { timeout: 5000 })
    await screen.findByRole('button', { name: 'Ouvrir le détail de Project task' })
    const planningReads = () => fetchMock.mock.calls.filter(([url, init]) => String(url) === '/api/v1/projects/3/planning/' && (!init?.method || init.method === 'GET')).length
    expect(planningReads()).toBe(1)
    await user.click(trigger)
    const menu = await screen.findByRole('menu')
    expect(within(menu).getAllByRole('menuitem').map((item) => item.textContent)).toEqual(['Modifier le projet', 'Paramètres du projet', 'Export Word', 'Export PDF'])
    expect(within(menu).getAllByRole('separator')).toHaveLength(1)
    await user.click(within(menu).getByRole('menuitem', { name: 'Paramètres du projet' }))
    const sheet = await screen.findByRole('dialog')
    const choice = await within(sheet).findByRole('combobox', { name: 'Mode de calcul des dépenses' })
    await user.selectOptions(choice, 'e')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url) === '/api/v1/projects/3/settings/EXPENSE_CALCULATION/' && init?.method === 'PATCH')).toBe(true))
    await user.click(within(sheet).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(planningReads()).toBe(2))
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('hides Project Settings without its backend capability', async () => {
    mockApi({ ...base, capabilities: { ...full, can_change_settings: false } })
    mount()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Actions pour Atlas' }))
    expect(screen.queryByRole('menuitem', { name: 'Paramètres du projet' })).not.toBeInTheDocument()
  })
  it('reloads Funding capabilities when a Project setting changes', async () => {
    const { fetchMock } = mockApi({ ...base, capabilities: { ...full, can_change_settings: true } })
    mount('/app/projects/3/funding')
    const user = userEvent.setup()
    expect(await screen.findByRole('button', { name: 'Ajouter un financement' })).toBeInTheDocument()
    const reads = () => fetchMock.mock.calls.filter(([url, init]) => String(url) === '/api/v1/projects/3/funding/' && (!init?.method || init.method === 'GET')).length
    expect(reads()).toBe(1)
    await user.click(await screen.findByRole('button', { name: 'Actions pour Atlas' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Paramètres du projet' }))
    const sheet = await screen.findByRole('dialog')
    await user.click(await within(sheet).findByRole('switch', { name: 'Le responsable peut modifier les financements' }))
    await waitFor(() => expect(within(sheet).getByRole('switch', { name: 'Le responsable peut modifier les financements' })).not.toBeChecked())
    await user.click(within(sheet).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(reads()).toBe(2))
    expect(screen.queryByRole('button', { name: 'Ajouter un financement' })).not.toBeInTheDocument()
  })
  it('uses the entity menu for edit and independent Word/PDF exports', async () => {
    mockApi({ ...base, capabilities: { ...full, can_export_word: true, can_export_pdf: false } })
    mount()
    const user = userEvent.setup()
    const trigger = await screen.findByRole('button', { name: 'Actions pour Atlas' })
    await user.click(trigger)
    expect(await screen.findByRole('menuitem', { name: 'Modifier le projet' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Export Word' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Export PDF' })).not.toBeInTheDocument()
    expect(screen.getByRole('separator')).toBeInTheDocument()
    await user.click(screen.getByRole('menuitem', { name: 'Modifier le projet' }))
    expect(within(screen.getByRole('dialog')).getByText('Modifier le projet')).toBeInTheDocument()
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Annuler' }))
    await waitFor(() => expect(trigger).toHaveFocus())
    await user.click(trigger)
    await user.click(await screen.findByRole('menuitem', { name: 'Export Word' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Exporter le projet — Export Word')
  })

  it('shows a Project export-only menu without a redundant separator', async () => {
    mockApi({ ...base, capabilities: { ...readonly, can_export_word: false, can_export_pdf: true } })
    mount()
    const trigger = await screen.findByRole('button', { name: 'Actions pour Atlas' })
    await userEvent.setup().click(trigger)
    expect(await screen.findByRole('menuitem', { name: 'Export PDF' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Modifier le projet' })).not.toBeInTheDocument()
    expect(screen.queryByRole('separator')).not.toBeInTheDocument()
  })
  it('opens Project Planning through local navigation and reuses the grouped Planning table', async () => {
    const { fetchMock } = mockApi()
    mount('/app/projects/3/tasks')
    expect(await screen.findByRole('button', { name: 'Ouvrir le détail de Project task' }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'En cours · 1' })).toBeInTheDocument()
    expect(screen.getByText('Personnes assignées: Marie Curie')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url) === '/api/v1/projects/3/planning/')).toBe(true)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ouvrir le détail de Project task' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Project task')
  })

  it('creates a milestone without a stale task start date and limits assignees to participants', async () => {
    const { fetchMock } = mockApi()
    mount('/app/projects/3/tasks')
    await screen.findByRole('button', { name: 'Ouvrir le détail de Project task' }, { timeout: 5000 })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter une tâche ou un jalon' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByText('Marie Curie')).toBeInTheDocument()
    expect(within(sheet).queryByText('C Outsider')).not.toBeInTheDocument()
    await userEvent.setup().type(within(sheet).getByRole('textbox', { name: 'Nom' }), 'Milestone new')
    await userEvent.setup().type(within(sheet).getByLabelText('Début'), '2026-10-01')
    await userEvent.setup().selectOptions(within(sheet).getByRole('combobox', { name: 'Tâche ou jalon' }), 'milestone')
    expect(within(sheet).queryByLabelText('Début')).not.toBeInTheDocument()
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url) === '/api/v1/projects/3/planning/' && init?.method === 'POST')).toBe(true))
    const call = fetchMock.mock.calls.find(([url, init]) => String(url) === '/api/v1/projects/3/planning/' && init?.method === 'POST')!
    expect(JSON.parse(String(call[1]?.body))).not.toHaveProperty('start_date')
  })

  it('keeps a read-only Project Planning visible without mutation controls', async () => {
    mockApi({ ...base, capabilities: readonly })
    mount('/app/projects/3/tasks')
    expect(await screen.findByRole('button', { name: 'Ouvrir le détail de Project task' }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter une tâche ou un jalon' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Project task' })).not.toBeInTheDocument()
  })

  it('passes URL Planning filters to the same scoped API before switching to Gantt', async () => {
    const { fetchMock } = mockApi()
    mount('/app/projects/3/tasks?search=Project&kind=task&employee=7')
    expect(await screen.findByRole('button', { name: 'Ouvrir le détail de Project task' }, { timeout: 5000 })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url) === '/api/v1/projects/3/planning/?search=Project&kind=task&employee=7')).toBe(true)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Gantt' }))
    expect(screen.getByRole('button', { name: 'Gantt' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('project-gantt')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => String(url).startsWith('/api/v1/projects/3/planning/'))).toHaveLength(1)
  })

  it('offers edit and confirmed delete through the canonical item menu', async () => {
    const { fetchMock } = mockApi()
    mount('/app/projects/3/tasks')
    await screen.findByRole('button', { name: 'Ouvrir le détail de Project task' }, { timeout: 5000 })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Project task' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByRole('textbox', { name: 'Nom' })).toHaveValue('Project task')
    await userEvent.setup().clear(within(sheet).getByRole('textbox', { name: 'Nom' }))
    await userEvent.setup().type(within(sheet).getByRole('textbox', { name: 'Nom' }), 'Updated task')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url) === '/api/v1/projects/3/planning/21/' && init?.method === 'PATCH')).toBe(true))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Project task' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    await userEvent.setup().click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Annuler' }))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions pour Project task' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    await userEvent.setup().click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url) === '/api/v1/projects/3/planning/21/' && init?.method === 'DELETE')).toBe(true))
  })
  it('translates Project navigation, overview, status and actions in English while preserving business names', async () => {
    mockApi()
    mount('/app/projects/3', 'en-US')
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Project sections' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Project information' })).toBeInTheDocument()
    expect(screen.getAllByText('Active').length).toBeGreaterThan(0)
    expect(screen.getByText('Université de Lille')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add institution' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add participant' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actions for UL' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Add participant' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByRole('heading', { name: 'Add participant' })).toBeInTheDocument()
    expect(within(sheet).getByRole('combobox', { name: 'Role' })).toBeInTheDocument()
  })

  it.each([
    ['Landmark', 'landmark'], ['BookOpen', 'book-open'], ['Bookmark', 'bookmark'],
    ['Cloud', 'cloud'], ['UserRoundCheck', 'user-round-check'],
  ])('renders the Project type icon %s through the shared Lucide registry', async (icon, className) => {
    mockApi({ ...base, generic_info: { ...base.generic_info, items: [{ id: 8, type: { id: 2, name: 'Id Financeur', icon }, value: 'value' }] } })
    mount()
    expect(await screen.findByText('Id Financeur')).toBeInTheDocument()
    expect(document.querySelector(`.lucide-${className}`)).toBeInTheDocument()
  })

  it.each([null, '', 'style:fas,icon:unknown', 'UnknownIcon'])('uses the GenericInfo fallback for Project icon %s', async (icon) => {
    mockApi({ ...base, generic_info: { ...base.generic_info, items: [{ id: 8, type: { id: 2, name: 'Citation Article', icon }, value: 'value' }] } })
    mount()
    expect(await screen.findByText('Citation Article')).toBeInTheDocument()
    expect(document.querySelector('.lucide-circle-question-mark')).toBeInTheDocument()
  })

  it('loads directly with header, four blocks and disabled declarative navigation', async () => {
    const { fetchMock } = mockApi()
    mount()
    expect(await screen.findByRole('heading', { name: 'Atlas' })).toBeInTheDocument()
    expect(screen.getAllByText('Actif').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Informations du projet' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Informations générales' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Institutions' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Participants' })).toBeInTheDocument()
    const projectColumn = screen.getByRole('region', { name: 'Informations du projet' }).parentElement
    expect(projectColumn).toContainElement(screen.getByRole('region', { name: 'Informations générales' }))
    expect(projectColumn?.parentElement).toContainElement(screen.getByRole('region', { name: 'Institutions' }))
    expect(projectColumn?.parentElement).toContainElement(screen.getByRole('region', { name: 'Participants' }))
    const nav = screen.getByRole('navigation', { name: 'Sections du projet' })
    expect(within(nav).getByRole('link', { name: 'Vue d’ensemble' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Jalons et tâches' })).toHaveAttribute('href', '/app/projects/3/tasks')
    expect(within(nav).getByRole('link', { name: 'Budgets' })).toHaveAttribute('href', '/app/projects/3/budgets')
    expect(within(nav).getByRole('link', { name: 'Contributions' })).toHaveAttribute('href', '/app/projects/3/contributions')
    expect(within(nav).getByRole('link', { name: 'Contrats' })).toHaveAttribute('href', '/app/projects/3/contracts')
    expect(within(nav).getByRole('link', { name: 'Notes' })).toHaveAttribute('href', '/app/projects/3/notes')
    expect(within(nav).getAllByText(/Calendrier|Absences de l’équipe|Fonds|Budgets|Contributions|Contrats|Tableau de bord|Notes/)).toHaveLength(7)
    expect(fetchMock.mock.calls.filter(([url]) => String(url).startsWith('/api/v1/projects/3/'))).toHaveLength(1)
  })

  it('loads shared Notes on the Project route', async () => {
    mockApi()
    mount('/app/projects/3/notes')
    expect(await screen.findByText('Aucune note.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Notes' })).toHaveAttribute('aria-current', 'page')
  })

  it('shows an inaccessible project without loading child resources', async () => {
    const { fetchMock } = mockApi(base, 404)
    mount()
    expect(await screen.findByText('Projet introuvable ou inaccessible.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('overview-options'))).toBe(false)
  })

  it('keeps readonly blocks readable and links visible Employees to React', async () => {
    mockApi({ ...base, capabilities: readonly, generic_info: { ...base.generic_info, capabilities: readonly }, institutions: { ...base.institutions, capabilities: readonly }, participants: { ...base.participants, capabilities: readonly } })
    mount()
    expect(await screen.findByRole('link', { name: 'Marie Curie' })).toHaveAttribute('href', '/app/employees/7')
    expect(screen.queryByRole('button', { name: 'Ajouter une institution' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter un participant' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajouter une information' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour UL' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Marie Curie' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour URL' })).not.toBeInTheDocument()
  })

  it('pins item actions on selection, clears them outside, and lists only permitted actions', async () => {
    mockApi({ ...base, institutions: { ...base.institutions, capabilities: { can_add: true, can_change: false, can_delete: true } } })
    mount()
    const institutions = await screen.findByRole('region', { name: 'Institutions' })
    const item = within(institutions).getByText('Université de Lille').closest('li')!
    await userEvent.setup().click(item)
    expect(item).toHaveAttribute('data-selected', 'true')
    await userEvent.setup().click(within(institutions).getByRole('button', { name: 'Actions pour UL' }))
    expect(await screen.findByRole('menuitem', { name: 'Supprimer' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Modifier' })).not.toBeInTheDocument()
    await userEvent.setup().keyboard('{Escape}')
    await userEvent.setup().click(screen.getByRole('heading', { name: 'Atlas' }))
    expect(item).toHaveAttribute('data-selected', 'false')
    expect(within(institutions).getByRole('button', { name: 'Ajouter une institution' })).toBeInTheDocument()
  })

  it('reuses ProjectSheet to edit root information and refreshes the overview', async () => {
    const { fetchMock } = mockApi()
    mount()
    await screen.findByRole('heading', { name: 'Atlas' })
    await userEvent.setup().click(within(screen.getByRole('region', { name: 'Informations du projet' })).getByRole('button', { name: 'Modifier' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Nom du projet')).toBeDisabled()
    await userEvent.setup().click(within(sheet).getByRole('checkbox', { name: 'Actif' }))
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1))
    await waitFor(() => expect(screen.getAllByText('Inactif').length).toBeGreaterThan(0))
  })

  it('keeps the Sheet open after a write error and does not replay a successful PATCH when refresh fails', async () => {
    const failed = mockApi(base, 200, { writeError: true })
    mount()
    await screen.findByRole('heading', { name: 'Atlas' })
    await userEvent.setup().click(within(screen.getByRole('region', { name: 'Informations du projet' })).getByRole('button', { name: 'Modifier' }))
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(screen.getByRole('dialog')).findByText('Refus serveur')).toBeInTheDocument()
    expect(failed.fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1)
  })

  it('reports a read failure after a successful write without replaying it', async () => {
    const { fetchMock } = mockApi(base, 200, { refreshError: true })
    mount()
    await screen.findByRole('heading', { name: 'Atlas' })
    await userEvent.setup().click(within(screen.getByRole('region', { name: 'Informations du projet' })).getByRole('button', { name: 'Modifier' }))
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('checkbox', { name: 'Actif' }))
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText(/La modification a été enregistrée/)).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1)
  })

  it('creates and deletes GenericInfo with the shared Sheet and confirmation', async () => {
    const { fetchMock } = mockApi()
    mount()
    await screen.findByText('old')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter une information' }))
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().selectOptions(await within(sheet).findByRole('combobox'), '2')
    await userEvent.setup().type(within(sheet).getByRole('textbox', { name: 'Valeur (facultative)' }), 'new')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('new')).toBeInTheDocument()
    await userEvent.setup().click(screen.getAllByRole('button', { name: 'Actions pour URL' }).at(-1)!)
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    await userEvent.setup().clear(within(screen.getByRole('dialog')).getByRole('textbox', { name: 'Valeur (facultative)' }))
    await userEvent.setup().type(within(screen.getByRole('dialog')).getByRole('textbox', { name: 'Valeur (facultative)' }), 'updated')
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('updated')).toBeInTheDocument()
    await userEvent.setup().click(screen.getAllByRole('button', { name: 'Actions pour URL' }).at(-1)!)
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
    await userEvent.setup().click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(1))
  })

  it('edits Institutions and navigates from a Participant name without a row action', async () => {
    const { fetchMock } = mockApi()
    mount()
    await screen.findByRole('link', { name: 'Marie Curie' })
    const institutions = screen.getByRole('region', { name: 'Institutions' })
    expect(within(institutions).queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(within(institutions).queryByRole('button', { name: 'Supprimer' })).not.toBeInTheDocument()
    await userEvent.setup().click(within(institutions).getByText('Université de Lille'))
    expect(within(institutions).getByText('Université de Lille').closest('li')).toHaveAttribute('data-selected', 'true')
    await userEvent.setup().click(within(institutions).getByRole('button', { name: 'Actions pour UL' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    await userEvent.setup().selectOptions(within(screen.getByRole('dialog')).getByLabelText('Rôle de l’institution'), 'c')
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/institutions/9/') && init?.method === 'PATCH')).toBe(true))
    const employeeLink = screen.getByRole('link', { name: 'Marie Curie' })
    expect(employeeLink.closest('li')).toHaveAttribute('data-selected', 'false')
    await userEvent.setup().click(employeeLink)
    expect(window.location.pathname).toBe('/app/employees/7')
  })

  it('searches Employees and creates a Participant through the bounded selector', async () => {
    const { fetchMock } = mockApi()
    mount()
    await screen.findByRole('link', { name: 'Marie Curie' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Ajouter un participant' }))
    await userEvent.setup().type(screen.getByRole('combobox', { name: 'Employee' }), 'Ada')
    await screen.findByRole('option', { name: 'Ada Lovelace' })
    await userEvent.setup().keyboard('{ArrowDown}{Enter}')
    await userEvent.setup().click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/participants/') && init?.method === 'POST' && String(init.body).includes('"employee_id":11'))).toBe(true))
    expect(await screen.findByRole('link', { name: 'Ada Lovelace' })).toHaveAttribute('href', '/app/employees/11')
  })

  it('edits and deletes a Participant only after confirmation', async () => {
    const { fetchMock } = mockApi()
    mount()
    const participants = await screen.findByRole('region', { name: 'Participants' })
    await userEvent.setup().click(within(participants).getByRole('button', { name: 'Actions pour Marie Curie' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).queryByRole('combobox', { name: 'Employee' })).not.toBeInTheDocument()
    await userEvent.setup().clear(within(sheet).getByRole('spinbutton', { name: 'Quotité (%)' }))
    await userEvent.setup().type(within(sheet).getByRole('spinbutton', { name: 'Quotité (%)' }), '25')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/participants/10/') && init?.method === 'PATCH' && String(init.body).includes('"quotity":"0.250"'))).toBe(true))
    await userEvent.setup().click(within(participants).getByRole('button', { name: 'Actions pour Marie Curie' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
    await userEvent.setup().click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/participants/10/') && init?.method === 'DELETE')).toBe(true))
  })

  it('creates and deletes an Institution with confirmation', async () => {
    const { fetchMock } = mockApi()
    mount()
    const institutions = await screen.findByRole('region', { name: 'Institutions' })
    await userEvent.setup().click(within(institutions).getByRole('button', { name: 'Ajouter une institution' }))
    const sheet = screen.getByRole('dialog')
    await userEvent.setup().selectOptions(await within(sheet).findByRole('combobox', { name: 'Institution' }), '5')
    await userEvent.setup().click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(institutions).findByText('Inserm')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/institutions/') && init?.method === 'POST')).toBe(true)
    await userEvent.setup().click(within(institutions).getByRole('button', { name: 'Actions pour IN' }))
    await userEvent.setup().click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')).toHaveLength(0)
    await userEvent.setup().click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/institutions/13/') && init?.method === 'DELETE')).toBe(true))
  })
})
