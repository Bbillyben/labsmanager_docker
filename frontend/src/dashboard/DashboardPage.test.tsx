import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { MemoryRouter } from 'react-router-dom'
import { PrintProvider } from '../print/PrintProvider'
import type { DashboardSummary, DashboardDetail, DashboardCatalog } from '../api/dashboards'

const api = vi.hoisted(() => ({
  listDashboards: vi.fn(), getDashboard: vi.fn(), getProjectDashboard: vi.fn(), getDashboardCatalog: vi.fn(), createDashboard: vi.fn(),
  renameDashboard: vi.fn(), deleteDashboard: vi.fn(), duplicateDashboard: vi.fn(), setDefaultDashboard: vi.fn(),
  reorderDashboards: vi.fn(), addDashboardWidget: vi.fn(), updateDashboardWidget: vi.fn(),
  deleteDashboardWidget: vi.fn(), saveDashboardLayout: vi.fn(),
}))
vi.mock('../api/dashboards', () => api)
vi.mock('./DashboardGrid', () => ({ DashboardGrid: ({ widgets, mode, onLayout, onConfigure }: { widgets: { id: string; definition_key: string }[]; mode: string; onLayout: (rows: unknown[]) => void; onConfigure: (item: unknown) => void }) =>
  <div data-testid="dashboard-grid" data-editing={mode === 'edit'}>{widgets.map((item) => <span key={item.id}>{item.definition_key}</span>)}<button onClick={() => onLayout([{ id: widgets[0].id, x: 2, y: 1, width: 4, height: 3, logical_order: 0 }])}>Move mock widget</button><button onClick={() => onConfigure(widgets[0])}>Configure mock widget</button></div> }))

import { DashboardPage } from './DashboardPage'

const summaries: DashboardSummary[] = [
  { id: 1, name: 'First', icon: '', is_default: true, position: 0, scope: 'user' },
  { id: 2, name: 'Second', icon: '', is_default: false, position: 1, scope: 'user' },
]
const widget = { id: '00000000-0000-4000-8000-000000000001', definition_key: 'core.note', source_key: 'core.note', renderer_key: 'empty', title: '', config: {}, x: 0, y: 0, width: 4, height: 3, logical_order: 0, available: true, data: {}, error: false }
const catalog: DashboardCatalog = { scope: 'user', renderers: { empty: { label: 'Text', config_fields: {} }, 'compact-list': { label: 'List', config_fields: {} }, kpi: { label: 'Indicator', config_fields: {} }, 'alert-list': { label: 'Alerts', config_fields: {} }, 'progress-list': { label: 'Progress', config_fields: {} } }, sources: [
  { key: 'core.note', label: 'Note', description: 'Text', category: 'General', compatible_renderers: ['empty'], default_renderer: 'empty', allow_multiple: true, config_fields: { message: { type: 'string', default: '' } } },
  { key: 'core.links', label: 'Quick links', description: 'Links', category: 'General', compatible_renderers: ['compact-list'], default_renderer: 'compact-list', allow_multiple: false, config_fields: {} },
  { key: 'core.projects', label: 'Visible projects', description: 'Projects', category: 'Projects', compatible_renderers: ['kpi', 'compact-list'], default_renderer: 'kpi', allow_multiple: true, config_fields: { active_only: { type: 'boolean', default: false }, limit: { type: 'integer', default: 5, min: 1, max: 20 } } },
  { key: 'core.milestones', label: 'Milestones', description: 'Project milestones', category: 'Projects', compatible_renderers: ['kpi', 'compact-list', 'alert-list'], default_renderer: 'compact-list', allow_multiple: true, config_fields: { scope: { type: 'choice', choices: ['all_visible', 'mine'], default: 'all_visible' } } },
  { key: 'core.funds', label: 'Funds', description: 'Funding', category: 'Finance', compatible_renderers: ['kpi', 'compact-list', 'alert-list', 'progress-list'], default_renderer: 'progress-list', allow_multiple: true, config_fields: { ending_within_days: { type: 'choice', choices: ['0', '30'], default: '0' } } },
  { key: 'core.contracts', label: 'Contracts', description: 'Contracts', category: 'Administration', compatible_renderers: ['kpi', 'compact-list', 'alert-list'], default_renderer: 'alert-list', allow_multiple: true, config_fields: {} },
  { key: 'core.employees', label: 'Employees', description: 'People', category: 'HR', compatible_renderers: ['kpi', 'compact-list', 'alert-list'], default_renderer: 'kpi', allow_multiple: true, config_fields: {} },
  { key: 'core.leaves', label: 'Leaves', description: 'Absences', category: 'HR', compatible_renderers: ['kpi', 'compact-list'], default_renderer: 'compact-list', allow_multiple: true, config_fields: {} },
  { key: 'core.tasks', label: 'Tasks', description: 'Work', category: 'Work', compatible_renderers: ['kpi', 'compact-list', 'alert-list'], default_renderer: 'compact-list', allow_multiple: true, config_fields: {} },
], definitions: [
  { key: 'core.note', title: 'Note', category: 'General', renderer_key: 'empty', source_key: 'core.note', supported_scopes: ['user'], default_size: [4, 3], min_size: [2, 2], max_size: [12, 8], allow_multiple: true, printable: true, icon: 'LayoutDashboard', config_fields: { message: 'string' } },
  { key: 'core.quick-links', title: 'Quick links', category: 'General', renderer_key: 'compact-list', source_key: 'core.links', supported_scopes: ['user'], default_size: [4, 3], min_size: [2, 2], max_size: [12, 8], allow_multiple: false, printable: true, icon: 'LayoutDashboard', config_fields: {} },
  { key: 'core.projects-count', title: 'Visible projects', category: 'Projects', renderer_key: 'kpi', source_key: 'core.projects', supported_scopes: ['user'], default_size: [4, 3], min_size: [2, 2], max_size: [12, 8], allow_multiple: true, printable: true, icon: 'LayoutDashboard', config_fields: {} },
] }

