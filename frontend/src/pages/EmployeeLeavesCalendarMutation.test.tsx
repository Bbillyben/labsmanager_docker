import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { CalendarEvent, EmployeeDetail } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeDetailContext } from './employeeDetailContext'
import { EmployeeLeaves } from './EmployeeLeaves'

const leave: CalendarEvent = {
  id: 'leave:7', title: 'Leave', start: '2026-09-10', end: '2026-09-13', source: 'core', kind: 'leave', all_day: true,
  color: null, description: 'Family', display: 'auto', metadata: { leave_id: 7, leave_type_id: 3, start_date: '2026-09-10', end_date: '2026-09-12', start_period: 'ST', end_period: 'EN' },
}
const employee = { id: 12, first_name: 'Jean', last_name: 'Dupont' } as EmployeeDetail
const calendarMock = vi.hoisted(() => ({ events: [] as CalendarEvent[], called: vi.fn() }))

vi.mock('./EmployeeCalendar', () => ({
  EmployeeCalendar: ({ events, onChangeDates }: { events: CalendarEvent[]; onChangeDates: (event: CalendarEvent, write: object) => Promise<void> }) =>
    <button onClick={() => { calendarMock.events = events; calendarMock.called(); void onChangeDates(events[0], { type_id: 3, start_date: '2026-09-13', start_period: 'ST', end_date: '2026-09-15', end_period: 'EN', comment: 'Family' }).catch(() => {}) }}>Move Leave</button>,
}))

function mount() {
  return render(<I18nProvider><EmployeeDetailContext.Provider value={{ employee, employeeId: '12' }}><EmployeeLeaves /></EmployeeDetailContext.Provider></I18nProvider>)
}

describe('Employee Leave calendar PATCH', () => {
  afterEach(() => { vi.restoreAllMocks(); localStorage.clear() })

  it('PATCHes the Leave resource once and treats a subsequent refresh failure as a read error', async () => {
    let calendarReads = 0
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.includes('/leaves/capabilities/')) return jsonResponse({ can_add: true, can_change: true, can_delete: true })
      if (url.includes('/calendar/filters/')) return jsonResponse([])
      if (url.includes('/calendar/')) return ++calendarReads <= 2 ? jsonResponse([leave]) : jsonResponse({}, 500)
      if (init?.method === 'PATCH') return jsonResponse({ id: 7 })
      return jsonResponse([])
    })
    mount()
    await screen.findByRole('button', { name: 'Move Leave' })
    await waitFor(() => expect(calendarReads).toBeGreaterThanOrEqual(2))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Move Leave' }))
    expect(calendarMock.called).toHaveBeenCalledOnce()
    expect(calendarMock.events).toHaveLength(1)
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'PATCH'), JSON.stringify(fetchMock.mock.calls.map(([url, init]) => [String(url), init?.method]))).toHaveLength(1))
    const [url, init] = fetchMock.mock.calls.find(([, options]) => options?.method === 'PATCH')!
    expect(String(url)).toContain('/api/v1/employees/12/leaves/7/')
    expect(JSON.parse(String(init?.body))).toMatchObject({ start_date: '2026-09-13', end_date: '2026-09-15', start_period: 'ST', end_period: 'EN' })
    expect(await screen.findByText('Leave is temporarily unavailable.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'PATCH')).toHaveLength(1)
    expect(screen.queryByText('The server could not process the request.')).not.toBeInTheDocument()
  })

  it('shows a backend validation error without refreshing after a rejected PATCH', async () => {
    let calendarReads = 0
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.includes('/leaves/capabilities/')) return jsonResponse({ can_add: true, can_change: true, can_delete: true })
      if (url.includes('/calendar/filters/')) return jsonResponse([])
      if (url.includes('/calendar/')) { calendarReads += 1; return jsonResponse([leave]) }
      if (init?.method === 'PATCH') return jsonResponse({ non_field_errors: ['Leave overlaps an existing absence.'] }, 400)
      return jsonResponse([])
    })
    mount()
    await screen.findByRole('button', { name: 'Move Leave' })
    await waitFor(() => expect(calendarReads).toBeGreaterThanOrEqual(2))
    const readsBeforeMutation = calendarReads
    await userEvent.setup().click(screen.getByRole('button', { name: 'Move Leave' }))
    expect(await screen.findByText('Leave overlaps an existing absence.')).toBeInTheDocument()
    expect(calendarReads).toBe(readsBeforeMutation)
    expect(fetchMock.mock.calls.filter(([, options]) => options?.method === 'PATCH')).toHaveLength(1)
  })
})
