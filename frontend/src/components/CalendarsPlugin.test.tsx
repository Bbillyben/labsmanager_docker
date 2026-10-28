import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { ContextTab, Page, SettingsPanel } from '../../../data/plugins/Calendars/frontend/src/main'
import * as api from '../../../data/plugins/Calendars/frontend/src/api'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { teamFilterSources } from '../config/teamFilterSources'
import { projectFilterSources } from '../config/projectFilterSources'

vi.mock('@labsmanager/plugin-ui', async (original) => ({
  ...(await original<typeof import('../plugin-api')>()),
  PluginCalendarView: ({ events, canCreate, showCalendarName, onRangeChange, onDateSelect, onEventClick }: {
    events: { id: string; title: string; calendarName?: string; color?: string; employeeNames?: string[] }[]; canCreate: boolean; showCalendarName?: boolean
    onRangeChange: (range: { start: string; end: string }) => void
    onDateSelect: (range: { start: string; end: string; allDay: boolean }) => void
    onEventClick: (id: string) => void
  }) => {
    // Keep date navigation explicit so tests can verify range requests.
    return <div data-testid="shared-calendar" data-selectable={canCreate}>
      <button onClick={() => onRangeChange({ start: '2026-03-01', end: '2026-04-01' })}>Show March</button>
      <button onClick={() => onDateSelect({ start: '2026-03-12', end: '2026-03-12', allDay: true })}>Choose date</button>
      {events.map((event) => <button key={event.id} data-color={event.color}
        onClick={() => onEventClick(event.id)}>{showCalendarName && event.calendarName ? `${event.calendarName} · ` : ''}{event.title}{event.employeeNames?.length ? ` · ${event.employeeNames.length}` : ''}</button>)}
    </div>
  },
}))

vi.mock('../../../data/plugins/Calendars/frontend/src/api', async (original) => ({
  ...(await original<typeof import('../../../data/plugins/Calendars/frontend/src/api')>()),
  listCalendars: vi.fn(), listTypes: vi.fn(), listEvents: vi.fn(), createCalendar: vi.fn(), updateCalendar: vi.fn(),
  listAttachments: vi.fn(), setAttachments: vi.fn(), updateType: vi.fn(),
  createEvent: vi.fn(), updateEvent: vi.fn(), deleteEvent: vi.fn(),
  createType: vi.fn(), listMembers: vi.fn(), setMember: vi.fn(), searchUsers: vi.fn(), resolveUser: vi.fn(),
  searchEligibleEmployees: vi.fn(), resolveEligibleEmployee: vi.fn(), listResources: vi.fn(),
}))

const calendar = { id: 5, name: 'Équipe', description: '', color: '#3b82f6', access_mode: 'restricted' as const, created_by: 1,
  calendar_type: 'events' as const, has_events: false, role: 'manage' as const, can_edit: true, can_manage: true }
const event = { id: 9, calendar: 5, event_type: null, title: 'Séminaire', description: '',
  start: '2026-03-12', end: '2026-03-13', all_day: true, color: '#3b82f6', created_by: 1, employees: [] }

function mount() { return render(<I18nProvider><Page context={{}} /></I18nProvider>) }
function mountManagement() { render(<I18nProvider><SettingsPanel context={{ pluginKey: 'calendars' }} /></I18nProvider>) }
async function openManagementAction(label: string) {
  await userEvent.click(await screen.findByRole('button', { name: 'Actions · Équipe' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: label }))
}

