import { render, screen, waitFor } from '@testing-library/react'
import { useEffect } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { localToday } from '../calendar/resourceVisibility'
import { buildOrganizationGraph } from '../pages/organizationGraph'
import { projectCalendarViewDefinition } from '../pages/projectCalendarScopes'
import { CalendarPrintView } from './CalendarPrintView'
import { GanttPrintView } from './GanttPrintView'
import { OrganizationChartPrintView } from './OrganizationChartPrintView'

vi.mock('@fullcalendar/react', () => ({
  default: function MockFullCalendar({ initialView, views, events, resources, eventContent, datesSet, selectable, editable }: {
    initialView: string
    views: Record<string, { type: string; slotDuration?: Record<string, number> }>
    events: Array<{ id: string; title: string; start: string; display: string; resourceId?: string; resourceIds?: string[]; extendedProps: Record<string, unknown> }>
    resources?: Array<{ id: string; title: string }>
    eventContent: (info: { event: { id: string; title: string; extendedProps: Record<string, unknown> } }) => React.ReactNode
    datesSet: () => void
    selectable: boolean
    editable: boolean
  }) {
    useEffect(() => { datesSet() }, [datesSet])
    return <div data-testid="fullcalendar-print" data-view={initialView} data-view-type={views[initialView]?.type} data-slots={JSON.stringify(views[initialView]?.slotDuration ?? null)} data-selectable={String(selectable)} data-editable={String(editable)}>
      {resources?.map((resource) => <span key={resource.id} data-resource-id={resource.id}>{resource.title}</span>)}
      {events.map((item) => <div key={item.id} data-event-id={item.id} data-display={item.display} data-resource={item.resourceId ?? item.resourceIds?.join(',')} data-start={item.start}>{eventContent({ event: { id: item.id, title: item.title, extendedProps: item.extendedProps } })}</div>)}
    </div>
  },
}))

const event = { id: 'leave:1', title: 'Paid leave', start: '2026-09-10', end: '2026-09-12', source: 'core', kind: 'leave', all_day: true, color: '#336699', description: null, display: 'auto', metadata: { employee_id: 1, leave_id: 1 } }

