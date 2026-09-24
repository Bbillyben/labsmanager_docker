import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CalendarEvent, EmployeeDetail, EmployeeLeave } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeDetailContext } from './employeeDetailContext'
import { EmployeeLeaves } from './EmployeeLeaves'

const employee: EmployeeDetail = {
  id: 12, first_name: 'Jean', last_name: 'Dupont', birth_date: null, email: null,
  entry_date: null, exit_date: null, is_active: true, current_statuses: [], superiors: [],
  contract_quotity: null, project_quotity: null, contribution_quotity: null, active_milestones_count: 0,
}
const leave: EmployeeLeave = {
  id: 7, type: { id: 3, short_name: 'CP', name: 'Congés payés', color: '#336699' },
  start_date: '2026-09-10', start_period: 'MI', end_date: '2026-09-12', end_period: 'MI', day_count: 1, comment: 'Famille',
}
const leaveEvent: CalendarEvent = {
  id: 'leave:7', title: 'Congés payés', start: '2026-09-10T12:00:00', end: '2026-09-12T12:00:00', source: 'core', kind: 'leave', all_day: false, color: '#336699', description: 'Famille', display: 'auto',
  metadata: { leave_id: 7, leave_type_id: 3, leave_type_short_name: 'CP', leave_type_color: '#336699', start_date: '2026-09-10', end_date: '2026-09-12', start_period: 'MI', end_period: 'MI', day_count: 1 },
}
const pluginEvent: CalendarEvent = {
  id: 'holiday:1', title: 'Jour férié', start: '2026-09-15', end: '2026-09-16', source: 'frenchholliday', kind: 'public_holiday', all_day: true, color: '#aaaaaa', description: 'Jour férié', display: 'background', metadata: {},
}
const pluginFilters = [{ id: 'sample-zone', title: 'Zone', type: 'select' as const, source: 'sample', choices: [{ value: 'A', label: 'Zone A' }, { value: 'B', label: 'Zone B' }], default: 'A' }]

function responseFor(input: RequestInfo | URL, calendar: CalendarEvent[] = [leaveEvent], leaves: EmployeeLeave[] = [leave]) {
  const url = String(input)
  if (url.includes('/calendar/filters/')) return jsonResponse(pluginFilters)
  if (url.includes('/calendar/')) return jsonResponse(calendar)
  return jsonResponse(leaves)
}

function renderPanel() {
  return render(<I18nProvider><EmployeeDetailContext.Provider value={{ employee, employeeId: '12' }}><EmployeeLeaves /></EmployeeDetailContext.Provider></I18nProvider>)
}

describe('Employee Leaves panel', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-09-22T12:00:00Z'))
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    localStorage.clear()
  })
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  it('loads a bounded month, exposes half-days and opens only Leave events', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => responseFor(input, [leaveEvent, pluginEvent]))
    renderPanel()

    expect(await screen.findByRole('region', { name: 'Calendrier des absences' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/calendar/?from=2026-09-01&to=2026-09-30'))).toBe(true)
    expect(screen.getAllByText('Midi → midi').length).toBeGreaterThan(0)
    const holiday = screen.getAllByText('Jour férié')[0]
    expect(holiday.closest('button, a')).toBeNull()
    await user.click(holiday)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    const leaveButton = screen.getAllByText('Midi → midi')[0].closest('button')
    expect(leaveButton).toHaveAttribute('aria-label', 'Ouvrir le congé Congés payés')
    await user.click(leaveButton!)
    const sheet = await screen.findByRole('dialog')
    expect(within(sheet).getByText('Famille')).toBeInTheDocument()
    expect(within(sheet).getByText(/1 j.*Midi → midi/)).toBeInTheDocument()
  })

  it('persists Table mode and opens a row with the keyboard', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => responseFor(input))
    renderPanel()
    await screen.findByRole('region', { name: 'Calendrier des absences' })
    await user.click(screen.getByRole('button', { name: 'Tableau' }))

    expect(localStorage.getItem('labsmanager:employee:leaves-display')).toBe('table')
    const row = await screen.findByRole('row', { name: 'Ouvrir le congé Congés payés' })
    row.focus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
  })

  it('requests bounded Year and 5-year windows and navigates them', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => responseFor(input))
    renderPanel()
    await screen.findByRole('region', { name: 'Calendrier des absences' })
    await user.click(screen.getByRole('button', { name: 'Année' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('from=2026-01-01&to=2026-12-31'))).toBe(true))
    await user.click(screen.getByRole('button', { name: '5 ans' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('from=2024-01-01&to=2028-12-31'))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Période suivante' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('from=2029-01-01&to=2033-12-31'))).toBe(true))
  }, 15_000)

  it('applies table filters and retries a local error', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    localStorage.setItem('labsmanager:employee:leaves-display', 'table')
    let attempts = 0
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input).includes('/calendar/filters/')) return jsonResponse(pluginFilters)
      attempts += 1
      return attempts === 1 ? jsonResponse({}, 500) : jsonResponse([leave])
    })
    renderPanel()
    await user.click(await screen.findByRole('button', { name: 'Réessayer' }))
    await screen.findByRole('row', { name: 'Ouvrir le congé Congés payés' })
    await user.selectOptions(screen.getByLabelText('Type de congé'), '3')
    await user.type(screen.getByLabelText('Du'), '2026-09-01')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('type=3') && String(url).includes('from=2026-09-01'))).toBe(true))
  })

  it('renders the English controls and empty state', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).includes('/calendar/filters/') ? jsonResponse([]) : jsonResponse([]))
    renderPanel()
    expect(await screen.findByText('No leave in this period.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Table' })).toBeInTheDocument()
    expect(screen.getByLabelText('Leave type')).toBeInTheDocument()
  })

  it('refreshes only calendar data when a generic plugin filter changes', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => responseFor(input))
    renderPanel()

    await user.selectOptions(await screen.findByLabelText('Zone'), 'B')

    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('sample-zone=B'))).toBe(true))
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/calendar/filters/'))).toHaveLength(1)
  })

  it('omits background events from five years and opens a dated Leave by keyboard', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => responseFor(input, [leaveEvent, pluginEvent]))
    renderPanel()

    await user.click(await screen.findByRole('button', { name: '5 ans' }))
    const eventButton = await screen.findByRole('button', { name: 'Ouvrir le congé Congés payés' })
    expect(within(eventButton).getByText(/10\/09\/2026 → 12\/09\/2026/)).toBeInTheDocument()
    expect(screen.queryByText('Jour férié')).not.toBeInTheDocument()
    eventButton.focus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
  })
})
