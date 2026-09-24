import { act, render, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CalendarEvent } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { EmployeeCalendar } from './EmployeeCalendar'

const calendar = vi.hoisted(() => ({ props: {} as Record<string, unknown> }))
vi.mock('@fullcalendar/react', () => ({ default: (props: Record<string, unknown>) => { calendar.props = props; return <div /> } }))

const leave: CalendarEvent = {
  id: 'leave:7', title: 'Leave', start: '2026-10-10', end: '2026-10-13', source: 'core', kind: 'leave', all_day: true,
  color: null, description: 'Family', display: 'auto', metadata: { leave_id: 7, leave_type_id: 3, start_date: '2026-10-10', end_date: '2026-10-12', start_period: 'ST', end_period: 'EN' },
}
const plugin = { ...leave, id: 'plugin:1', source: 'plugin', kind: 'holiday' }

function mount(onChangeDates = vi.fn().mockResolvedValue(undefined), canChange = true) {
  const onOpen = vi.fn()
  render(<I18nProvider><EmployeeCalendar anchor={new Date(2026, 9, 1)} events={[leave, plugin]} onOpen={onOpen} onCreate={vi.fn()} onChangeDates={onChangeDates} canCreate canChange={canChange} view="year" /></I18nProvider>)
  return { onOpen, onChangeDates }
}

describe('Employee Calendar direct Leave interactions', () => {
  it('uses dayGridYear and sends a date-only business mutation after a drop', async () => {
    const { onChangeDates } = mount()
    expect(calendar.props.initialView).toBe('dayGridYear')
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
