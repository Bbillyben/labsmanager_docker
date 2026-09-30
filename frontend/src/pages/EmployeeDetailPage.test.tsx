import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { AppRouter } from '../router/AppRouter'
import { authenticatedUser, jsonResponse } from '../test/fixtures'

vi.mock('../gantt/LabsManagerGantt', () => ({
  LabsManagerGantt: ({ data, events, onSelect }: {
    data: { items: Array<{ key: string }> }
    events: Array<{ id: string }>
    onSelect: (identity: { kind: 'work' | 'participation' | 'project'; id: string }) => void
  }) => <div data-testid="employee-gantt">
    <span>{data.items.map((item) => item.key).join(',')}</span>
    <span>{events.map((event) => event.id).join(',')}</span>
    <button onClick={() => onSelect({ kind: 'work', id: '20' })} type="button">Open work</button>
    <button onClick={() => onSelect({ kind: 'participation', id: '1' })} type="button">Select participation</button>
    <button onClick={() => onSelect({ kind: 'project', id: '10' })} type="button">Select project</button>
  </div>,
}))

const detail = {
  id: 12,
  first_name: 'Jean',
  last_name: 'Dupont',
  birth_date: '1990-03-04',
  email: 'jean@example.test',
  entry_date: '2020-01-02',
  exit_date: null,
  is_active: true,
  current_statuses: [{ id: 1, code: 'ENG', name: 'Chercheur' }],
  superiors: [],
  contract_quotity: '0.500',
  project_quotity: '0.250',
  contribution_quotity: null,
  active_milestones_count: 3,
}
const statuses = [
  { id: 1, type: { id: 1, code: 'ENG', name: 'Chercheur' }, start_date: '2024-01-01', end_date: null, contractuality: { code: 'c', label: 'Contractuel' }, is_active: true },
  { id: 2, type: { id: 2, code: 'DOC', name: 'Doctorant' }, start_date: '2020-01-01', end_date: '2023-12-31', contractuality: { code: 'c', label: 'Contractuel' }, is_active: false },
]
const hierarchy = {
  superiors: [
    { id: 1, employee: { id: 3, first_name: 'Marie', last_name: 'Martin' }, start_date: '2023-09-01', end_date: null, is_active: true },
    { id: 2, employee: { id: 4, first_name: 'Ancien', last_name: 'Chef' }, start_date: '2020-01-01', end_date: '2023-08-31', is_active: false },
  ],
  subordinates: [{ id: 3, employee: { id: 5, first_name: 'Claire', last_name: 'Durand' }, start_date: '2020-01-01', end_date: '2022-01-01', is_active: false }],
}
const genericInfo = [{ id: 7, type: { id: 8, name: 'Téléphone', icon: 'style:fas,icon:phone' }, value: '01 02 03 04 05' }]
const projects = [
  { id: 1, project: { id: 10, name: 'Projet Atlas', start_date: '2023-01-01', end_date: null }, role: { code: 'l', label: 'Responsable' }, start_date: '2024-01-01', end_date: null, quotity: '0.250', is_active: true },
  { id: 2, project: { id: 11, name: 'Projet passé', start_date: '2020-01-01', end_date: '2021-01-01' }, role: { code: 'p', label: 'Participant' }, start_date: '2020-01-01', end_date: '2021-01-01', quotity: '0.100', is_active: false },
]
const projectWorkload = { range: { start: '2026-06-20', end: '2027-06-20' }, segments: [{ start: '2026-06-20', end: '2027-06-20', total_quotity: '0.250', projects: [{ id: 10, name: 'Projet Atlas', quotity: '0.250', can_view: false }] }] }
const milestones = [
  {
    id: 20, name: 'Rapport budget', desc: 'Préparer le rapport complet.', start_date: null, end_date: '2026-09-18', status: false, type: 'q', quotity: '0.650', display_state: 'overdue', days_to_due: -2, work_kind: 'milestone',
    project: { id: 10, name: 'Projet Atlas', can_view: false },
    employees: [
      { id: 12, first_name: 'Jean', last_name: 'Dupont', can_view: true },
      { id: 99, first_name: 'Personne', last_name: 'Contextuelle', can_view: false },
    ],
  },
  { id: 21, name: 'Préparer atelier', desc: null, start_date: '2026-09-19', end_date: '2026-09-22', status: false, type: 'o', quotity: '0.000', display_state: 'due_soon', days_to_due: 2, work_kind: 'task', project: { id: 11, name: 'Projet Beta', can_view: true }, employees: [] },
  { id: 22, name: 'Suivi continu', desc: null, start_date: '2026-09-01', end_date: null, status: false, type: 'o', quotity: '0.000', display_state: 'in_progress', days_to_due: null, work_kind: 'task', project: { id: 10, name: 'Projet Atlas', can_view: false }, employees: [] },
  { id: 23, name: 'Tâche future', desc: null, start_date: '2026-10-01', end_date: null, status: false, type: 'o', quotity: '0.000', display_state: 'planned', days_to_due: null, work_kind: 'task', project: { id: 10, name: 'Projet Atlas', can_view: false }, employees: [] },
  { id: 24, name: 'Jalon terminé', desc: null, start_date: null, end_date: '2026-08-01', status: true, type: 'q', quotity: '1.000', display_state: 'completed', days_to_due: -50, work_kind: 'milestone', project: { id: 10, name: 'Projet Atlas', can_view: false }, employees: [] },
]

