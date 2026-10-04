import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { CalendarEvent } from '../api/employees'
import { I18nProvider } from '../i18n/I18nProvider'
import { SharedCalendar, type ResourceVisibilityMode } from './SharedCalendar'

vi.mock('@fullcalendar/react', () => ({
  default: function MockCalendar({ initialView, resources, events }: { initialView: string; resources?: Array<{ id: string; title: string }>; events: Array<{ id: string; resourceId?: string; resourceIds?: string[] }> }) {
    return <div data-testid="calendar-render" data-view={initialView}>
      {resources?.map((item) => <span data-resource-id={item.id} key={item.id}>{item.title}</span>)}
      {events.map((item) => <span data-event-id={item.id} data-resource={item.resourceId ?? item.resourceIds?.join(',')} key={item.id} />)}
    </div>
  },
}))

const resources = [{ id: '1', title: 'Ada' }, { id: '2', title: 'Bea' }]
const event = (id: string, start: string, metadata: Record<string, unknown>): CalendarEvent => ({ id, title: id, start, end: null, source: 'core', kind: 'leave', all_day: true, color: null, description: null, display: 'auto', metadata })
const periodEvents = [event('ada', '2026-10-05', { employee_id: 1, leave_id: 1 }), { ...event('holiday', '2026-10-05', {}), source: 'plugin', kind: 'holiday', display: 'background' }]
const todayEvents = [event('bea-today', '2026-10-03', { employee_id: 2, leave_id: 2 })]

function Harness() {
  const [scope, setScope] = useState<'month' | 'year'>('month')
  const [viewMode, setViewMode] = useState<'calendar' | 'resources'>('resources')
  const [visibilityMode, setVisibilityMode] = useState<ResourceVisibilityMode>('period')
  return <I18nProvider>
    <button onClick={() => setScope(scope === 'month' ? 'year' : 'month')}>Switch scope</button>
    <button onClick={() => setViewMode(viewMode === 'resources' ? 'calendar' : 'resources')}>Switch view</button>
    <SharedCalendar anchor={new Date(2026, 9, 1)} scope={scope} viewMode={viewMode} events={periodEvents} todayEvents={todayEvents} resources={resources} resourceVisibilityMode={visibilityMode} onResourceVisibilityModeChange={setVisibilityMode} />
  </I18nProvider>
}

describe('SharedCalendar Resource control', () => {
  it('defaults to period, supports all/today, and keeps the mode across scope and view changes', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const select = screen.getByRole('combobox')
    expect(select).toHaveValue('period')
    expect(screen.getAllByTestId('calendar-render')[0].querySelectorAll('[data-resource-id]')).toHaveLength(1)
    expect(screen.getByTestId('calendar-render').querySelector('[data-event-id="holiday"]')).toHaveAttribute('data-resource', '1')
    await user.selectOptions(select, 'all')
    expect(screen.getByTestId('calendar-render').querySelectorAll('[data-resource-id]')).toHaveLength(2)
    await user.selectOptions(select, 'today')
    expect(screen.getByTestId('calendar-render').querySelector('[data-resource-id="2"]')).toBeInTheDocument()
    expect(screen.getByTestId('calendar-render').querySelector('[data-resource-id="1"]')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch scope' }))
    expect(select).toHaveValue('today')
    expect(screen.getByTestId('calendar-render')).toHaveAttribute('data-view', 'resourceTimelineYearCustom')
    await user.click(screen.getByRole('button', { name: 'Switch view' }))
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch view' }))
    expect(screen.getByRole('combobox')).toHaveValue('today')
  })

  it('recalculates period rows after changing the visible month', () => {
    const { rerender } = render(<I18nProvider><SharedCalendar anchor={new Date(2026, 9, 1)} scope="month" viewMode="resources" events={periodEvents} resources={resources} /></I18nProvider>)
    expect(screen.getByTestId('calendar-render').querySelector('[data-resource-id="1"]')).toBeInTheDocument()
    rerender(<I18nProvider><SharedCalendar anchor={new Date(2026, 10, 1)} scope="month" viewMode="resources" events={periodEvents} resources={resources} /></I18nProvider>)
    expect(screen.getByTestId('calendar-render').querySelectorAll('[data-resource-id]')).toHaveLength(0)
  })

  it('renders an explicitly scoped background event on each of its resources', () => {
    const background = { ...event('shared-background', '2026-10-05', { resource_ids: [1, 2] }), kind: 'holiday', source: 'plugin', display: 'background' }
    render(<I18nProvider><SharedCalendar anchor={new Date(2026, 9, 1)} scope="month" viewMode="resources" events={[background]} resources={resources} /></I18nProvider>)
    expect(screen.getByTestId('calendar-render').querySelectorAll('[data-resource-id]')).toHaveLength(2)
    expect(screen.getByTestId('calendar-render').querySelector('[data-event-id="shared-background"]')).toHaveAttribute('data-resource', '1,2')
  })
})
