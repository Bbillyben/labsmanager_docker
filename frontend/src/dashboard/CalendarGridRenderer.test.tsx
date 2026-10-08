import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { DashboardTimelineData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { CalendarGridRenderer } from './CalendarGridRenderer'
import { getDashboardRenderer } from './renderers'

const data: DashboardTimelineData = {
  window_start: '2026-10-06', today: '2026-10-08', window_end: '2026-10-22', earlier_overdue_count: 3,
  events: [
    { id: 'tasks:1', source_type: 'tasks', source_label: 'Task', date: '2026-10-08', title: 'Prepare report', project_name: 'NUMETAB', secondary: 'Alice Martin', href: '/app/projects/1/tasks', state: 'today', tone: 'warning', icon: 'FolderKanban' },
    { id: 'tasks:2', source_type: 'tasks', source_label: 'Task', date: '2026-10-08', title: 'Review report', project_name: 'NUMETAB', state: 'today', tone: 'warning', icon: 'FolderKanban' },
    { id: 'milestones:3', source_type: 'milestones', source_label: 'Milestone', date: '2026-10-08', title: 'Approval', project_name: 'MIGAD', href: '/app/projects/2/tasks', state: 'soon', tone: 'warning', icon: 'Flag' },
    { id: 'milestones:4', source_type: 'milestones', source_label: 'Milestone', date: '2026-10-10', title: 'Late milestone', project_name: 'MIGAD', state: 'future', tone: 'neutral', icon: 'Flag' },
  ],
}
const widget = { data } as DashboardWidget
const renderGrid = (size: 'compact' | 'standard' | 'expanded' = 'standard', mode: 'view' | 'print' = 'view') => render(<I18nProvider><CalendarGridRenderer widget={widget} size={size} mode={mode} /></I18nProvider>)

describe('Calendar grid renderer', () => {
  it('uses the Timeline payload, renders weekly cells and compact source counts', () => {
    expect(getDashboardRenderer('calendar-grid')).toBe(CalendarGridRenderer)
    expect(getDashboardRenderer('timeline-calendar')).toBeDefined()
    const view = renderGrid()
    expect(view.container.querySelectorAll('[data-date]')).toHaveLength(17)
    expect(screen.getByText(/3 overdue deadlines before/)).toBeInTheDocument()
    const today = view.container.querySelector('[data-date="2026-10-08"]')!
    expect(today).toHaveAttribute('data-today', 'true')
    expect(within(today as HTMLElement).getByLabelText('Task: 2')).toBeInTheDocument()
    expect(within(today as HTMLElement).getByLabelText('Milestone: 1')).toBeInTheDocument()
    expect(view.container.querySelector('[data-date="2026-10-10"]')).toHaveTextContent('1')
    expect(view.container.querySelector('[data-date="2026-10-07"]')).not.toHaveAttribute('type', 'button')
  })

  it('opens only populated days, shows all details, and restores focus without fetching', async () => {
    const user = userEvent.setup()
    const fetch = vi.spyOn(globalThis, 'fetch')
    renderGrid()
    expect(screen.queryByText('Prepare report')).not.toBeInTheDocument()
    const trigger = screen.getByRole('button', { name: /View 3 deadlines on/ })
    trigger.focus()
    await user.click(trigger)
    expect(screen.getByRole('link', { name: 'Prepare report' })).toHaveAttribute('href', '/app/projects/1/tasks')
    expect(screen.getByText('Review report')).toBeInTheDocument()
    expect(screen.getByText('Approval')).toBeInTheDocument()
    expect(screen.getByText('Alice Martin')).toBeInTheDocument()
    expect(screen.getAllByText('NUMETAB')).toHaveLength(2)
    expect(fetch).not.toHaveBeenCalled()
    await user.keyboard('{Escape}')
    expect(trigger).toHaveFocus()
    fetch.mockRestore()
  })

  it('keeps the same dates in all sizes and prints visible counts without buttons', () => {
    for (const size of ['compact', 'standard', 'expanded'] as const) {
      const view = renderGrid(size)
      expect(view.container.querySelectorAll('[data-date]')).toHaveLength(17)
      expect(view.container.querySelector('[data-date="2026-10-08"]')).toBeTruthy()
      view.unmount()
    }
    const print = renderGrid('standard', 'print')
    expect(print.container.querySelectorAll('[data-date]')).toHaveLength(17)
    expect(screen.queryByRole('button', { name: /View 3 deadlines on/ })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Task: 2')).toBeInTheDocument()
  })

  it('keeps a seven-column grid for every configured horizon', () => {
    for (const horizon of [14, 21, 30, 60]) {
      const end = new Date(Date.UTC(2026, 9, 8 + horizon)).toISOString().slice(0, 10)
      const longWidget = { data: { ...data, window_end: end } } as DashboardWidget
      const view = render(<I18nProvider><CalendarGridRenderer widget={longWidget} size="compact" /></I18nProvider>)
      expect(view.container.querySelectorAll('[data-date]')).toHaveLength(horizon + 3)
      view.unmount()
    }
  })
})
