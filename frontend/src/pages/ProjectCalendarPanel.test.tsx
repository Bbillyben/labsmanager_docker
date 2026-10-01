import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { ProjectCalendarPanel } from './ProjectCalendarPanel'
import { projectCalendarRange, projectCalendarScopes, shiftProjectCalendarAnchor, type ProjectCalendarScope } from './projectCalendarScopes'

vi.mock('@fullcalendar/react', () => ({
  default: ({ initialView, events, resources, eventClick, select, selectAllow, views }: {
    initialView: string
    events: Array<{ id: string; title: string; editable?: boolean; resourceId?: string; resourceIds?: string[]; extendedProps?: Record<string, unknown> }>
    resources?: Array<{ id: string; title: string }>
    eventClick?: (info: { event: { id: string; extendedProps?: Record<string, unknown> } }) => void
    select?: (info: { allDay: boolean; startStr: string; endStr: string; resource?: { id: string } }) => void
    selectAllow?: (info: { resource?: { id: string } }) => boolean
    views?: Record<string, { type: string; duration?: Record<string, number> }>
  }) => <div data-testid="calendar" data-view={initialView} data-duration={JSON.stringify(views?.[initialView]?.duration ?? null)}>
    {resources?.map((resource) => <span key={resource.id}>{resource.title}</span>)}
    {events.map((event) => <button data-editable={String(Boolean(event.editable))} data-resource={event.resourceId ?? event.resourceIds?.join(',')} key={event.id} onClick={() => eventClick?.({ event: { id: event.id, extendedProps: event.extendedProps } })}>{event.title}</button>)}
    <button onClick={() => select?.({ allDay: true, startStr: '2026-09-20', endStr: '2026-09-22', resource: { id: '12' } })}>Select range</button>
    <button onClick={() => { const info = { allDay: false, startStr: '2026-09-20T12:00:00+02:00', endStr: '2026-09-22T12:00:00+02:00', resource: { id: '12' } }; if (selectAllow?.(info) ?? true) select?.(info) }}>Select timed range</button>
    <button onClick={() => { const info = { allDay: false, startStr: '2026-09-20T12:00:00+02:00', endStr: '2026-09-22T12:00:00+02:00', resource: { id: '13' } }; if (selectAllow?.(info) ?? true) select?.(info) }}>Select read-only resource</button>
  </div>,
}))

const leave = {
  id: 'leave:7', title: 'Paid leave', start: '2026-09-10', end: '2026-09-12', source: 'core', kind: 'leave', all_day: true, color: '#336699', description: 'Family', display: 'auto',
  metadata: { leave_id: 7, employee_id: 12, leave_type_id: 3, leave_type_short_name: 'CP', leave_type_color: '#336699', start_date: '2026-09-10', end_date: '2026-09-11', start_period: 'ST', end_period: 'EN', day_count: 2 },
}
const holiday = { id: 'holiday:1', title: 'Holiday', start: '2026-09-15', end: '2026-09-16', source: 'plugin', kind: 'holiday', all_day: true, color: '#aaaaaa', description: null, display: 'background', metadata: {} }

function mockApi(canAdd: boolean, withReadOnlyParticipant = false) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.includes('/participants/')) return jsonResponse([{ id: 12, title: 'Ada Reader', capabilities: { can_add: canAdd, can_change: canAdd, can_delete: canAdd } }, ...(withReadOnlyParticipant ? [{ id: 13, title: 'Grace Viewer', capabilities: { can_add: false, can_change: false, can_delete: false } }] : [])])
    if (url.includes('/filters/')) return jsonResponse([])
    if (url.includes('/leave-types/')) return jsonResponse([{ id: 3, name: 'Paid leave', short_name: 'CP', color: '#336699', parent_id: null, depth: 0 }])
    if (url.endsWith('/leaves/')) return jsonResponse({ id: 8, type: { id: 3, name: 'Paid leave', short_name: 'CP', color: '#336699' }, start_date: '2026-09-20', start_period: 'ST', end_date: '2026-09-21', end_period: 'EN', day_count: 2, comment: '' }, 201)
    return jsonResponse([leave, holiday])
  })
}

