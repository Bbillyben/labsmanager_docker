import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { CalendarPluginActions, PluginContributionsProvider, PluginContributionSections, PluginEntityActions, PluginEntityTabs, UserPluginActions } from './PluginContributions'
import type { UIContribution, UIEntity } from '../api/uiContributions'
import { loadPluginComponent } from './pluginModuleLoader'

vi.mock('./pluginModuleLoader', () => ({ loadPluginComponent: vi.fn() }))

const contribution = (slug: string, id: string, entity: UIEntity, type: 'action' | 'section', label: string, behavior: UIContribution['behavior'] = null, confirm = false): UIContribution => ({
  id: `plugin:${slug}:${id}`, plugin_slug: slug, slot: `${entity}.detail.${type}s`, type,
  label, icon: null, behavior, confirm, priority: 0,
})

function mount(entity: UIEntity) {
  render(<I18nProvider><PluginContributionsProvider scope={{ entity, objectId: 42 }}>
    <PluginEntityActions label="Entity actions" groups={[]} />
    <PluginContributionSections />
  </PluginContributionsProvider></I18nProvider>)
}

describe('React plugin contributions', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] }) })
  afterEach(() => vi.restoreAllMocks())

  it('adds a contextual Employee tab link without loading its module', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ contributions: [
      { id: 'plugin:demo:employee-tab', plugin_slug: 'demo', local_id: 'employee-tab',
        slot: 'employee.detail.tabs', type: 'tab', label: 'Demo tab', icon: null, behavior: null,
        confirm: false, priority: 0, module: 'main', component: 'EmployeeTab', api_version: 1 },
    ] }))
    render(<I18nProvider><MemoryRouter><PluginContributionsProvider scope={{ entity: 'employee', objectId: 42 }}>
      <PluginEntityTabs base="/employees/42" linkClassName="link" activeClassName="active" />
    </PluginContributionsProvider></MemoryRouter></I18nProvider>)
    expect(await screen.findByRole('link', { name: 'Demo tab' })).toHaveAttribute('href', '/employees/42/plugins/demo/employee-tab')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('loads an independent React action only when opened, passes context and closes it', async () => {
    const action = contribution('demo', 'dialog', 'project', 'action', 'Open demo', 'module')
    const detailUrl = '/api/v1/ui-contributions/project/42/plugin%3Ademo%3Adialog/'
    const descriptor = { ...action, module: 'main', component: 'DemoDialog', api_version: 1,
      module_url: '/static/plugins/demo/assets/main.js', css_urls: [], asset_version: '1',
      context: { entity: 'project', objectId: 42, name: 'Visible project', actionUrl: detailUrl } }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/ui-contributions/project/42/') return jsonResponse({ contributions: [action] })
      if (url === detailUrl) return jsonResponse(descriptor)
      throw Error(url)
    })
    vi.mocked(loadPluginComponent).mockResolvedValue(({ context, onClose }) => <div role="dialog">
      <span>{context.name}</span><button onClick={onClose}>Close demo</button>
    </div>)
    mount('project')
    await screen.findByRole('button', { name: 'Entity actions' })
    expect(loadPluginComponent).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Entity actions' }))
    await userEvent.click(screen.getByRole('menuitem', { name: 'Open demo' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Visible project')
    expect(loadPluginComponent).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Close demo' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it.each([['team', 'teams'], ['project', 'projects']] as const)('adds only visible %s tabs from contribution metadata', async (entity, plural) => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ contributions: [
      { id: `plugin:calendars:${entity}-calendars`, plugin_slug: 'calendars', local_id: `${entity}-calendars`,
        slot: `${entity}.detail.tabs`, type: 'tab', label: 'Calendars', icon: null, behavior: null,
        confirm: false, priority: 0, module: 'main', component: 'ContextTab', api_version: 1 },
    ] }))
    render(<I18nProvider><MemoryRouter><PluginContributionsProvider scope={{ entity, objectId: 42 }}>
      <PluginEntityTabs base={`/${plural}/42`} linkClassName="link" activeClassName="active" />
    </PluginContributionsProvider></MemoryRouter></I18nProvider>)
    expect(await screen.findByRole('link', { name: 'Calendars' })).toHaveAttribute('href', `/${plural}/42/plugins/calendars/${entity}-calendars`)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('keeps same local ids from two plugins distinct and copies a Project URL', async () => {
    const copy = vi.fn(() => true)
    Object.defineProperty(document, 'execCommand', { configurable: true, value: copy })
    Object.defineProperty(window.navigator, 'clipboard', { configurable: true, value: undefined })
    const items = [contribution('alpha', 'shared', 'project', 'action', 'Copy A', 'copy_url'), contribution('beta', 'shared', 'project', 'action', 'Copy B', 'copy_url'), contribution('alpha', 'facts', 'project', 'section', 'Project facts')]
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/ui-contributions/project/42/' && init?.method !== 'POST') return jsonResponse({ contributions: items })
      if (url.endsWith('/plugin%3Aalpha%3Afacts/') && init?.method !== 'POST') return jsonResponse({ format: 'properties', items: [{ label: 'User', value: 'ada' }] })
      if (url.endsWith('/plugin%3Aalpha%3Ashared/') && init?.method === 'POST') return jsonResponse({ url: '/app/projects/42' })
      if (url.endsWith('/plugin%3Abeta%3Ashared/') && init?.method === 'POST') return jsonResponse({ url: '/app/projects/42' })
      throw Error(url)
    })
    mount('project')
    expect(await screen.findByText('ada')).toBeInTheDocument()
    screen.getByRole('button', { name: 'Entity actions' }).focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('menuitem', { name: 'Copy B' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('menuitem', { name: 'Copy A' }))
    expect(await screen.findByText('Link copied.')).toBeInTheDocument()
    expect(screen.getByDisplayValue('/app/projects/42')).toBeInTheDocument()
    expect(copy).toHaveBeenCalledWith('copy')
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === '/api/v1/ui-contributions/project/42/')).toHaveLength(1)
  })

  it('confirms an Employee action and isolates a failed section', async () => {
    let executed = false
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/ui-contributions/employee/42/') return jsonResponse({ contributions: [contribution('alpha', 'run', 'employee', 'action', 'Run demo', 'action', true), contribution('alpha', 'facts', 'employee', 'section', 'Employee facts')] })
      if (url.endsWith('/plugin%3Aalpha%3Afacts/')) return jsonResponse({ detail: 'Failed' }, 502)
      if (url.endsWith('/plugin%3Aalpha%3Arun/') && init?.method === 'POST') { executed = true; return jsonResponse({ message: 'Employee 42 was checked.' }) }
      throw Error(url)
    })
    mount('employee')
    expect(await screen.findByText('Unable to load this plugin section.')).toBeInTheDocument()
    screen.getByRole('button', { name: 'Entity actions' }).focus()
    await userEvent.keyboard('{Enter}')
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Run demo' }))
    expect(executed).toBe(false)
    const dialog = screen.getByRole('alertdialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Run' }))
    expect(await screen.findByText('Employee 42 was checked.')).toBeInTheDocument()
    expect(executed).toBe(true)
  })

  it('opens a Team URL and renders declared links without HTML injection', async () => {
    const opened = { opener: window, location: { href: '' }, close: vi.fn() }
    vi.spyOn(window, 'open').mockReturnValue(opened as unknown as Window)
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/ui-contributions/team/42/') return jsonResponse({ contributions: [contribution('alpha', 'open', 'team', 'action', 'Open team', 'open_url'), contribution('alpha', 'links', 'team', 'section', 'Team links')] })
      if (url.endsWith('/plugin%3Aalpha%3Alinks/')) return jsonResponse({ format: 'links', items: [{ label: '<b>Team</b>', url: '/app/teams/42' }] })
      if (url.endsWith('/plugin%3Aalpha%3Aopen/') && init?.method === 'POST') return jsonResponse({ url: '/app/teams/42' })
      throw Error(url)
    })
    mount('team')
    const link = await screen.findByRole('link', { name: '<b>Team</b>' })
    expect(link).toHaveAttribute('href', '/app/teams/42')
    expect(link.querySelector('b')).toBeNull()
    screen.getByRole('button', { name: 'Entity actions' }).focus()
    await userEvent.keyboard('{Enter}')
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Open team' }))
    expect(opened.location.href).toBe('/app/teams/42')
    expect(opened.opener).toBeNull()
  })

  it('renders nothing for an empty contribution list', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ contributions: [] }))
    mount('project')
    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
    expect(screen.queryByRole('button', { name: 'Entity actions' })).not.toBeInTheDocument()
    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })

  it('loads calendar actions for the displayed context without adding an empty control', async () => {
    const action = { ...contribution('alpha', 'subscribe', 'project', 'action', 'Subscribe', 'action'), slot: 'calendar.toolbar.actions' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/v1/ui-contributions/calendar/project/42/') return jsonResponse({ contributions: [action] })
      if (url === '/api/v1/ui-contributions/calendar/main/0/') return jsonResponse({ contributions: [] })
      if (url.endsWith('/plugin%3Aalpha%3Asubscribe/') && init?.method === 'POST') return jsonResponse({ message: 'Ready' })
      throw Error(url)
    })
    render(<I18nProvider><CalendarPluginActions calendarType="project" objectId={42} /><CalendarPluginActions calendarType="main" objectId={0} /></I18nProvider>)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const trigger = await screen.findByRole('button', { name: 'Plugin actions' })
    trigger.focus()
    await userEvent.keyboard('{Enter}')
    await userEvent.click(screen.getByRole('menuitem', { name: 'Subscribe' }))
    expect(await screen.findByText('Ready')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Plugin actions' })).toHaveLength(1)
  })

  it('renders multiple personal actions in one plugin section', async () => {
    const items = ['First', 'Second'].map((label, index) => ({ ...contribution('alpha', String(index), 'project', 'action', label), slot: 'user.plugin.settings.actions' }))
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/ui-contributions/user-plugin/alpha/') return jsonResponse({ contributions: items })
      throw Error(String(input))
    })
    render(<I18nProvider><UserPluginActions pluginKey="alpha" /></I18nProvider>)
    const trigger = await screen.findByRole('button', { name: 'Plugin actions' })
    trigger.focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('menuitem', { name: 'First' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Second' })).toBeInTheDocument()
  })
})