type Payloads = { detail?: unknown; statuses?: unknown; hierarchy?: unknown; genericInfo?: unknown; projects?: unknown; milestones?: unknown | (() => Response); milestonePatchError?: boolean; workload?: unknown; contracts?: unknown; contributions?: unknown; contributionWorkload?: unknown; budgets?: unknown; calendar?: unknown; calendarFilters?: unknown }
function mockApi(payloads: Payloads = {}) {
  const workState = Array.isArray(payloads.milestones) ? structuredClone(payloads.milestones) : structuredClone(milestones)
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input), method = init?.method ?? 'GET'
    if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
    if (url === '/api/v1/notes/employee/12/') return jsonResponse({ capabilities: { can_add: false }, items: [] })
    if (url.startsWith('/api/v1/reports/employee/')) return jsonResponse({ templates: [{ id: 9, name: 'Rapport employé' }] })
    if (url.endsWith('/statuses/')) return jsonResponse(payloads.statuses ?? statuses)
    if (url.endsWith('/hierarchy/')) return jsonResponse(payloads.hierarchy ?? hierarchy)
    if (url.endsWith('/generic-info/')) return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, items: payloads.genericInfo ?? genericInfo })
    if (/\/api\/v1\/planning\/items\/\d+\/dependencies\/$/.test(url)) return jsonResponse({ can_add: true, predecessors: [], successors: [] })
    if (/\/milestones\/\d+\/$/.test(url) && method === 'PATCH') {
      if (payloads.milestonePatchError) return jsonResponse({ desc: ['Modification refusée'] }, 400)
      const id = Number(url.match(/\/milestones\/(\d+)\/$/)?.[1])
      const index = workState.findIndex((item: { id: number }) => item.id === id)
      const body = JSON.parse(String(init?.body))
      const saved = { ...workState[index], ...body }
      workState[index] = saved
      return jsonResponse(saved)
    }
    if (url.endsWith('/milestones/')) {
      const payload = Array.isArray(payloads.milestones) || payloads.milestones === undefined ? workState : payloads.milestones
      if (typeof payload === 'function') return payload()
      return payload instanceof Response ? payload : jsonResponse(payload)
    }
    if (url.endsWith('/project-participations/')) return jsonResponse(payloads.projects ?? projects)
    if (url.includes('/project-workload/')) return jsonResponse(payloads.workload ?? projectWorkload)
    if (url.includes('/contribution-workload/')) return jsonResponse(payloads.contributionWorkload ?? { range: { start: '2026-06-20', end: '2027-06-20' }, segments: [] })
    if (url.endsWith('/contributions/')) return jsonResponse(payloads.contributions ?? [])
    if (url.endsWith('/budgets/')) return jsonResponse(payloads.budgets ?? [])
    if (url.endsWith('/contracts/capabilities/')) return jsonResponse({ can_add: false, can_change: false, can_delete: false })
    if (url.endsWith('/contracts/')) return jsonResponse(payloads.contracts ?? [])
    if (url.includes('/calendar/filters/')) return jsonResponse(payloads.calendarFilters ?? [])
    if (url.includes('/calendar/')) return jsonResponse(payloads.calendar ?? [])
    if (/\/api\/v1\/employees\/\d+\/$/.test(url)) return jsonResponse(payloads.detail ?? detail)
    throw new Error(`Unexpected URL ${url}`)
  })
}

