import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CalendarEvent } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { EmployeeCalendar } from './EmployeeCalendar'
import { projectCalendarScopes, projectDayGridViews } from './projectCalendarScopes'
import timelinePlugin from '@fullcalendar/react-scheduler/timeline'

const calendar = vi.hoisted(() => ({ props: {} as Record<string, unknown> }))
vi.mock('@fullcalendar/react', () => ({ default: (props: Record<string, unknown>) => { calendar.props = props; return <div /> } }))

const leave: CalendarEvent = {
  id: 'leave:7', title: 'Leave', start: '2026-10-10', end: '2026-10-13', source: 'core', kind: 'leave', all_day: true,
  color: null, description: 'Family', display: 'auto', metadata: { leave_id: 7, leave_type_id: 3, start_date: '2026-10-10', end_date: '2026-10-12', start_period: 'ST', end_period: 'EN' },
}
const plugin = { ...leave, id: 'plugin:1', source: 'plugin', kind: 'holiday' }

function mount(onChangeDates = vi.fn().mockResolvedValue(undefined), canChange = true) {
  const onOpen = vi.fn()
  render(<I18nProvider><EmployeeCalendar anchor={new Date(2026, 9, 1)} events={[leave, plugin]} onOpen={onOpen} onCreate={vi.fn()} onChangeDates={onChangeDates} canCreate canChange={canChange} projectScope="year" /></I18nProvider>)
  return { onOpen, onChangeDates }
}

describe('Employee Calendar direct Leave interactions', () => {
  it('registers the shared views and plugins for Employee and Project', () => {
    mount(vi.fn(), false)
    expect(calendar.props.initialView).toBe(projectCalendarScopes.year.calendarView)
    expect(calendar.props.views).toBe(projectDayGridViews)
    expect(calendar.props.plugins).toContain(timelinePlugin)
    expect(calendar.props.dayMaxEvents).toBe(false)
    expect(calendar.props.dayMaxEventRows).toBe(false)
  })

  it.each(['month', 'year'] as const)('shows the Employee on a Project Leave in %s, without renaming plugin events', (projectScope) => {
    render(<I18nProvider><EmployeeCalendar anchor={new Date(2026, 9, 1)} events={[{ ...leave, metadata: { ...leave.metadata, employee_id: 12 } }, plugin]} onOpen={vi.fn()} onCreate={vi.fn()} onChangeDates={vi.fn()} canCreate={false} canChange={false} projectScope={projectScope} projectEmployeeNames={new Map([[12, 'Ada Reader']])} /></I18nProvider>)
    const eventContent = calendar.props.eventContent as (info: unknown) => React.ReactNode
    render(<>{eventContent({ event: { id: 'leave:7', title: 'Leave', extendedProps: { source: 'core', kind: 'leave', metadata: { employee_id: 12 } } } })}</>)
    expect(screen.getByRole('button', { name: /Ada Reader — Leave/ })).toHaveTextContent('Ada Reader — Leave')
    render(<>{eventContent({ event: { id: 'plugin:1', title: 'Holiday', extendedProps: { source: 'plugin', kind: 'holiday', metadata: {} } } })}</>)
    expect(screen.getByText('Holiday')).toBeInTheDocument()
    expect(screen.queryByText('Ada Reader — Holiday')).not.toBeInTheDocument()
  })

  it('uses the existing Project creation callback for a non-resource Timeline selection', () => {
    const onCreate = vi.fn()
    render(<I18nProvider><EmployeeCalendar anchor={new Date(2026, 9, 1)} events={[leave]} onOpen={vi.fn()} onCreate={onCreate} onChangeDates={vi.fn()} canCreate canChange={false} projectScope="year" /></I18nProvider>)
    const select = calendar.props.select as (selection: { allDay: boolean; startStr: string; endStr: string }) => void
    select({ allDay: false, startStr: '2026-10-06T12:00:00+02:00', endStr: '2026-10-09T00:00:00+02:00' })
    expect(onCreate).toHaveBeenCalledWith({ start_date: '2026-10-06', end_date: '2026-10-08' })
  })

  it('uses the shared year view and sends a date-only business mutation after a drop', async () => {
    const { onChangeDates } = mount()
    expect(calendar.props.initialView).toBe('dayGridYearCustom')
    expect((calendar.props.events as Array<{ editable: boolean }>).map((event) => event.editable)).toEqual([true, false])
    await act(async () => (calendar.props.eventDrop as (info: unknown) => void)({
      event: { id: 'leave:7', startStr: '2026-10-13' }, oldEvent: { startStr: '2026-10-10' }, revert: vi.fn(),
    }))
    expect(onChangeDates).toHaveBeenCalledWith(leave, { type_id: 3, start_date: '2026-10-13', start_period: 'ST', end_date: '2026-10-15', end_period: 'EN', comment: 'Family' })
  })

  it('reverts a rejected resize and keeps half-day markers', async () => {
    const onChangeDates = vi.fn().mockRejectedValue(new Error('denied'))
    mount(onChangeDates)
    const revert = vi.fn()
    await act(async () => (calendar.props.eventResize as (info: unknown) => void)({
      event: { id: 'leave:7', startStr: '2026-10-09', endStr: '2026-10-13' },
      oldEvent: { startStr: '2026-10-10', endStr: '2026-10-13' }, revert,
    }))
    await waitFor(() => expect(revert).toHaveBeenCalledOnce())
    expect(onChangeDates.mock.calls[0][1]).toMatchObject({ start_date: '2026-10-09', end_date: '2026-10-12', start_period: 'ST', end_period: 'EN' })
    expect(calendar.props.eventResizableFromStart).toBe(true)
  })

  it('reverts a rejected drop', async () => {
    mount(vi.fn().mockRejectedValue(new Error('overlap')))
    const revert = vi.fn()
    await act(async () => (calendar.props.eventDrop as (info: unknown) => void)({
      event: { id: 'leave:7', startStr: '2026-10-13' }, oldEvent: { startStr: '2026-10-10' }, revert,
    }))
    await waitFor(() => expect(revert).toHaveBeenCalledOnce())
  })

  it('keeps every event read-only without can_change, opens a simple click and suppresses a click after dragging', () => {
    const { onOpen } = mount(vi.fn(), false)
    const click = calendar.props.eventClick as (info: unknown) => void
    const dragStart = calendar.props.eventDragStart as () => void
    expect((calendar.props.events as Array<{ editable: boolean }>).every((event) => !event.editable)).toBe(true)
    click({ event: { id: 'leave:7', extendedProps: { source: 'core', kind: 'leave' } } })
    expect(onOpen).toHaveBeenCalledWith(leave)
    onOpen.mockClear()
    dragStart()
    click({ event: { id: 'leave:7', extendedProps: { source: 'core', kind: 'leave' } } })
    expect(onOpen).not.toHaveBeenCalled()
  })
})