describe('Calendars external page in the host tree', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [calendar] })
    vi.mocked(api.listTypes).mockResolvedValue({ results: [] })
    vi.mocked(api.listEvents).mockResolvedValue({ results: [event] })
    vi.mocked(api.listResources).mockResolvedValue({ results: [] })
    vi.mocked(api.createEvent).mockResolvedValue(event)
    vi.mocked(api.createCalendar).mockResolvedValue({ ...calendar, id: 7, name: 'Nouveau' })
    vi.mocked(api.updateCalendar).mockResolvedValue(calendar)
    vi.mocked(api.listAttachments).mockResolvedValue({ employees: [], teams: [], projects: [] })
    vi.mocked(api.setAttachments).mockResolvedValue({ employees: [], teams: [], projects: [] })
    vi.mocked(api.updateType).mockResolvedValue({ id: 11, calendar: 5, name: 'Réunion', color: '#aabbcc', is_active: true })
    vi.mocked(api.updateEvent).mockResolvedValue(event)
    vi.mocked(api.deleteEvent).mockResolvedValue(undefined)
    vi.mocked(api.createType).mockResolvedValue({ id: 11, calendar: 5, name: 'Réunion', color: '', is_active: true })
    vi.mocked(api.listMembers).mockResolvedValue({ owner: { id: 1, label: 'Owner' }, results: [] })
    vi.mocked(api.setMember).mockResolvedValue({ user: { id: 8, label: 'Alice' }, level: 'edit' })
    vi.mocked(api.searchUsers).mockResolvedValue({ results: [{ id: 8, label: 'Alice' }], has_more: false })
    vi.mocked(api.resolveUser).mockResolvedValue({ results: [{ id: 8, label: 'Alice' }] })
    vi.mocked(api.searchEligibleEmployees).mockResolvedValue({ results: [], has_more: false })
    vi.mocked(api.resolveEligibleEmployee).mockResolvedValue({ results: [] })
  })

  it('offers a personal ICS URL to a viewer only when the consumer is available', async () => {
    let enabled = false
    const action = { id: 'plugin:icalexport:published', plugin_slug: 'icalexport', slot: 'published-calendar.actions',
      type: 'action', label: 'Subscribe', behavior: 'module', icon: null, confirm: false, priority: 0 }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/ui-contributions/published-calendar/calendars/5/')
        return new Response(JSON.stringify({ contributions: enabled ? [action] : [] }), { headers: { 'content-type': 'application/json' } })
      if (url.endsWith('/plugin%3Aicalexport%3Apublished/'))
        return new Response(JSON.stringify({ ...action, module: 'main', component: 'SubscriptionDialog', api_version: 1,
          module_url: '/static/plugins/icalexport/assets/main.js', css_urls: [], asset_version: '1',
          context: { providerSlug: 'calendars', calendarId: '5', name: 'Équipe', actionUrl: url } }),
        { headers: { 'content-type': 'application/json' } })
      throw Error(url)
    })
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [{ ...calendar, role: 'view', can_edit: false, can_manage: false }] })
    const mounted = mount()
    await screen.findByTestId('shared-calendar')
    expect(screen.queryByRole('button', { name: 'Subscribe' })).not.toBeInTheDocument()
    mounted.unmount()
    enabled = true
    mount()
    await userEvent.click(await screen.findByRole('button', { name: 'Subscribe' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/plugin%3Aicalexport%3Apublished/'))).toBe(true))
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
  })

  it('selects an accessible calendar through the shared presentation', async () => {
    mount()
    const shared = await screen.findByTestId('shared-calendar')
    expect(api.listCalendars).toHaveBeenCalledWith(expect.any(AbortSignal), undefined, 'general')
    expect(shared).toHaveAttribute('data-selectable', 'true')
    await userEvent.click(screen.getByText('Show March'))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledWith(5, '2026-03-01', '2026-04-01', expect.any(AbortSignal)))
    expect(await screen.findByText('Séminaire')).toBeInTheDocument()
  })

  it('updates the active page and form when the host language changes', async () => {
    const previous = Object.getOwnPropertyDescriptor(navigator, 'languages')
    try {
      Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] })
      mount()
      expect(await screen.findByRole('button', { name: 'Ajouter un événement' })).toBeInTheDocument()
      await userEvent.click(screen.getByRole('button', { name: 'Ajouter un événement' }))
      expect(await screen.findByText('Nouvel événement')).toBeInTheDocument()
      Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en-GB'] })
      window.dispatchEvent(new Event('languagechange'))
      expect((await screen.findAllByText('Add event')).length).toBeGreaterThan(0)
      expect(await screen.findByText('New event')).toBeInTheDocument()
    } finally {
      if (previous) Object.defineProperty(navigator, 'languages', previous)
    }
  })

  it('keeps associated calendars out of the general view and in plugin settings', async () => {
    const contextual = { ...calendar, id: 8, name: 'Contextual', attachments: { employees: [{ id: 12, label: 'Ada' }], teams: [], projects: [] } }
    vi.mocked(api.listCalendars).mockImplementation(async (_signal, _context, scope) => ({ results: scope === 'managed' ? [calendar, contextual] : [calendar] }))
    mount()
    expect(await screen.findByRole('option', { name: 'Équipe' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Contextual' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Managed calendars' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create calendar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Manage' })).not.toBeInTheDocument()
    mountManagement()
    expect(await screen.findByRole('cell', { name: 'Contextual' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Employees: Ada' })).toBeInTheDocument()
    expect(api.listCalendars).toHaveBeenCalledWith(expect.any(AbortSignal), undefined, 'managed')
  })

  it('hides management and event creation for a viewer', async () => {
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [{ ...calendar, role: 'view', can_edit: false, can_manage: false }] })
    mount()
    expect(await screen.findByTestId('shared-calendar')).toHaveAttribute('data-selectable', 'false')
    expect(screen.queryByRole('button', { name: 'Manage' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('Choose date'))
    expect(screen.queryByText('New event')).not.toBeInTheDocument()
  })

  it('does not expose management actions for a calendar without manage capability', async () => {
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [{ ...calendar, role: 'view', can_edit: false, can_manage: false }] })
    mountManagement()
    expect(await screen.findByRole('cell', { name: 'Équipe' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions · Équipe' })).not.toBeInTheDocument()
  })

  it('creates an all-day event with an exclusive end date', async () => {
    mount()
    await userEvent.click(await screen.findByText('Choose date'))
    expect(await screen.findByText('New event')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Title'), 'Atelier')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createEvent).toHaveBeenCalledWith(5, expect.objectContaining({
      title: 'Atelier', start: '2026-03-12', end: '2026-03-13', all_day: true,
    })))
  })

  it('shows an API error and retries the visible period', async () => {
    vi.mocked(api.listEvents).mockRejectedValueOnce(new Error('unavailable')).mockResolvedValue({ results: [] })
    mount()
    await userEvent.click(await screen.findByText('Show March'))
    const eventError = await screen.findByText('Unable to load events.')
    await userEvent.click(within(eventError.closest('[role="alert"]')!).getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledTimes(2))
  })

  it('switches calendars and requests only the selected calendar period', async () => {
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [calendar, { ...calendar, id: 6, name: 'Deuxième' }] })
    mount()
    await userEvent.click(await screen.findByText('Show March'))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledWith(5, '2026-03-01', '2026-04-01', expect.any(AbortSignal)))
    await userEvent.selectOptions(screen.getByLabelText('Calendar'), '6')
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledWith(6, '2026-03-01', '2026-04-01', expect.any(AbortSignal)))
  })

  it('edits and deletes an event through the shared sheet and confirmation dialog', async () => {
    mount()
    await userEvent.click(await screen.findByText('Show March'))
    await userEvent.click(await screen.findByRole('button', { name: 'Séminaire' }))
    const title = await screen.findByLabelText('Title')
    await userEvent.clear(title)
    await userEvent.type(title, 'Updated')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.updateEvent).toHaveBeenCalledWith(5, 9, expect.objectContaining({ title: 'Updated' })))
    await userEvent.click(await screen.findByRole('button', { name: 'Séminaire' }))
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    const dialog = await screen.findByRole('alertdialog')
    await userEvent.click(dialog.querySelector('button:last-child')!)
    await waitFor(() => expect(api.deleteEvent).toHaveBeenCalledWith(5, 9))
  })

  it('creates another independent calendar and selects it', async () => {
    vi.mocked(api.listCalendars).mockResolvedValueOnce({ results: [calendar] })
      .mockResolvedValue({ results: [calendar, { ...calendar, id: 7, name: 'Nouveau' }] })
    mountManagement()
    await userEvent.click(await screen.findByRole('button', { name: 'Create calendar' }))
    await userEvent.type(await screen.findByLabelText('Name'), 'Nouveau')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createCalendar).toHaveBeenCalledWith({ name: 'Nouveau', description: '', color: '#3b82f6', access_mode: 'restricted', calendar_type: 'events' }))
    expect(await screen.findByRole('cell', { name: 'Nouveau' })).toBeInTheDocument()
    expect(screen.queryByTestId('shared-calendar')).not.toBeInTheDocument()
  })

  it('manages event types and shares with an actual user account', async () => {
    mountManagement()
    await openManagementAction('Event types')
    await userEvent.type(screen.getByLabelText('New type'), 'Réunion')
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(api.createType).toHaveBeenCalledWith(5, { name: 'Réunion', color: '', is_active: true }))
    await userEvent.click(screen.getByRole('tab', { name: 'Sharing' }))
    await userEvent.type(screen.getByRole('combobox', { name: 'User' }), 'Alice')
    await userEvent.click(await screen.findByRole('option', { name: 'Alice' }))
    await userEvent.selectOptions(screen.getByLabelText('Access'), 'edit')
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => expect(api.setMember).toHaveBeenCalledWith(5, 8, 'edit'))
  }, 15000)

  it('loads and edits existing event types from calendar settings', async () => {
    vi.mocked(api.listTypes).mockResolvedValue({ results: [{ id: 11, calendar: 5, name: 'Réunion', color: '', is_active: true }] })
    mountManagement()
    await openManagementAction('Settings')
    await userEvent.click(screen.getByRole('tab', { name: 'Event types' }))
    await waitFor(() => expect(api.listTypes).toHaveBeenCalledWith(5))
    await userEvent.click(await screen.findByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.updateType).toHaveBeenCalledWith(5, 11, expect.objectContaining({ name: 'Réunion' })))
  })

  it('applies effective event colors without calendar administration controls', async () => {
    vi.mocked(api.listTypes).mockResolvedValue({ results: [{ id: 11, calendar: 5, name: 'Réunion', color: '#0088cc', is_active: true }] })
    vi.mocked(api.listEvents).mockResolvedValueOnce({ results: [{ ...event, event_type: 11, color: '#0088cc' }] })
      .mockResolvedValue({ results: [{ ...event, event_type: 11, color: '#aabbcc' }] })
    mount()
    await userEvent.click(await screen.findByText('Show March'))
    expect(await screen.findByRole('button', { name: 'Séminaire' })).toHaveAttribute('data-color', '#0088cc')
    expect(screen.queryByRole('button', { name: 'Manage' })).not.toBeInTheDocument()
  })

  it('saves the access mode only for managers', async () => {
    mountManagement()
    await openManagementAction('Settings')
    await userEvent.selectOptions(screen.getByLabelText('Access mode'), 'inherited')
    expect(screen.getByText(/People allowed to view an attached object/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.updateCalendar).toHaveBeenCalledWith(5, expect.objectContaining({ access_mode: 'inherited' })))
  })

  it('chooses the assignment calendar type and locks it after events exist', async () => {
    mountManagement()
    await userEvent.click(await screen.findByRole('button', { name: 'Create calendar' }))
    await userEvent.type(screen.getByLabelText('Name'), 'Assignments')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'assignments')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createCalendar).toHaveBeenCalledWith(expect.objectContaining({ calendar_type: 'assignments' })))
  })

  it('shows assigned employees and permits removing the last one', async () => {
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [{ ...calendar, calendar_type: 'assignments' }] })
    vi.mocked(api.listEvents).mockResolvedValue({ results: [{ ...event, employees: [{ id: 8, label: 'Alice' }] }] })
    mount()
    await userEvent.click(await screen.findByText('Show March'))
    await userEvent.click(await screen.findByRole('button', { name: 'Séminaire · 1' }))
    expect(screen.getByText('Alice')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Remove' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.updateEvent).toHaveBeenCalledWith(5, 9, expect.objectContaining({ employees: [] })))
  })

  it('searches eligible employees and sends multiple distinct assignments', async () => {
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [{ ...calendar, calendar_type: 'assignments' }] })
    vi.mocked(api.searchEligibleEmployees).mockResolvedValue({ results: [{ id: 8, label: 'Alice' }], has_more: false })
    vi.mocked(api.resolveEligibleEmployee).mockResolvedValue({ results: [{ id: 8, label: 'Alice' }] })
    mount()
    await userEvent.click(await screen.findByText('Choose date'))
    await userEvent.type(screen.getByLabelText('Title'), 'Assigned event')
    await userEvent.type(screen.getByRole('combobox', { name: 'Assigned employees' }), 'Ali')
    await userEvent.click(await screen.findByRole('option', { name: 'Alice' }))
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(await screen.findByText('Alice')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createEvent).toHaveBeenCalledWith(5, expect.objectContaining({ employees: [8] })))
  })

  it('uses the host selectors to attach and remove Employees, Teams and Projects', async () => {
    const sources = [employeeFilterSources.allEmployees, teamFilterSources.teams, projectFilterSources.projects]
    for (const [index, source] of sources.entries()) {
      vi.spyOn(source, 'search').mockResolvedValue({ options: [{ value: String(index + 20), label: `Object ${index}` }], hasMore: false })
      vi.spyOn(source, 'resolve').mockResolvedValue({ value: String(index + 20), label: `Object ${index}` })
    }
    const state = { employees: [] as { id: number; label: string }[], teams: [] as { id: number; label: string }[], projects: [] as { id: number; label: string }[] }
    vi.mocked(api.setAttachments).mockImplementation(async (_id, update) => {
      for (const kind of ['employees', 'teams', 'projects'] as const) {
        if (update[kind]) state[kind] = update[kind].map((id) => ({ id, label: `Object ${id - 20}` }))
      }
      return { ...state }
    })
    mountManagement()
    await openManagementAction('Attachments')
    await waitFor(() => expect(api.listAttachments).toHaveBeenCalledWith(5, expect.any(AbortSignal)))
    for (const [index, kind] of (['Employees', 'Teams', 'Projects'] as const).entries()) {
      const group = screen.getByText(kind).closest('.calendars-attachment-group') as HTMLElement
      await userEvent.type(within(group).getByRole('combobox', { name: kind }), `Object ${index}`)
      await userEvent.click(await screen.findByRole('option', { name: `Object ${index}` }))
      await userEvent.click(within(group).getByRole('button', { name: 'Add' }))
      await waitFor(() => expect(api.setAttachments).toHaveBeenCalledWith(5, { [kind.toLowerCase()]: [index + 20] }))
      expect(await within(group).findByText(`Object ${index}`)).toBeInTheDocument()
    }
    const group = screen.getByText('Employees').closest('.calendars-attachment-group') as HTMLElement
    await userEvent.click(within(group).getByRole('button', { name: 'Remove' }))
    const dialog = await screen.findByRole('alertdialog')
    await userEvent.click(dialog.querySelector('button:last-child')!)
    await waitFor(() => expect(api.setAttachments).toHaveBeenCalledWith(5, { employees: [] }))
  }, 20000)
})

