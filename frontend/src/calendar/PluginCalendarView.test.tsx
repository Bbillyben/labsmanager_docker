import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { I18nProvider } from '../i18n/I18nProvider'
import { PrintProvider } from '../print/PrintProvider'
import { PluginCalendarView } from './PluginCalendarView'
import { pluginCalendarResources, pluginCalendarViewKey, type PluginCalendarEvent } from './pluginCalendarPresentation'

vi.mock('@fullcalendar/react', () => ({
  default: ({ initialView, events, resources, eventClick, eventContent, select }: {
    initialView: string; events: { id: string; title: string; color: string; resourceIds?: string[] }[]
    resources?: { id: string; title: string }[]
    eventClick: (info: { event: { id: string } }) => void
    eventContent?: (info: { event: { id: string; title: string } }) => ReactNode
    select: (info: { startStr: string; endStr: string; allDay: boolean }) => void
  }) => <div data-testid="full-calendar" data-view={initialView}>
    {resources?.map((item) => <span key={item.id} data-testid="resource-row">{item.title}</span>)}
    {events.map((item) => <button key={item.id} data-color={item.color} data-resources={item.resourceIds?.join(',')}
      onClick={() => eventClick({ event: { id: item.id } })}>{eventContent ? eventContent({ event: { id: item.id, title: item.title } }) : item.title}</button>)}
    <button onClick={() => select({ startStr: '2026-03-12', endStr: '2026-03-13', allDay: true })}>Select date</button>
  </div>,
}))

const events: PluginCalendarEvent[] = [
  { id: '5:9', title: 'Atelier', start: '2026-03-12', end: '2026-03-13', color: '#aabbcc',
    calendarName: 'Équipe', typeName: 'Maintenance', employeeNames: ['Ada', 'Bob'], resourceIds: ['employee:1', 'employee:2'] },
  { id: '6:10', title: 'Libre', start: '2026-03-14', end: '2026-03-15', color: '#ee7733', calendarName: 'Projet' },
]

it('shares the four core periods across calendar, list and resource modes', async () => {
  const range = vi.fn()
  const open = vi.fn()
  render(<I18nProvider><PrintProvider><PluginCalendarView title="Calendars" events={events} allowResources showCalendarName
    onRangeChange={range} onEventClick={open} /></PrintProvider></I18nProvider>)
  expect(await screen.findByTestId('full-calendar')).toHaveAttribute('data-view', 'dayGridMonthCustom')
  const period = screen.getByRole('group', { name: 'Calendar period' })
  for (const [name, scope] of [['15 days', 'fifteenDays'], ['2 months', 'twoMonths'], ['Year', 'year']] as const) {
    await userEvent.click(within(period).getByRole('button', { name }))
    expect(screen.getByTestId('full-calendar')).toHaveAttribute('data-view', pluginCalendarViewKey(scope, 'calendar'))
  }
  const display = screen.getByRole('group', { name: 'Display' })
  await userEvent.click(within(display).getByRole('button', { name: 'List' }))
  expect(screen.getByTestId('full-calendar')).toHaveAttribute('data-view', 'list_year')
  expect(screen.getByText('Maintenance')).toBeInTheDocument()
  expect(screen.getByText('Ada, Bob')).toBeInTheDocument()
  await userEvent.click(within(display).getByRole('button', { name: 'Resources' }))
  expect(screen.getByTestId('full-calendar')).toHaveAttribute('data-view', 'resourceTimelineYearCustom')
  expect(screen.getAllByTestId('resource-row')).toHaveLength(3)
  expect(screen.getByRole('button', { name: 'Équipe · Atelier' })).toHaveAttribute('data-resources', 'employee:1,employee:2')
  expect(screen.getByRole('button', { name: 'Projet · Libre' })).toHaveAttribute('data-resources', '__calendar_unassigned__')
  await userEvent.click(screen.getByRole('button', { name: 'Équipe · Atelier' }))
  expect(open).toHaveBeenCalledWith('5:9')
  expect(range).toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Print' }))
  const preview = await screen.findByRole('dialog', { name: 'Calendars' }, { timeout: 10000 })
  expect(within(preview).getByTestId('full-calendar')).toHaveAttribute('data-view', 'resourceTimelineYearCustom')
  expect(within(preview).getAllByTestId('resource-row')).toHaveLength(3)
}, 20000)

it('keeps resources permission scoped and presents one virtual row for events without visible employees', () => {
  const rows = pluginCalendarResources(events, [{ id: 'employee:1', title: 'Ada' }], 'No employee row')
  expect(rows.map((item) => item.id)).toEqual(['employee:1', 'employee:2', '__calendar_unassigned__'])
  expect(rows[1].title).toBe('Bob')
})

it('offers no resource mode for a plain events calendar', async () => {
  render(<I18nProvider><PrintProvider><PluginCalendarView title="Events" events={events.slice(1)}
    onRangeChange={vi.fn()} /></PrintProvider></I18nProvider>)
  expect(screen.queryByRole('button', { name: 'Resources' })).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'List' }))
  await waitFor(() => expect(screen.getByTestId('full-calendar')).toHaveAttribute('data-view', 'list_month'))
})