function renderAt(id = 12, panel = '') {
  window.history.pushState({}, '', `/app/employees/${id}${panel ? `/${panel}` : ''}`)
  return render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
}

describe('Employee R2 detail', () => {
  it('uses the shared entity menu for independent exports without an Edit action', async () => {
    mockApi({ detail: { ...detail, capabilities: { can_export_word: true, can_export_pdf: false } } })
    renderAt()
    const user = userEvent.setup()
    const trigger = await screen.findByRole('button', { name: 'Actions pour Jean Dupont' }, { timeout: 5000 })
    await user.click(trigger)
    expect(await screen.findByRole('menuitem', { name: 'Export Word' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: /Modifier/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Export PDF' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('menuitem', { name: 'Export Word' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('Exporter l’employé — Export Word')
    expect(within(dialog).getByLabelText('Du')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Au')).toBeInTheDocument()
  })

  it('shows no Employee menu without exports and shows PDF alone when permitted', async () => {
    mockApi({ detail: { ...detail, capabilities: { can_export_word: false, can_export_pdf: true } } })
    renderAt()
    const trigger = await screen.findByRole('button', { name: 'Actions pour Jean Dupont' })
    await userEvent.setup().click(trigger)
    expect(await screen.findByRole('menuitem', { name: 'Export PDF' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Export Word' })).not.toBeInTheDocument()
  })

  it('omits the Employee entity menu when no header action is available', async () => {
    mockApi({ detail: { ...detail, capabilities: { can_export_word: false, can_export_pdf: false } } })
    renderAt()
    await screen.findByRole('heading', { name: 'Jean Dupont' })
    expect(screen.queryByRole('button', { name: 'Actions pour Jean Dupont' })).not.toBeInTheDocument()
  })
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    Object.defineProperty(window.navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockResolvedValue(undefined) } })
    localStorage.clear()
  })

  it('renders Overview and does not load Project-domain resources', async () => {
    const user = userEvent.setup()
    const writeText = vi.spyOn(navigator.clipboard, 'writeText')
    const fetchMock = mockApi()
    renderAt()

    expect(await screen.findByRole('heading', { name: 'Jean Dupont', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vue d’ensemble' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('heading', { name: 'Vue d’ensemble' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Informations générales', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'jean@example.test' })).toHaveAttribute('href', 'mailto:jean@example.test')
    expect(await screen.findByText('Téléphone')).toBeInTheDocument()
    const contractIndicator = screen.getByText('Quotité contrats').closest('div')!
    expect(contractIndicator).toHaveTextContent(/50\s*%/)
    expect(screen.getByText('3')).toBeInTheDocument()

    const emailRow = screen.getByRole('link', { name: 'jean@example.test' }).closest('dd')!
    await user.click(within(emailRow).getByRole('button', { name: 'Copier la valeur' }))
    expect(writeText).toHaveBeenCalledWith('jean@example.test')
    expect(within(emailRow).getByRole('button', { name: 'Copié' })).toBeInTheDocument()

    expect(screen.queryByText('Doctorant')).not.toBeInTheDocument()
    const statusesSection = screen.getByRole('heading', { name: 'Statuts' }).closest('section')!
    await user.click(within(statusesSection).getByRole('button', { name: '↳ 1 précédent' }))
    expect(screen.getByText('Doctorant')).toBeInTheDocument()
    await user.click(within(statusesSection).getByRole('button', { name: '↟ Réduire' }))
    expect(screen.queryByText('Doctorant')).not.toBeInTheDocument()
    expect(within(statusesSection).getByRole('button', { name: '↳ 1 précédent' })).toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Marie Martin' })).toHaveAttribute('href', '/app/employees/3')
    expect(screen.queryByRole('link', { name: 'Ancien Chef' })).not.toBeInTheDocument()
    const superiors = screen.getByRole('heading', { name: 'Supérieurs' }).closest('div')!
    await user.click(within(superiors).getByRole('button', { name: '↳ 1 précédent' }))
    expect(screen.getByRole('link', { name: 'Ancien Chef' })).toHaveAttribute('href', '/app/employees/4')
    expect(within(superiors).getByRole('button', { name: '↟ Réduire' })).toBeInTheDocument()

    const urls = fetchMock.mock.calls.map(([input]) => String(input))
    expect(urls.some((url) => url.endsWith('/milestones/'))).toBe(false)
    expect(urls.some((url) => url.endsWith('/project-participations/'))).toBe(false)
    expect(urls.some((url) => url.includes('/project-workload/'))).toBe(false)
    expect(urls.some((url) => url.endsWith('/contracts/'))).toBe(false)
    expect(screen.queryByRole('heading', { name: 'Jalons et tâches' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Profil temporel de charge projet' })).not.toBeInTheDocument()
  })

  it('shows the single Overview section directly even with a stale collapse preference', async () => {
    localStorage.setItem('labsmanager:employee:general-open', 'false')
    mockApi()
    renderAt(12)

    expect(await screen.findByRole('heading', { name: 'Informations générales', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Informations' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Informations générales/ })).not.toBeInTheDocument()
  })

  it('persists the milestones collapse by section type across employees', async () => {
    const user = userEvent.setup()
    mockApi()
    const view = renderAt(12, 'projects')
    const collapse = await screen.findByRole('button', { name: 'Replier Jalons et tâches' })

    await screen.findByRole('button', { name: 'Ouvrir le détail de Rapport budget' })
    await user.click(collapse)
    expect(localStorage.getItem('labsmanager:employee:milestones-open')).toBe('false')
    expect(localStorage.getItem('labsmanager:employee:general-open')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Ouvrir le détail de Rapport budget' })).not.toBeInTheDocument()

    view.unmount()
    renderAt(13, 'projects')
    expect(await screen.findByRole('button', { name: 'Développer Jalons et tâches' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('renders the principal Overview empty states without inventing actions', async () => {
    mockApi({ statuses: [], hierarchy: { superiors: [], subordinates: [] }, genericInfo: [], milestones: [], projects: [] })
    renderAt()

    expect(await screen.findByText('Aucune information complémentaire.')).toBeInTheDocument()
    expect(screen.getAllByText('Aucun actuellement')).toHaveLength(3)
    expect(screen.queryByRole('button', { name: /précédent/ })).not.toBeInTheDocument()
  })

  it('navigates locally with the same Employee id and opens shared Notes', async () => {
    const user = userEvent.setup()
    mockApi()
    renderAt()

    const navigation = await screen.findByRole('navigation', { name: 'Navigation de la fiche Employee' })
    const projectsLink = within(navigation).getByRole('link', { name: 'Projets' })
    expect(projectsLink).toHaveAttribute('href', '/app/employees/12/projects')
    await user.click(projectsLink)
    expect(window.location.pathname).toBe('/app/employees/12/projects')
    expect(projectsLink).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByRole('heading', { name: 'Jalons et tâches' })).toBeInTheDocument()

    const contractsLink = within(navigation).getByRole('link', { name: 'Contrats' })
    await user.click(contractsLink)
    expect(window.location.pathname).toBe('/app/employees/12/contracts')
    expect(contractsLink).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('Aucun contrat visible.')).toBeInTheDocument()

    const fundingLink = within(navigation).getByRole('link', { name: 'Financement' })
    expect(fundingLink).toHaveAttribute('href', '/app/employees/12/funding')
    await user.click(fundingLink)
    expect(window.location.pathname).toBe('/app/employees/12/funding')
    expect(fundingLink).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByRole('heading', { name: 'Contributions', level: 2 })).toBeInTheDocument()

    const leavesLink = within(navigation).getByRole('link', { name: 'Congés' })
    await user.click(leavesLink)
    expect(window.location.pathname).toBe('/app/employees/12/leaves')
    expect(leavesLink).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('Aucune absence dans cette période.')).toBeInTheDocument()

    const notesLink = within(navigation).getByRole('link', { name: 'Notes' })
    await user.click(notesLink)
    expect(window.location.pathname).toBe('/app/employees/12/notes')
    expect(notesLink).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('Aucune note.')).toBeInTheDocument()
  })

  it('loads milestones, workload and participations only on Projects', async () => {
    const fetchMock = mockApi()
    renderAt(12, 'projects')

    expect(await screen.findByRole('button', { name: 'Ouvrir le détail de Rapport budget' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Profil temporel de charge projet' })).toBeInTheDocument()
    expect(screen.getByText('Projet passé')).toBeInTheDocument()
    expect(screen.getByText('Responsable')).toBeInTheDocument()
    const urls = fetchMock.mock.calls.map(([input]) => String(input))
    expect(urls.some((url) => url.endsWith('/milestones/'))).toBe(true)
    expect(urls.some((url) => url.endsWith('/project-participations/'))).toBe(true)
    expect(urls.some((url) => url.includes('/project-workload/'))).toBe(true)
  })

  it('links only independently visible Projects in the participation list', async () => {
    const user = userEvent.setup()
    mockApi({ projects: projects.map((item) => ({ ...item, project: { ...item.project, can_view: item.project.id === 10 } })) })
    renderAt(12, 'projects')

    const participations = await screen.findByRole('region', { name: 'Participations aux projets' })
    expect(within(participations).getByRole('link', { name: 'Projet Atlas' })).toHaveAttribute('href', '/app/projects/10')
    expect(within(participations).queryByRole('link', { name: 'Projet passé' })).not.toBeInTheDocument()
    expect(within(participations).getByText('Projet passé')).toBeInTheDocument()
    expect(within(participations).getByText('Responsable')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Gantt' }))
    expect(await screen.findByTestId('employee-gantt')).toBeInTheDocument()
  })

  it('switches to Gantt with Calendar filters without refetching Employee business data', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({
      calendarFilters: [{ id: 'sample-zone', title: 'Zone', type: 'select', source: 'sample', choices: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }], default: 'a' }],
      calendar: [{ id: 'calendar-one', title: 'Event', start: '2026-09-01', end: '2026-09-02', source: 'sample', kind: 'event', all_day: true, color: null, description: null, display: 'auto', metadata: {} }],
    })
    renderAt(12, 'projects')
    expect(await screen.findByRole('button', { name: 'Ouvrir le détail de Rapport budget' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Gantt' }))
    expect(await screen.findByTestId('employee-gantt')).toHaveTextContent('project:10,participation:1,work:20')
    expect(screen.getByTestId('employee-gantt')).toHaveTextContent('calendar-one')
    await user.selectOptions(screen.getByLabelText('Zone'), 'b')
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes('sample-zone=b'))).toBe(true))
    expect(screen.getByTestId('employee-gantt')).toHaveTextContent('work:20')
    await user.click(screen.getByRole('button', { name: '1 an' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input), window.location.origin)
      return url.pathname.endsWith('/calendar/') && Number(url.searchParams.get('to')?.slice(0, 4)) - Number(url.searchParams.get('from')?.slice(0, 4)) === 1
    })).toBe(true))
    await user.click(screen.getByRole('button', { name: '2 ans' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => {
      const url = new URL(String(input), window.location.origin)
      return url.pathname.endsWith('/calendar/') && Number(url.searchParams.get('to')?.slice(0, 4)) - Number(url.searchParams.get('from')?.slice(0, 4)) === 2
    })).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Select participation' }))
    await user.click(screen.getByRole('button', { name: 'Select project' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(window.location.pathname).toBe('/app/employees/12/projects')
    await user.click(await screen.findByRole('button', { name: 'Open work' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Rapport budget')
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Fermer' }))
    await user.click(screen.getByRole('button', { name: 'Liste' }))
    expect(screen.getByRole('button', { name: 'Ouvrir le détail de Rapport budget' })).toBeInTheDocument()
    const calendarCalls = fetchMock.mock.calls.filter(([input]) => String(input).includes('/calendar/?')).length
    await user.click(screen.getByRole('button', { name: 'Gantt' }))
    expect(screen.getByLabelText('Zone')).toHaveValue('b')
    expect(fetchMock.mock.calls.filter(([input]) => String(input).includes('/calendar/?'))).toHaveLength(calendarCalls)
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/milestones/'))).toHaveLength(1)
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/project-participations/'))).toHaveLength(1)
  })

  it('keeps both Project sections collapsible after routing', async () => {
    const user = userEvent.setup()
    mockApi()
    renderAt(12, 'projects')

    const collapse = await screen.findByRole('button', { name: 'Replier Participations aux projets' })
    await user.click(collapse)
    expect(localStorage.getItem('labsmanager:employee:project-participations-open')).toBe('false')
    expect(screen.queryByRole('heading', { name: 'Profil temporel de charge projet' })).not.toBeInTheDocument()
  })

  it('groups milestones, limits progress to quantifiable items and opens the detail Sheet', async () => {
    const user = userEvent.setup()
    mockApi()
    renderAt(12, 'projects')

    expect(await screen.findByRole('heading', { name: /Jalons et tâches/ })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'En retard · 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Échéance proche · 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'En cours · 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Planifiés · 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Terminés · 1' })).toBeInTheDocument()
    expect(screen.queryByText('Jalon terminé')).not.toBeInTheDocument()
    expect(screen.getAllByRole('progressbar')).toHaveLength(1)
    expect(within(screen.getByRole('button', { name: 'Ouvrir le détail de Rapport budget' })).getByText(/Jean Dupont, Personne Contextuelle/)).toBeInTheDocument()
    expect(within(screen.getByRole('button', { name: 'Ouvrir le détail de Préparer atelier' })).queryByRole('progressbar')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ouvrir le détail de Rapport budget' }))
    const sheet = await screen.findByRole('dialog')
    expect(within(sheet).getByRole('heading', { name: 'Rapport budget' })).toBeInTheDocument()
    expect(within(sheet).getByText('Préparer le rapport complet.')).toBeInTheDocument()
    expect(within(sheet).getByText('Projet Atlas')).toBeInTheDocument()
    expect(within(sheet).getByRole('link', { name: 'Jean Dupont' })).toHaveAttribute('href', '/app/employees/12')
    expect(within(sheet).getByText('Personne Contextuelle')).toBeInTheDocument()
    expect(within(sheet).queryByRole('link', { name: 'Personne Contextuelle' })).not.toBeInTheDocument()
    expect(within(sheet).getByRole('progressbar')).toHaveValue(65)
    expect(within(sheet).queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Créer|Supprimer/ })).not.toBeInTheDocument()

    await user.click(within(sheet).getByRole('button', { name: 'Fermer' }))
    const task = screen.getByRole('button', { name: 'Ouvrir le détail de Préparer atelier' })
    task.focus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('heading', { name: 'Préparer atelier' })).toBeInTheDocument()
  })

  it('edits only Employee Planning progress, status and description, then refreshes list and Gantt', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({ milestones: milestones.map((item) => ({ ...item, can_change: item.id === 20 })) })
    renderAt(12, 'projects')
    await user.click(await screen.findByRole('button', { name: 'Ouvrir le détail de Rapport budget' }, { timeout: 5000 }))
    const sheet = await screen.findByRole('dialog')
    expect(within(sheet).getByText('Préparer le rapport complet.')).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Modifier' }))
    expect(within(sheet).getByRole('textbox', { name: 'Description' })).toHaveValue('Préparer le rapport complet.')
    expect(within(sheet).getByRole('spinbutton', { name: 'Progression (%)' })).toHaveValue(65)
    expect(within(sheet).getByRole('checkbox', { name: 'Terminé' })).not.toBeChecked()
    expect(within(sheet).queryByRole('textbox', { name: /Nom|Projet/ })).not.toBeInTheDocument()
    expect(within(sheet).queryByRole('button', { name: /Ajouter un prédécesseur|Ajouter un successeur|Supprimer/ })).not.toBeInTheDocument()
    await user.clear(within(sheet).getByRole('textbox', { name: 'Description' }))
    await user.type(within(sheet).getByRole('textbox', { name: 'Description' }), 'Brouillon')
    await user.click(within(sheet).getByRole('button', { name: 'Annuler' }))
    expect(within(sheet).getByText('Préparer le rapport complet.')).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Modifier' }))
    await user.clear(within(sheet).getByRole('textbox', { name: 'Description' }))
    await user.type(within(sheet).getByRole('textbox', { name: 'Description' }), 'Terminé côté Employee')
    await user.clear(within(sheet).getByRole('spinbutton', { name: 'Progression (%)' }))
    await user.type(within(sheet).getByRole('spinbutton', { name: 'Progression (%)' }), '75')
    await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(within(sheet).getByText('Terminé côté Employee')).toBeInTheDocument())
    expect(within(sheet).queryByRole('textbox', { name: 'Description' })).not.toBeInTheDocument()
    const patch = fetchMock.mock.calls.find(([input, init]) => String(input).endsWith('/milestones/20/') && init?.method === 'PATCH')
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ desc: 'Terminé côté Employee', quotity: '0.750', status: false })
    await waitFor(() => expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/milestones/')).length).toBe(2))
    await user.click(within(sheet).getByRole('button', { name: 'Fermer' }))
    expect(within(screen.getByRole('button', { name: 'Ouvrir le détail de Rapport budget' })).getByRole('progressbar')).toHaveValue(75)
    await user.click(screen.getByRole('button', { name: 'Gantt' }))
    await user.click(await screen.findByRole('button', { name: 'Open work' }, { timeout: 5000 }))
    expect(within(await screen.findByRole('dialog')).getByText('Terminé côté Employee')).toBeInTheDocument()
  })

  it('uses per-item capability in Employee Planning and retains the Sheet after a PATCH error', async () => {
    const user = userEvent.setup()
    mockApi({ milestones: milestones.map((item) => ({ ...item, can_change: item.id === 20 })), milestonePatchError: true })
    renderAt(12, 'projects')
    await user.click(await screen.findByRole('button', { name: 'Ouvrir le détail de Préparer atelier' }))
    expect(within(await screen.findByRole('dialog')).queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Fermer' }))
    await user.click(screen.getByRole('button', { name: 'Ouvrir le détail de Rapport budget' }))
    const sheet = await screen.findByRole('dialog')
    await user.click(within(sheet).getByRole('button', { name: 'Modifier' }))
    await user.click(within(sheet).getByRole('button', { name: 'Enregistrer' }))
    expect(await within(sheet).findByText('Modification refusée')).toBeInTheDocument()
    expect(within(sheet).getByRole('textbox', { name: 'Description' })).toBeInTheDocument()
  })

  it('expands completed milestones on demand', async () => {
    const user = userEvent.setup()
    mockApi()
    renderAt(12, 'projects')

    await user.click(await screen.findByRole('button', { name: /Terminés · 1/ }))

    expect(screen.getByRole('button', { name: 'Ouvrir le détail de Jalon terminé' })).toBeInTheDocument()
    expect(screen.getAllByRole('progressbar')).toHaveLength(2)
  })

  it('retries a local milestone error without hiding the Employee detail', async () => {
    const user = userEvent.setup()
    let failed = false
    mockApi({ milestones: () => {
      if (!failed) { failed = true; return jsonResponse({}, 500) }
      return jsonResponse([])
    } })
    renderAt(12, 'projects')

    expect(await screen.findByRole('heading', { name: 'Jean Dupont', level: 1 })).toBeInTheDocument()
    const tracker = screen.getByRole('heading', { name: 'Jalons et tâches' }).closest('section')!
    await user.click(await within(tracker).findByRole('button', { name: 'Réessayer' }))
    expect(await within(tracker).findByText('Aucun jalon ou tâche assigné.')).toBeInTheDocument()
  })

  it('shows an indistinguishable 404 state without retry', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input) === '/api/v1/me/' ? jsonResponse(authenticatedUser) : jsonResponse({}, 404))
    renderAt(999999)

    expect(await screen.findByRole('alert')).toHaveTextContent('Employee introuvable ou inaccessible.')
    expect(screen.queryByRole('button', { name: 'Réessayer' })).not.toBeInTheDocument()
  })

  it('keeps Employee loading and forbidden states at layout level', async () => {
    let resolveEmployee!: (response: Response) => void
    const employeeResponse = new Promise<Response>((resolve) => { resolveEmployee = resolve })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input) === '/api/v1/me/' ? jsonResponse(authenticatedUser) : employeeResponse)
    renderAt(12, 'projects')

    expect(await screen.findByText('Chargement de l’employé…')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Navigation de la fiche Employee' })).not.toBeInTheDocument()
    resolveEmployee(jsonResponse({}, 403))
    expect(await screen.findByRole('alert')).toHaveTextContent('Accès interdit à cette fiche Employee.')
    expect(screen.queryByRole('heading', { name: 'Projets' })).not.toBeInTheDocument()
  })

  it('retries a primary network error', async () => {
    let failed = false
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/me/') return jsonResponse(authenticatedUser)
      if (/\/api\/v1\/employees\/\d+\/$/.test(url) && !failed) { failed = true; throw new TypeError('offline') }
      if (/\/api\/v1\/employees\/\d+\/$/.test(url)) return jsonResponse(detail)
      if (url.endsWith('/generic-info/')) return jsonResponse({ capabilities: { can_add: false, can_change: false, can_delete: false }, items: [] })
      if (url.endsWith('/statuses/')) return jsonResponse([])
      if (url.endsWith('/hierarchy/')) return jsonResponse({ superiors: [], subordinates: [] })
      if (url.includes('/project-workload/')) return jsonResponse(projectWorkload)
      return jsonResponse([])
    })
    const user = userEvent.setup()
    renderAt()

    await user.click(await screen.findByRole('button', { name: 'Réessayer' }))
    expect(await screen.findByRole('heading', { name: 'Jean Dupont', level: 1 })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Aucune information complémentaire.')).toBeInTheDocument())
  })
})
