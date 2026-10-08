import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DashboardDeadlineData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { DeadlineListRenderer } from './DeadlineListRenderer'
import { AlertListRenderer, CompactListRenderer } from './PilotRenderers'
import { getDashboardRenderer } from './renderers'

const data: DashboardDeadlineData = {
  summary: { count: 6, overdue_count: 1, due_soon_count: 2 },
  items: [
    { key: '1', label: 'Ethics approval', project_name: 'NUMETAB', date: '2026-10-15', href: '/app/projects/1/tasks', days_until: -7, state: 'overdue' },
    { key: '2', label: 'Final report', project_name: 'MIGAD', date: '2026-10-22', href: '/app/projects/2/tasks', days_until: 0, state: 'today' },
    { key: '3', label: 'Omics delivery', project_name: 'PreciseIT', date: '2026-11-04', href: '/app/projects/3/tasks', days_until: 3, state: 'due_soon' },
    { key: '4', label: 'Long-term review', project_name: 'Future', date: '2027-01-15', href: '/app/projects/4/tasks', days_until: 99, state: 'upcoming' },
    { key: '5', label: 'Grant closure', project_name: 'Done', date: '2026-09-01', href: '/app/projects/5/tasks', days_until: -37, state: 'completed' },
    { key: '6', label: 'Undated', project_name: 'No date', date: null, href: '/app/projects/6/tasks', days_until: null, state: 'unscheduled' },
  ],
}
const widget = (payload: unknown, renderer_key = 'deadline-list'): DashboardWidget => ({
  id: 'one', definition_key: 'core.milestones', source_key: 'core.milestones', renderer_key,
  title: '', config: {}, x: 0, y: 0, width: 6, height: 5, logical_order: 0, available: true, data: payload, error: false,
})

describe('deadline-list dashboard renderer', () => {
  it('resolves from the existing renderer registry, including print', () => {
    expect(getDashboardRenderer('deadline-list')).toBe(DeadlineListRenderer)
    expect(getDashboardRenderer('deadline-list', 'print')).toBe(DeadlineListRenderer)
  })

  it('shows a strong summary and two prioritized rows in compact size', () => {
    render(<I18nProvider><DeadlineListRenderer widget={widget(data)} size="compact" /></I18nProvider>)
    expect(screen.getByText('6')).toBeInTheDocument()
    expect(screen.getByText('items in scope')).toBeInTheDocument()
    expect(screen.getByText('Ethics approval')).toBeInTheDocument()
    expect(screen.getByText('Final report')).toBeInTheDocument()
    expect(screen.queryByText('Omics delivery')).not.toBeInTheDocument()
    expect(screen.queryByText('NUMETAB')).not.toBeInTheDocument()
  })

  it('renders dates, projects, relative urgency and links in standard size', () => {
    render(<I18nProvider><DeadlineListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('NUMETAB')).toBeInTheDocument()
    expect(screen.getByText('7 days overdue')).toBeInTheDocument()
    expect(screen.getByText('Due today')).toBeInTheDocument()
    expect(screen.getByText('in 3 days')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ethics approval' })).toHaveAttribute('href', '/app/projects/1/tasks')
    expect(screen.queryByText('Undated')).not.toBeInTheDocument()
  })

  it('shows all bounded rows expanded, in presentation and in print without links', () => {
    const view = render(<I18nProvider><DeadlineListRenderer widget={widget(data)} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Undated')).toBeInTheDocument()
    view.rerender(<I18nProvider><DeadlineListRenderer widget={widget(data)} size="standard" mode="presentation" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Final report' })).toBeInTheDocument()
    view.rerender(<I18nProvider><DeadlineListRenderer widget={widget(data)} size="standard" mode="print" /></I18nProvider>)
    expect(screen.getByText('Undated')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ethics approval' })).not.toBeInTheDocument()
  })

  it('keeps milestone compact and alert lists distinct from the enhanced timeline', () => {
    const view = render(<I18nProvider><DeadlineListRenderer widget={widget({ summary: { count: 0, overdue_count: 0, due_soon_count: 0 }, items: [] })} size="standard" /></I18nProvider>)
    expect(screen.getByText('No content yet.')).toBeInTheDocument()
    const listData = { items: [{ key: '1', label: 'Ethics approval', severity: 'danger' as const }], deadline: data }
    view.rerender(<I18nProvider><CompactListRenderer widget={widget(listData, 'compact-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-compact')).toBeInTheDocument()
    expect(screen.getByText('Ethics approval')).toBeInTheDocument()
    expect(screen.queryByText('items in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><AlertListRenderer widget={widget(listData, 'alert-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-alert')).toBeInTheDocument()
    expect(screen.getByText('Ethics approval')).toBeInTheDocument()
    expect(screen.queryByText('items in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><DeadlineListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('items in scope')).toBeInTheDocument()
  })
})