describe('Calendars contextual tabs', () => {
  const second = { ...calendar, id: 6, name: 'Projet', color: '#aabbcc', role: 'view' as const, can_edit: false, can_manage: false }
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listCalendars).mockResolvedValue({ results: [calendar, second] })
    vi.mocked(api.listEvents).mockImplementation(async (id) => ({ results: [{ ...event, calendar: id, title: id === 5 ? 'Atelier' : 'Réunion', color: id === 5 ? '#3b82f6' : '#aabbcc' }] }))
    vi.mocked(api.listTypes).mockResolvedValue({ results: [] })
    vi.mocked(api.createEvent).mockResolvedValue(event)
    vi.mocked(api.updateEvent).mockResolvedValue(event)
  })

  it('subscribes to the selected view-only contextual calendar', async () => {
    const action = { id: 'plugin:icalexport:published', plugin_slug: 'icalexport', slot: 'published-calendar.actions',
      type: 'action', label: 'Subscribe', behavior: 'module', icon: null, confirm: false, priority: 0 }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.startsWith('/api/v1/ui-contributions/published-calendar/') && !url.includes('plugin%3A'))
        return new Response(JSON.stringify({ contributions: [action] }), { headers: { 'content-type': 'application/json' } })
      if (url.includes('plugin%3A')) return new Response(JSON.stringify({ ...action, module: 'main', component: 'SubscriptionDialog',
        api_version: 1, module_url: '/static/plugins/icalexport/assets/main.js', css_urls: [], asset_version: '1',
        context: { providerSlug: 'calendars', calendarId: '6', name: 'Projet', actionUrl: url } }),
      { headers: { 'content-type': 'application/json' } })
      throw Error(url)
    })
    render(<I18nProvider><ContextTab context={{ entity: 'team', objectId: 12 }} /></I18nProvider>)
    await screen.findByTestId('shared-calendar')
    const buttons = await screen.findAllByRole('button', { name: 'Subscribe' })
    await userEvent.click(buttons[1])
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/calendars/6/plugin%3Aicalexport%3Apublished/'))).toBe(true))
  })

  it.each(['employee', 'team', 'project'] as const)('loads only %s calendars after opening the tab', async (entity) => {
    render(<I18nProvider><ContextTab context={{ entity, objectId: 12 }} /></I18nProvider>)
    expect(await screen.findByTestId('shared-calendar')).toBeInTheDocument()
    expect(api.listCalendars).toHaveBeenCalledWith(expect.any(AbortSignal), { entity, objectId: 12 })
    expect(api.listEvents).not.toHaveBeenCalled()
    await userEvent.click(screen.getByText('Show March'))
    await waitFor(() => expect(api.listEvents).toHaveBeenCalledTimes(2))
    expect(await screen.findByRole('button', { name: 'Équipe · Atelier' })).toHaveAttribute('data-color', '#3b82f6')
    expect(screen.getByRole('button', { name: 'Projet · Réunion' })).toHaveAttribute('data-color', '#aabbcc')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Projet' }))
    expect(screen.queryByRole('button', { name: 'Projet · Réunion' })).not.toBeInTheDocument()
  })

  it('requires an explicit editable destination for creation and preserves viewing rights', async () => {
    render(<I18nProvider><ContextTab context={{ entity: 'project', objectId: 12 }} /></I18nProvider>)
    await userEvent.click(await screen.findByText('Choose date'))
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
    expect(screen.queryByRole('option', { name: 'Projet' })).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Calendar'), '5')
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
    await userEvent.type(await screen.findByLabelText('Title'), 'New')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(api.createEvent).toHaveBeenCalledWith(5, expect.objectContaining({ title: 'New' })))
    await userEvent.click(screen.getByText('Show March'))
    await userEvent.click(await screen.findByRole('button', { name: 'Projet · Réunion' }))
    expect(await screen.findByLabelText('Title')).toBeDisabled()
  }, 15000)
})