function setup(items = summaries, firstWidgets = [widget]) {
  let current = items
  api.listDashboards.mockImplementation(async () => current)
  api.getDashboard.mockImplementation(async (id: number): Promise<DashboardDetail> => ({ ...current.find((item) => item.id === id)!, widgets: id === 1 ? firstWidgets : [] }))
  api.getDashboardCatalog.mockResolvedValue(catalog)
  api.createDashboard.mockImplementation(async (name: string, template: string) => {
    expect(['employee', 'leader', 'lab-manager', 'blank']).toContain(template)
    const added = { id: 3, name, icon: '', is_default: !current.length, position: current.length, scope: 'user' as const }
    current = [...current, added]
    return added
  })
  api.setDefaultDashboard.mockImplementation(async (id: number) => { current = current.map((item) => ({ ...item, is_default: item.id === id })); return current.find((item) => item.id === id) })
  api.reorderDashboards.mockImplementation(async (ids: number[]) => { current = ids.map((id, index) => ({ ...current.find((item) => item.id === id)!, position: index })); return current })
  api.duplicateDashboard.mockImplementation(async () => { const item = { id: 3, name: 'First (copy)', icon: '', is_default: false, position: 2, scope: 'user' as const }; current = [...current, item]; return item })
  api.renameDashboard.mockImplementation(async (id: number, name: string) => { current = current.map((item) => item.id === id ? { ...item, name } : item); return current.find((item) => item.id === id) })
  api.deleteDashboard.mockImplementation(async (id: number) => { current = current.filter((item) => item.id !== id) })
  api.saveDashboardLayout.mockResolvedValue({})
  api.addDashboardWidget.mockResolvedValue(widget)
  render(<I18nProvider><MemoryRouter initialEntries={['/dashboard']}><PrintProvider><DashboardPage /></PrintProvider></MemoryRouter></I18nProvider>)
}

beforeEach(() => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  Object.values(api).forEach((mock) => mock.mockReset())
})

