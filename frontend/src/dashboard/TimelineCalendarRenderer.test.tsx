import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DashboardTimelineData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { getDashboardRenderer } from './renderers'
import { TimelineCalendarRenderer } from './TimelineCalendarRenderer'

const data: DashboardTimelineData = {
  window_start: '2026-10-06', today: '2026-10-08', window_end: '2026-10-15', earlier_overdue_count: 2,
  events: [
    { id: 'tasks:1', source_type: 'tasks', source_label: 'Task', date: '2026-10-08', title: 'Prepare report', project_name: 'NUMETAB', project_href: '/app/projects/1', secondary: 'Alice Martin', href: '/app/projects/1/tasks', state: 'today', tone: 'warning', icon: 'FolderKanban' },
    { id: 'milestones:2', source_type: 'milestones', source_label: 'Milestone', date: '2026-10-10', title: 'Submit report', project_name: 'MIGAD', href: '/app/projects/2/tasks', state: 'soon', tone: 'warning', icon: 'Flag' },
  ],
}
const widget = { data } as DashboardWidget

describe('Timeline calendar', () => {
  it('is registered for viewing and print and locates events by date', () => {
    expect(getDashboardRenderer('timeline-calendar')).toBe(TimelineCalendarRenderer)
    expect(getDashboardRenderer('timeline-calendar', 'print')).toBe(TimelineCalendarRenderer)
    render(<I18nProvider><TimelineCalendarRenderer widget={widget} size="standard" /></I18nProvider>)
    expect(screen.getByText(/2 overdue deadlines before/)).toBeInTheDocument()
    const today = screen.getByRole('link', { name: 'Prepare report' }).closest('section')!
    expect(today).toHaveAttribute('data-today', 'true')
    expect(within(today).getByRole('link', { name: 'Prepare report' })).toBeInTheDocument()
    expect(screen.getByText('Submit report').closest('section')!.querySelector('time')).toHaveAttribute('dateTime', '2026-10-10')
  })

  it('varies context by size without changing the horizon and keeps print readable', () => {
    const view = render(<I18nProvider><TimelineCalendarRenderer widget={widget} size="compact" /></I18nProvider>)
    expect(screen.queryByText('NUMETAB')).not.toBeInTheDocument()
    expect(view.container.querySelectorAll('section')).toHaveLength(10)
    view.rerender(<I18nProvider><TimelineCalendarRenderer widget={widget} size="standard" mode="presentation" /></I18nProvider>)
    expect(screen.getByText('NUMETAB')).toBeInTheDocument()
    expect(screen.queryByText('Alice Martin')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><TimelineCalendarRenderer widget={widget} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Alice Martin')).toBeInTheDocument()
    view.rerender(<I18nProvider><TimelineCalendarRenderer widget={widget} size="expanded" mode="print" /></I18nProvider>)
    expect(screen.queryByRole('link', { name: 'Prepare report' })).not.toBeInTheDocument()
    expect(screen.getByText('Prepare report')).toBeInTheDocument()
  })
})