describe('Project Calendar', () => {
  beforeEach(() => { Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }) })
  afterEach(() => vi.restoreAllMocks())

  it('uses the same events for Calendar, List and resourceTimeline Participants', async () => {
    mockApi(false)
    const user = userEvent.setup()
    render(<I18nProvider><ProjectCalendarPanel projectId="4" /></I18nProvider>)
    expect(await screen.findByTestId('calendar')).toHaveAttribute('data-view', projectCalendarScopes.month.calendarView)
    expect(screen.queryByRole('button', { name: 'Ajouter une absence' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Liste' }))
    expect(screen.getByRole('row', { name: 'Ouvrir le congé Paid leave' })).toHaveTextContent('Ada Reader')
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    expect(screen.getByTestId('calendar')).toHaveAttribute('data-view', 'resourceTimelineMonthCustom')
    expect(screen.getByRole('button', { name: 'Paid leave' })).toHaveAttribute('data-resource', '12')
    expect(screen.getByRole('button', { name: 'Holiday' })).toHaveAttribute('data-resource', '12')
    await user.click(screen.getByRole('button', { name: 'Paid leave' }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Family')
    expect(screen.queryByRole('button', { name: 'Modifier l’absence' })).not.toBeInTheDocument()
  })

  it('offers contextual creation only for editable Participants', async () => {
    const fetchMock = mockApi(true)
    const user = userEvent.setup()
    render(<I18nProvider><ProjectCalendarPanel projectId="4" /></I18nProvider>)
    await screen.findByRole('button', { name: 'Ajouter une absence' })
    await user.click(screen.getByRole('button', { name: 'Paid leave' }))
    expect(await screen.findByRole('button', { name: 'Modifier l’absence' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Fermer' }))
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    await user.click(screen.getByRole('button', { name: 'Select range' }))
    const sheet = await screen.findByRole('dialog')
    expect(sheet).toHaveTextContent('Employé')
    expect(screen.getByLabelText('Employé')).toHaveValue('12')
    expect(screen.getByLabelText('Début')).toHaveValue('2026-09-20')
    expect(screen.getByLabelText('Fin')).toHaveValue('2026-09-21')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/leave-types/'))).toBe(true))
  })

  it.each([
    ['fifteenDays', '15 jours'], ['month', 'Mois'], ['twoMonths', '2 mois'], ['year', 'Année'],
  ] as Array<[ProjectCalendarScope, string]>)('opens the existing Leave Sheet from a timed Resource selection in %s', async (_scope, label) => {
    mockApi(true)
    const user = userEvent.setup()
    render(<I18nProvider><ProjectCalendarPanel projectId="4" /></I18nProvider>)
    await screen.findByRole('button', { name: 'Ajouter une absence' })
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    await user.click(screen.getByRole('button', { name: label }))
    await user.click(screen.getByRole('button', { name: 'Select timed range' }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText('Employé')).toHaveValue('12')
    expect(screen.getByLabelText('Début')).toHaveValue('2026-09-20')
    expect(screen.getByLabelText('Fin')).toHaveValue('2026-09-22')
  })

  it('does not open creation for a Resource without Employee capability', async () => {
    mockApi(true, true)
    const user = userEvent.setup()
    render(<I18nProvider><ProjectCalendarPanel projectId="4" /></I18nProvider>)
    await screen.findByRole('button', { name: 'Ajouter une absence' })
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    await user.click(screen.getByRole('button', { name: 'Select read-only resource' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it.each(['calendar', 'resources'] as const)('uses all four scopes in %s with matching API bounds and one event per source', async (mode) => {
    const fetchMock = mockApi(false)
    const user = userEvent.setup()
    const anchor = new Date()
    render(<I18nProvider><ProjectCalendarPanel projectId="4" /></I18nProvider>)
    await screen.findByTestId('calendar')
    if (mode === 'resources') await user.click(screen.getByRole('button', { name: 'Ressources' }))
    const cases: Array<[ProjectCalendarScope, string]> = [
      ['fifteenDays', '15 jours'], ['month', 'Mois'], ['twoMonths', '2 mois'], ['year', 'Année'],
    ]
    for (const [scope, label] of cases) {
      await user.click(screen.getByRole('button', { name: label }))
      await waitFor(() => expect(screen.getByTestId('calendar')).toHaveAttribute('data-view', projectCalendarScopes[scope][mode === 'calendar' ? 'calendarView' : 'resourceView']))
      const range = projectCalendarRange(scope, anchor)
      await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`/calendar/?from=${range.from}&to=${range.to}`))).toBe(true))
      expect(screen.getAllByRole('button', { name: 'Paid leave' })).toHaveLength(1)
      expect(screen.getAllByRole('button', { name: 'Holiday' })).toHaveLength(1)
      if (mode === 'resources') {
        expect(screen.getByText('Ada Reader')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Paid leave' })).toHaveAttribute('data-resource', '12')
      }
      if (scope === 'fifteenDays' || scope === 'twoMonths') expect(screen.getByTestId('calendar')).toHaveAttribute('data-duration', JSON.stringify(projectCalendarScopes[scope].duration))
    }
  })

  it('advances and goes back by the active 15-day period, reloading its exact bounds', async () => {
    const fetchMock = mockApi(false)
    const user = userEvent.setup()
    const anchor = new Date()
    render(<I18nProvider><ProjectCalendarPanel projectId="4" /></I18nProvider>)
    await screen.findByTestId('calendar')
    await user.click(screen.getByRole('button', { name: '15 jours' }))
    await user.click(screen.getByRole('button', { name: 'Période suivante' }))
    const next = projectCalendarRange('fifteenDays', shiftProjectCalendarAnchor(anchor, 'fifteenDays', 1))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes(`/calendar/?from=${next.from}&to=${next.to}`))).toBe(true))
    const callsBeforePrevious = fetchMock.mock.calls.length
    await user.click(screen.getByRole('button', { name: 'Période précédente' }))
    const current = projectCalendarRange('fifteenDays', anchor)
    await waitFor(() => expect(fetchMock.mock.calls.slice(callsBeforePrevious).some(([url]) => String(url).includes(`/calendar/?from=${current.from}&to=${current.to}`))).toBe(true))
  })

  it('reuses all calendar views and member resources for a Team', async () => {
    const fetchMock = mockApi(true, true)
    const user = userEvent.setup()
    render(<I18nProvider><ProjectCalendarPanel teamId="8" /></I18nProvider>)
    expect(await screen.findByTestId('calendar')).toHaveAttribute('data-view', 'dayGridMonthCustom')
    expect(screen.getByRole('button', { name: 'Paid leave' })).toHaveAttribute('data-editable', 'true')
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/teams/8/calendar/?'))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Ressources' }))
    expect(screen.getByText('Ada Reader')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Paid leave' })).toHaveAttribute('data-resource', '12')
    expect(screen.getByRole('button', { name: 'Paid leave' })).toHaveAttribute('data-editable', 'true')
    expect(screen.getByRole('button', { name: 'Holiday' })).toHaveAttribute('data-editable', 'false')
    await user.click(screen.getByRole('button', { name: '2 mois' }))
    expect(screen.getByTestId('calendar')).toHaveAttribute('data-view', 'resourceTimelineTwoMonths')
    expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith('/api/v1/projects/8/'))).toBe(false)
  })
})
