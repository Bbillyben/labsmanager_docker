import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DashboardTaskWorkloadData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { AlertListRenderer, CompactListRenderer } from './PilotRenderers'
import { getDashboardRenderer } from './renderers'
import { TaskWorkloadRenderer } from './TaskWorkloadRenderer'

const data: DashboardTaskWorkloadData = {
  summary: { count: 18, overdue_count: 5, due_soon_count: 4 },
  items: [
    { key: '1', title: 'Critical analysis', href: '/app/projects/1/tasks', project_name: 'NUMETAB', project_href: '/app/projects/1', assignees: [{ id: 1, name: 'Alice Martin', href: '/app/employees/1' }], date: '2026-10-05', days_until: -3, state: 'overdue' },
    { key: '2', title: 'Prepare final report', href: '/app/projects/2/tasks', project_name: 'MIGAD', project_href: '/app/projects/2', assignees: [{ id: 2, name: 'Bob Dupont', href: null }], date: '2026-10-09', days_until: 1, state: 'due_soon' },
    { key: '3', title: 'Validate samples', href: '/app/projects/3/tasks', project_name: 'PreciseIT', project_href: '/app/projects/3', assignees: [], date: '2026-10-13', days_until: 5, state: 'due_soon' },
    { key: '4', title: 'Later work', href: '/app/projects/4/tasks', project_name: 'Later', project_href: '/app/projects/4', assignees: [], date: '2027-01-01', days_until: 85, state: 'later' },
    { key: '5', title: 'Done work', href: '/app/projects/5/tasks', project_name: 'Done', project_href: '/app/projects/5', assignees: [], date: '2026-09-01', days_until: -37, state: 'done' },
    { key: '6', title: 'Unscheduled work', href: '/app/projects/6/tasks', project_name: 'Undated', project_href: '/app/projects/6', assignees: [], date: null, days_until: null, state: 'unscheduled' },
  ],
}
const widget = (payload: unknown, renderer_key = 'task-workload'): DashboardWidget => ({
  id: 'one', definition_key: 'core.tasks', source_key: 'core.tasks', renderer_key,
  title: '', config: {}, x: 0, y: 0, width: 6, height: 5, logical_order: 0, available: true, data: payload, error: false,
})

describe('task workload dashboard renderer', () => {
  it('is registered for normal view and print', () => {
    expect(getDashboardRenderer('task-workload')).toBe(TaskWorkloadRenderer)
    expect(getDashboardRenderer('task-workload', 'print')).toBe(TaskWorkloadRenderer)
  })

  it('shows workload counts and two urgent tasks in compact size', () => {
    render(<I18nProvider><TaskWorkloadRenderer widget={widget(data)} size="compact" /></I18nProvider>)
    expect(screen.getByText('18')).toBeInTheDocument()
    expect(screen.getByText('tasks in scope')).toBeInTheDocument()
    expect(screen.getByText('Critical analysis')).toBeInTheDocument()
    expect(screen.getByText('Prepare final report')).toBeInTheDocument()
    expect(screen.getByText('3 days overdue')).toBeInTheDocument()
    expect(screen.getByText('due tomorrow')).toBeInTheDocument()
    expect(screen.queryByText('Validate samples')).not.toBeInTheDocument()
    expect(screen.queryByText('NUMETAB')).not.toBeInTheDocument()
  })

  it('preserves Project and assignee context in standard size', () => {
    render(<I18nProvider><TaskWorkloadRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Critical analysis' })).toHaveAttribute('href', '/app/projects/1/tasks')
    expect(screen.getByRole('link', { name: 'NUMETAB' })).toHaveAttribute('href', '/app/projects/1')
    expect(screen.getByRole('link', { name: 'Alice Martin' })).toHaveAttribute('href', '/app/employees/1')
    expect(screen.getByText('Bob Dupont')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Bob Dupont' })).not.toBeInTheDocument()
    expect(screen.getByText('in 5 days')).toBeInTheDocument()
    expect(screen.queryByText('Unscheduled work')).not.toBeInTheDocument()
  })

  it('shows all bounded rows expanded and all rows without links in print', () => {
    const view = render(<I18nProvider><TaskWorkloadRenderer widget={widget(data)} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Unscheduled work')).toBeInTheDocument()
    view.rerender(<I18nProvider><TaskWorkloadRenderer widget={widget(data)} size="standard" mode="presentation" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Critical analysis' })).toBeInTheDocument()
    view.rerender(<I18nProvider><TaskWorkloadRenderer widget={widget(data)} size="standard" mode="print" /></I18nProvider>)
    expect(screen.getByText('Unscheduled work')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Critical analysis' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Alice Martin' })).not.toBeInTheDocument()
  })

  it('keeps compact and alert lists generic', () => {
    const list = { items: [{ key: '1', label: 'Critical analysis', severity: 'danger' as const }] }
    const view = render(<I18nProvider><CompactListRenderer widget={widget(list, 'compact-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-compact')).toBeInTheDocument()
    expect(screen.queryByText('tasks in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><AlertListRenderer widget={widget(list, 'alert-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-alert')).toBeInTheDocument()
    expect(screen.queryByText('tasks in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><TaskWorkloadRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('tasks in scope')).toBeInTheDocument()
  })
})
