import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getUIPage, getUIPages, getUITab, type UIModuleDescriptor } from '../api/uiContributions'
import { loadPluginComponent } from '../components/pluginModuleLoader'
import { I18nProvider } from '../i18n/I18nProvider'
import { EmployeePluginTab, EntityPluginTab, PluginPage } from './PluginPage'

vi.mock('../api/uiContributions', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/uiContributions')>()),
  getUIPage: vi.fn(), getUIPages: vi.fn(), getUITab: vi.fn(),
}))
vi.mock('../components/pluginModuleLoader', () => ({ loadPluginComponent: vi.fn() }))

const descriptor = (context: UIModuleDescriptor['context'] = {}): UIModuleDescriptor => ({
  id: 'plugin:modelexample:example-page', plugin_slug: 'modelexample', local_id: 'example-page',
  slot: 'plugin.page', type: 'page', label: 'Model Example', icon: null, behavior: null,
  confirm: false, priority: 0, module: 'main', component: 'Page', api_version: 1,
  module_url: '/static/plugins/modelexample/assets/main-abc.js?v=abc', css_urls: [], asset_version: 'abc', context,
})

function renderAt(path: string, navigationLocation?: string) {
  return render(<I18nProvider><MemoryRouter initialEntries={[{ pathname: path, state: navigationLocation ? { navigationLocation } : null }]}><Routes>
    <Route path="/plugins/:pluginSlug/:pageId" element={<PluginPage />} />
    <Route path="/employees/:employeeId/plugins/:pluginSlug/:tabId" element={<EmployeePluginTab />} />
    <Route path="/teams/:teamId/plugins/:pluginSlug/:tabId" element={<EntityPluginTab entity="team" />} />
    <Route path="/projects/:projectId/plugins/:pluginSlug/:tabId" element={<EntityPluginTab entity="project" />} />
  </Routes></MemoryRouter></I18nProvider>)
}

describe('direct plugin routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
    vi.mocked(getUIPages).mockResolvedValue({ contributions: [] })
    vi.mocked(loadPluginComponent).mockResolvedValue(({ context }) => <p>Context {context.objectId ?? 'page'}</p>)
  })

  it('requests page authorization before importing its component', async () => {
    vi.mocked(getUIPage).mockResolvedValue(descriptor())
    expect(loadPluginComponent).not.toHaveBeenCalled()
    renderAt('/plugins/modelexample/example-page')
    expect(await screen.findByText('Context page')).toBeInTheDocument()
    expect(getUIPage).toHaveBeenCalledWith('modelexample', 'example-page', expect.any(AbortSignal))
    expect(loadPluginComponent).toHaveBeenCalledTimes(1)
    expect(getUIPages).not.toHaveBeenCalled()
  })

  it('shows calendar navigation only for an authorized page that declares it', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    vi.mocked(getUIPage).mockResolvedValue({ ...descriptor(), navigation: { location: 'calendars', labels: { fr: 'Agenda' }, icon: 'calendar', order: 0 } })
    vi.mocked(getUIPages).mockResolvedValue({ contributions: [{ ...descriptor(), navigation: { location: 'calendars', labels: { fr: 'Agenda' }, icon: 'calendar', order: 0 } }] })
    renderAt('/plugins/modelexample/example-page')
    expect(await screen.findByRole('link', { name: 'Agenda' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Calendrier général' })).toHaveAttribute('href', '/calendars?tab=employees')
    expect(await screen.findByText('Context page')).toBeInTheDocument()
  })

  it('keeps the calendar navigation visible while its authorized module loads', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    let authorize!: (value: UIModuleDescriptor) => void
    vi.mocked(getUIPage).mockReturnValue(new Promise((resolve) => { authorize = resolve }))
    vi.mocked(getUIPages).mockResolvedValue({ contributions: [{ ...descriptor(), navigation: { location: 'calendars', labels: { fr: 'Agenda' }, icon: 'calendar', order: 0 } }] })
    renderAt('/plugins/modelexample/example-page', 'calendars')
    expect(await screen.findByRole('link', { name: 'Agenda' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('status')).toHaveTextContent('Chargement')
    authorize({ ...descriptor(), navigation: { location: 'calendars', labels: { fr: 'Agenda' }, icon: 'calendar', order: 0 } })
    expect(await screen.findByText('Context page')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Agenda' })).toHaveAttribute('aria-current', 'page')
    expect(getUIPages).toHaveBeenCalledTimes(1)
  })

  it('passes the backend authorized employee context to the tab', async () => {
    vi.mocked(getUITab).mockResolvedValue(descriptor({ entity: 'employee', objectId: 12 }))
    renderAt('/employees/12/plugins/modelexample/employee-tab')
    expect(await screen.findByText('Context 12')).toBeInTheDocument()
    expect(getUITab).toHaveBeenCalledWith('employee', 12, 'plugin:modelexample:employee-tab', expect.any(AbortSignal))
  })

  it.each([['team', '/teams/12'], ['project', '/projects/12']] as const)('loads a direct %s tab through the shared route', async (entity, base) => {
    vi.mocked(getUITab).mockResolvedValue(descriptor({ entity, objectId: 12 }))
    renderAt(`${base}/plugins/modelexample/context-tab`)
    expect(await screen.findByText('Context 12')).toBeInTheDocument()
    expect(getUITab).toHaveBeenCalledWith(entity, 12, 'plugin:modelexample:context-tab', expect.any(AbortSignal))
  })

  it('does not import code when the direct route is denied', async () => {
    vi.mocked(getUIPage).mockRejectedValue(new Error('forbidden'))
    renderAt('/plugins/modelexample/example-page')
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(loadPluginComponent).not.toHaveBeenCalled()
  })

  it('logs the original module error with its plugin, contribution and URL', async () => {
    const failure = new TypeError('Failed to fetch dynamically imported module')
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(getUIPage).mockResolvedValue(descriptor())
    vi.mocked(loadPluginComponent).mockRejectedValue(failure)
    renderAt('/plugins/modelexample/example-page')
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load the plugin module.')
    expect(log).toHaveBeenCalledWith('Plugin React module failed', {
      plugin: 'modelexample',
      contribution: 'plugin:modelexample:example-page',
      moduleUrl: '/static/plugins/modelexample/assets/main-abc.js?v=abc',
      error: failure,
    })
  })
})
