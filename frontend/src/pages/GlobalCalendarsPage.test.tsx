import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { localToday } from '../calendar/resourceVisibility'
import { jsonResponse } from '../test/fixtures'
import { GlobalCalendarsPage } from './GlobalCalendarsPage'

vi.mock('./EmployeeCalendar', () => ({ EmployeeCalendar: ({ events, onOpen }: { events: Array<{ id: string }>; onOpen: (event: { id: string }) => void }) =>
  <div data-testid="shared-calendar"><button onClick={() => events[0] && onOpen(events[0])}>Open Leave</button></div> }))
vi.mock('@fullcalendar/react', () => ({ default: function MockCalendar({ initialView, events, resources }: { initialView: string; events: Array<{ id: string; display: string; resourceId?: string; resourceIds?: string[] }>; resources?: Array<{ id: string; title: string }> }) {
  return <div data-testid="shared-resource-calendar" data-view={initialView}>{resources?.map((item) => <span key={item.id} data-resource-id={item.id}>{item.title}</span>)}{events.map((item) => <span key={item.id} data-event-id={item.id} data-display={item.display} data-resource={item.resourceId ?? item.resourceIds?.join(',')} />)}</div>
} }))
vi.mock('../gantt/PlanningGanttView', () => ({ PlanningGanttView: ({ onSelect }: { onSelect: (value: { kind: string; id: string }) => void }) =>
  <div data-testid="shared-gantt"><button onClick={() => onSelect({ kind: 'work', id: '9' })}>Open Work</button><button onClick={() => onSelect({ kind: 'project', id: '3' })}>Open Project</button></div> }))
vi.mock('./EmployeeLeaveSheet', () => ({ EmployeeLeaveSheet: ({ employeeName }: { employeeName: string }) => <div>Leave detail: {employeeName}</div> }))
vi.mock('./MilestoneDetailSheet', () => ({ MilestoneDetailSheet: ({ milestone }: { milestone: { name: string } | null }) => milestone ? <div>Work detail: {milestone.name}</div> : null }))

const leave = { id: 'leave:4', title: 'Annual leave', source: 'core', kind: 'leave', start: '2026-10-01', end: '2026-10-03', metadata: { employee_id: 2, leave_id: 4, leave_type_id: 7, leave_type_short_name: 'CP', leave_type_color: '#336699', start_date: '2026-10-01', end_date: '2026-10-02', start_period: 'ST', end_period: 'EN', day_count: 2 } }
const item = { id: 9, name: 'Task', project: { id: 3, name: 'Project', can_view: true }, dependencies: [], work_kind: 'task', start_date: '2026-10-01', end_date: '2026-10-10', display_state: 'in_progress' }

function setup(path = '/app/calendars') {
  window.history.pushState({}, '', path)
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url === '/api/v1/employees/filter-options/') return jsonResponse({ statuses: [{ id: 1, name: 'Staff' }], teams: [{ id: 2, name: 'Team' }] })
    if (url === '/api/v1/projects/filter-options/') return jsonResponse({ teams: [], funders: [], institutions: [] })
    if (url === '/api/v1/leave-types/') return jsonResponse([{ id: 7, name: 'Annual leave' }])
    if (url === '/api/v1/employees/2/') return jsonResponse({ id: 2, first_name: 'Ada', last_name: 'Viewer' })
    if (url === '/api/v1/projects/3/') return jsonResponse({ id: 3, name: 'Project' })
    if (url === '/api/v1/calendars/employees/filters/') return jsonResponse([{ id: 'frenchholliday-zone', title: 'Zone', type: 'select', source: 'plugin', choices: [{ value: 'Zone A', label: 'Zone A' }, { value: 'Zone B', label: 'Zone B' }], default: 'Zone A' }])
    if (url === '/api/v1/calendars/projects/filters/') return jsonResponse([])
    if (url.startsWith('/api/v1/calendars/employees/?')) {
      const isToday = new URL(url, 'http://localhost').searchParams.get('from') === localToday() && new URL(url, 'http://localhost').searchParams.get('to') === localToday()
      return jsonResponse({ events: isToday ? [{ ...leave, id: 'leave:5', start: localToday(), end: null, metadata: { ...leave.metadata, employee_id: 5, leave_id: 5 } }] : [leave, { ...leave, id: 'holiday', title: 'Holiday', kind: 'holiday', source: 'plugin', display: 'background', metadata: {} }], employee_names: { '2': 'Ada Viewer', '5': 'Bea Reader' }, resources: [{ id: '2', title: 'Ada Viewer' }, { id: '5', title: 'Bea Reader' }] })
    }
    if (url.startsWith('/api/v1/calendars/projects/?')) return jsonResponse({ projects: [{ id: 3, name: 'Project', start_date: '2026-01-01', end_date: '2026-12-31' }], items: [item], events: [], milestone_statuses: ['completed', 'overdue', 'due_soon', 'planned', 'in_progress'] })
    throw new Error(url)
  })
  render(<I18nProvider><BrowserRouter basename="/app"><GlobalCalendarsPage /></BrowserRouter></I18nProvider>)
  return fetch
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