describe('Dashboard foundation', () => {
  it('reuses the grid and editor for a Project without personal dashboard management', async () => {
    const project = { ...summaries[0], id: 9, name: 'Project dashboard', scope: 'project' as const, project_id: 42, widgets: [widget] }
    api.getProjectDashboard.mockResolvedValue(project)
    api.getDashboardCatalog.mockResolvedValue({ ...catalog, scope: 'project', project_options: [{ id: 42, name: 'Visible project' }],
      sources: [{ ...catalog.sources[2], config_fields: { project_scope: { type: 'choice', choices: ['context', 'all_visible', 'specific_project'] }, project_id: { type: 'project' } } }] })
    api.saveDashboardLayout.mockResolvedValue({})
    render(<I18nProvider><MemoryRouter initialEntries={['/projects/42/dashboard']}><PrintProvider><DashboardPage projectId="42" /></PrintProvider></MemoryRouter></I18nProvider>)
    expect(await screen.findByTestId('dashboard-grid')).toBeInTheDocument()
    expect(api.getProjectDashboard).toHaveBeenCalledWith('42')
    expect(api.getDashboardCatalog).toHaveBeenCalledWith('42')
    expect(screen.queryByRole('combobox', { name: 'Tableau de bord' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dupliquer' })).not.toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    await user.click(screen.getByRole('button', { name: 'Move mock widget' }))
    await user.click(screen.getByRole('button', { name: 'Enregistrer la disposition' }))
    await waitFor(() => expect(api.saveDashboardLayout).toHaveBeenCalledWith(9, expect.any(Array)))
    await user.click(screen.getByRole('button', { name: 'Projets visibles' }))
    await user.selectOptions(screen.getByLabelText('Périmètre projet'), 'specific_project')
    await user.selectOptions(screen.getByLabelText('Projet'), '42')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.addDashboardWidget).toHaveBeenCalledWith(9, 'core.projects', 'kpi', '', { project_scope: 'specific_project', project_id: 42 }))
  })
  it('offers all four templates without choosing one for a new user', async () => {
    setup([])
    expect(await screen.findByText('Choisissez votre tableau de bord initial')).toBeInTheDocument()
    expect(screen.getAllByRole('radio')).toHaveLength(4)
    expect(screen.getAllByRole('radio').every((radio) => !(radio as HTMLInputElement).checked)).toBe(true)
    expect(api.createDashboard).not.toHaveBeenCalled()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Nom du tableau de bord'), 'My start')
    await user.click(screen.getByRole('radio', { name: /Employé/ }))
    await user.click(screen.getByRole('button', { name: 'Créer le tableau de bord' }))
    await waitFor(() => expect(api.createDashboard).toHaveBeenCalledWith('My start', 'employee'))
    expect(await screen.findByRole('combobox', { name: 'Tableau de bord' })).toBeInTheDocument()
  })

  it('switches dashboards and saves one batch layout only in edit mode', async () => {
    setup()
    const user = userEvent.setup()
    expect(await screen.findByTestId('dashboard-grid')).toHaveAttribute('data-editing', 'false')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    expect(screen.getByTestId('dashboard-grid')).toHaveAttribute('data-editing', 'true')
    await user.click(screen.getByRole('button', { name: 'Move mock widget' }))
    await user.click(screen.getByRole('button', { name: 'Enregistrer la disposition' }))
    await waitFor(() => expect(api.saveDashboardLayout).toHaveBeenCalledWith(1, [{ id: widget.id, x: 2, y: 1, width: 4, height: 3, logical_order: 0 }]))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Tableau de bord' }), '2')
    await waitFor(() => expect(api.getDashboard).toHaveBeenCalledWith(2))
    expect(screen.getByText('Aucun widget. Ajoutez-en un en mode personnalisation.')).toBeInTheDocument()
  })

  it('supports default and reorder without inferring permissions', async () => {
    setup()
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Tableau de bord' }), '2')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    await user.click(screen.getByRole('button', { name: 'Définir par défaut' }))
    await waitFor(() => expect(api.setDefaultDashboard).toHaveBeenCalledWith(2))
    await user.click(screen.getByRole('button', { name: 'Monter' }))
    await waitFor(() => expect(api.reorderDashboards).toHaveBeenCalledWith([2, 1]))
  })

  it('renames and duplicates through the management actions', async () => {
    setup()
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    await user.click(screen.getByRole('button', { name: 'Renommer' }))
    const name = screen.getByLabelText('Nom du tableau de bord')
    await user.clear(name)
    await user.type(name, 'Renamed')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.renameDashboard).toHaveBeenCalledWith(1, 'Renamed'))
    await user.click(screen.getByRole('button', { name: 'Dupliquer' }))
    await waitFor(() => expect(api.duplicateDashboard).toHaveBeenCalledWith(1))
    expect(await screen.findByRole('option', { name: 'First (copy)' })).toBeInTheDocument()
  })

  it('confirms deletion and returns to onboarding after the last dashboard', async () => {
    setup([summaries[0]])
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    await user.click(screen.getByRole('button', { name: 'Supprimer le tableau de bord' }))
    expect(api.deleteDashboard).not.toHaveBeenCalled()
    expect(screen.getByText('Supprimer « First » et tous ses widgets ?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(api.deleteDashboard).toHaveBeenCalledWith(1))
    expect(await screen.findByText('Choisissez votre tableau de bord initial')).toBeInTheDocument()
  })

  it('disables a catalogue definition that permits only one instance', async () => {
    setup(summaries, [widget, { ...widget, id: 'quick-1', definition_key: 'core.quick-links', source_key: 'core.links', renderer_key: 'compact-list' }])
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    expect(screen.getByRole('button', { name: 'Liens rapides' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Note' })).toBeEnabled()
  })

  it('searches sources and configures a compatible renderer before adding', async () => {
    setup()
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    await user.type(screen.getByLabelText('Rechercher une source'), 'Visible projects')
    expect(screen.queryByRole('button', { name: 'Note' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Projets visibles' }))
    await user.selectOptions(screen.getByLabelText('Présentation'), 'compact-list')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.addDashboardWidget).toHaveBeenCalledWith(1, 'core.projects', 'compact-list', '', {}))
  })

  it('edits an existing instance with an explicit save and keeps its identity', async () => {
    setup(summaries, [{ ...widget, source_key: 'core.projects', definition_key: 'core.projects-count', renderer_key: 'kpi', config: { active_only: false, limit: 5 } }])
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.click(screen.getByRole('button', { name: 'Configure mock widget' }))
    await user.selectOptions(screen.getByLabelText('Présentation'), 'compact-list')
    await user.type(screen.getByLabelText('Titre personnalisé'), 'My projects')
    await user.click(screen.getByLabelText('Projets actifs uniquement'))
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.updateDashboardWidget).toHaveBeenCalledWith(1, widget.id, 'My projects', { active_only: true, limit: 5 }, 'compact-list'))
  })

  it('groups business sources and generates their configuration without domain-specific forms', async () => {
    setup()
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    await user.click(screen.getByRole('button', { name: 'Personnaliser' }))
    expect(screen.getByRole('heading', { name: 'Finances' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ressources humaines' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Financements visibles' }))
    expect(screen.getByRole('option', { name: 'Liste de progression' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Fin sous'), '30')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.addDashboardWidget).toHaveBeenCalledWith(1, 'core.funds', 'progress-list', '', { ending_within_days: '30' }))
  })

  it('opens central Print with the current dashboard snapshot and no extra data request', async () => {
    setup(summaries, [{ ...widget, data: { message: 'Printable note' } }])
    const user = userEvent.setup()
    await screen.findByTestId('dashboard-grid')
    const reads = api.getDashboard.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Imprimer' }))
    expect(await screen.findByTestId('dashboard-print', {}, { timeout: 5000 })).toHaveTextContent('Printable note')
    expect(api.getDashboard).toHaveBeenCalledTimes(reads)
    expect(screen.getByRole('button', { name: 'Retour' })).toBeInTheDocument()
  })
})