describe('static print renderers', () => {
  it.each([
    ['month', 'calendar', 'dayGridMonthCustom'],
    ['year', 'calendar', 'dayGridYearCustom'],
    ['month', 'resources', 'resourceTimelineMonthCustom'],
    ['year', 'resources', 'resourceTimelineYearCustom'],
  ] as const)('uses the shared %s/%s FullCalendar definition in print', async (scope, mode, viewType) => {
    const ready = vi.fn()
    const resources = [{ id: '2', title: 'Bea' }, { id: '1', title: 'Ada' }]
    render(<I18nProvider><CalendarPrintView state={{ scope, viewType, mode, range: scope === 'month' ? { from: '2026-09-01', to: '2026-09-30' } : { from: '2026-01-01', to: '2026-12-31' }, events: [event], resources, employeeNames: { 1: 'Ada Reader' } }} onReady={ready} /></I18nProvider>)
    const calendar = screen.getByTestId('fullcalendar-print')
    const definition = projectCalendarViewDefinition(scope, mode)
    expect(calendar).toHaveAttribute('data-view', definition.key)
    expect(calendar).toHaveAttribute('data-view-type', definition.options.type)
    expect(calendar).toHaveAttribute('data-slots', JSON.stringify((definition.options as { slotDuration?: object }).slotDuration ?? null))
    expect(calendar).toHaveAttribute('data-selectable', 'false')
    expect(calendar).toHaveAttribute('data-editable', 'false')
    await waitFor(() => expect(ready).toHaveBeenCalled())
    if (mode === 'resources') {
      expect(calendar.querySelectorAll('[data-resource-id]')).toHaveLength(1)
      expect(calendar.querySelector('[data-event-id="leave:1"]')).toHaveAttribute('data-resource', '1')
      expect(calendar).not.toHaveTextContent('Ada Reader — Paid leave')
    } else expect(calendar).toHaveTextContent('Ada Reader — Paid leave')
  })

  it('preserves events and background producers in the same FullCalendar view', () => {
    const holiday = { ...event, id: 'holiday', title: 'Holiday zone', display: 'background', kind: 'holiday', source: 'plugin' }
    render(<I18nProvider><CalendarPrintView state={{ scope: 'twoMonths', viewType: 'dayGridTwoMonths', mode: 'calendar', range: { from: '2026-09-01', to: '2026-10-31' }, events: [event, holiday] }} onReady={() => {}} /></I18nProvider>)
    const calendar = screen.getByTestId('fullcalendar-print')
    expect(calendar).toHaveAttribute('data-view', 'dayGridTwoMonths')
    expect(calendar.querySelector('[data-event-id="holiday"]')).toHaveAttribute('data-display', 'background')
    expect(calendar.querySelector('[data-event-id="leave:1"]')).toHaveAttribute('data-start', '2026-09-10')
  })

  it('keeps the selected Resource visibility mode in print', () => {
    const todayEvent = { ...event, id: 'leave:2', start: localToday(), end: null, metadata: { employee_id: 2, leave_id: 2 } }
    render(<I18nProvider><CalendarPrintView state={{ scope: 'year', viewType: 'resourceTimelineYearCustom', mode: 'resources', range: { from: '2025-01-01', to: '2025-12-31' }, events: [event], todayEvents: [todayEvent], resourceVisibilityMode: 'today', resources: [{ id: '1', title: 'Ada' }, { id: '2', title: 'Bea' }] }} onReady={() => {}} /></I18nProvider>)
    expect(screen.getByTestId('fullcalendar-print').querySelector('[data-resource-id="2"]')).toBeInTheDocument()
    expect(screen.getByTestId('fullcalendar-print').querySelector('[data-resource-id="1"]')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Ressources' })).not.toBeInTheDocument()
  })

  it('renders current Gantt tasks and links as SVG without SVAR viewport', () => {
    const ready = vi.fn()
    const data = { items: [
      { key: 'group:1', kind: 'group' as const, label: 'Project A', start: '2026-01-01', end: '2026-12-31', identity: { kind: 'project' as const, id: '1' } },
      { key: 'work:1', parentKey: 'group:1', kind: 'task' as const, label: 'Task A', start: '2026-03-01', end: '2026-04-01', identity: { kind: 'work' as const, id: '1' } },
    ], dependencies: [] }
    render(<GanttPrintView state={{ data, events: [], window: { from: '2026-01-01', to: '2026-12-31', months: 12 } }} onReady={ready} />)
    expect(screen.getByTestId('gantt-print')).toHaveTextContent('Project A')
    expect(screen.getByTestId('gantt-print')).toHaveTextContent('Task A')
    const gantt = screen.getByRole('img', { name: 'Gantt' })
    expect(gantt).toHaveAttribute('data-major-scale', 'month')
    expect(gantt).toHaveAttribute('data-minor-scale', 'week')
    expect(gantt).toHaveTextContent('janv. 2026')
    const firstMinor = gantt.querySelector('[data-scale="minor"] line')
    expect(firstMinor?.getAttribute('x1')).toBe(gantt.querySelector('[data-task-id="group:1"] rect')?.getAttribute('x'))
    expect(ready).toHaveBeenCalled()
    const { unmount } = render(<GanttPrintView state={{ data, events: [], window: { from: '2026-01-01', to: '2026-12-31', months: 12 }, closedKeys: ['group:1'] }} onReady={() => {}} />)
    expect(screen.getAllByTestId('gantt-print')[1]).not.toHaveTextContent('Task A')
    unmount()
  })

  it('uses year/month scales for the 24-month Gantt and keeps task alignment', () => {
    const data = { items: [{ key: 'group:1', kind: 'group' as const, label: 'Project', start: '2026-01-01', end: '2026-01-31', identity: { kind: 'project' as const, id: '1' } }], dependencies: [] }
    render(<GanttPrintView state={{ data, events: [], window: { from: '2026-01-01', to: '2027-12-31', months: 24 } }} onReady={() => {}} />)
    const gantt = screen.getByRole('img', { name: 'Gantt' })
    expect(gantt).toHaveAttribute('data-major-scale', 'year')
    expect(gantt).toHaveAttribute('data-minor-scale', 'month')
    expect(gantt).toHaveTextContent('2026')
    expect(gantt).toHaveTextContent('2027')
    expect(gantt.querySelectorAll('[data-scale="minor"]')).toHaveLength(24)
  })

  it('runs ELK on the already collapsed graph and signals readiness afterwards', async () => {
    const employees = [
      { id: 1, name: 'Root', is_active: true, statuses: [], can_view: true },
      { id: 2, name: 'Collapsed child', is_active: true, statuses: [], can_view: true },
    ]
    const graph = buildOrganizationGraph(employees, [{ superior_id: 1, employee_id: 2 }], new Set([1]), '')
    const ready = vi.fn()
    render(<OrganizationChartPrintView state={{ graph, showCurrentOnly: true, search: '' }} onReady={ready} />)
    await waitFor(() => expect(ready).toHaveBeenCalled())
    expect(screen.getByTestId('organization-chart-print')).toHaveTextContent('Root')
    expect(screen.getByTestId('organization-chart-print')).not.toHaveTextContent('Collapsed child')
  })
})