describe('Global calendars', () => {
  it('uses the shared Leave calendar, filters, URL scopes and detail', async () => {
    const fetch = setup('/app/calendars?tab=employees&employees_date=2026-10-01&view=month&employees_current_status=1&employees_team=2&employees_type=7&employees_employee=2')
    const user = userEvent.setup()
    expect(await screen.findByTestId('shared-calendar')).toBeInTheDocument()
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('current_status=1') && String(input).includes('team=2') && String(input).includes('type=7') && String(input).includes('employee=2'))).toBe(true))
    await user.selectOptions(screen.getByLabelText('Zone'), 'Zone B')
    expect(new URLSearchParams(window.location.search).get('employees_plugin_frenchholliday-zone')).toBe('Zone B')
    await waitFor(() => {
      const requests = fetch.mock.calls.map(([input]) => String(input)).filter((url) => url.startsWith('/api/v1/calendars/employees/?'))
      expect(requests.some((url) => new URL(url, 'http://localhost').searchParams.get('frenchholliday-zone') === 'Zone B')).toBe(true)
      expect(requests.every((url) => !url.includes(':{'))).toBe(true)
    })
    await user.click(screen.getByRole('button', { name: '2 mois' }))
    expect(window.location.search).toContain('view=twoMonths')
    await user.click(screen.getByRole('button', { name: 'Open Leave' }))
    expect(await screen.findByText('Leave detail: Ada Viewer')).toBeInTheDocument()
  })

  it('uses the shared Planning Gantt with Project and Work navigation', async () => {
    const fetch = setup('/app/calendars?tab=projects&projects_date=2026-10-01&months=24&projects_status=true&projects_team=2&projects_project=3&projects_milestone_status=in_progress')
    const user = userEvent.setup()
    expect(await screen.findByTestId('shared-gantt')).toBeInTheDocument()
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('/calendars/projects/?') && String(input).includes('status=true') && String(input).includes('team=2') && String(input).includes('milestone_status=in_progress'))).toBe(true))
    expect(fetch.mock.calls.filter(([input]) => String(input).startsWith('/api/v1/calendars/projects/?'))
      .every(([input]) => new URL(String(input), 'http://localhost').searchParams.get('milestone_status') === 'in_progress')).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Open Work' }))
    expect(await screen.findByText('Work detail: Task')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Calendrier général' }))
    expect(window.location.search).toContain('projects_milestone_status=in_progress')
    expect(await screen.findByTestId('shared-calendar')).toBeInTheDocument()
  })

  it('keeps filters and background events when switching all Resource scopes', async () => {
    const fetch = setup('/app/calendars?tab=employees&employees_date=2026-10-01&view=month&employees_team=2&employees_plugin_frenchholliday-zone=Zone%20B')
    const user = userEvent.setup()
    await screen.findByTestId('shared-calendar')
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    const resourceCalendar = await screen.findByTestId('shared-resource-calendar')
    expect(resourceCalendar).toHaveAttribute('data-view', 'resourceTimelineMonthCustom')
    expect(resourceCalendar.querySelectorAll('[data-resource-id]')).toHaveLength(1)
    expect(resourceCalendar.querySelector('[data-event-id="leave:4"]')).toBeInTheDocument()
    expect(resourceCalendar.querySelector('[data-event-id="holiday"]')).toHaveAttribute('data-display', 'background')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Ressources' }), 'all')
    expect(resourceCalendar.querySelectorAll('[data-resource-id]')).toHaveLength(2)
    expect(window.location.search).toContain('employees_team=2')
    expect(window.location.search).toContain('employees_plugin_frenchholliday-zone=Zone')
    for (const [label, view] of [['15 jours', 'resourceTimelineFifteenDays'], ['2 mois', 'resourceTimelineTwoMonths'], ['Année', 'resourceTimelineYearCustom']] as const) {
      await user.click(screen.getByRole('button', { name: label }))
      expect(screen.getByTestId('shared-resource-calendar')).toHaveAttribute('data-view', view)
    }
    await user.click(screen.getByRole('button', { name: 'Calendrier' }))
    expect(await screen.findByTestId('shared-calendar')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    expect(screen.getByTestId('shared-resource-calendar')).toHaveAttribute('data-view', 'resourceTimelineYearCustom')
    expect(screen.getByRole('combobox', { name: 'Ressources' })).toHaveValue('all')
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes('team=2') && String(input).includes('frenchholliday-zone=Zone+B'))).toBe(true))
  })

  it('loads today independently of the displayed year with the same filters', async () => {
    const fetch = setup('/app/calendars?tab=employees&employees_date=2024-01-01&view=year&calendar_mode=resources&employees_team=2')
    const user = userEvent.setup()
    const select = await screen.findByRole('combobox', { name: 'Ressources' })
    await user.selectOptions(select, 'today')
    await waitFor(() => expect(fetch.mock.calls.some(([input]) => String(input).includes(`/calendars/employees/?from=${localToday()}&to=${localToday()}`) && String(input).includes('team=2'))).toBe(true))
    await waitFor(() => expect(screen.getByTestId('shared-resource-calendar').querySelector('[data-resource-id="5"]')).toBeInTheDocument())
    expect(screen.getByTestId('shared-resource-calendar').querySelector('[data-resource-id="2"]')).not.toBeInTheDocument()
  })
})
