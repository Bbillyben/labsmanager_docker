import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DashboardEmployeeMovementsData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { EmployeeMovementsRenderer } from './EmployeeMovementsRenderer'
import { AlertListRenderer, CompactListRenderer } from './PilotRenderers'
import { getDashboardRenderer } from './renderers'

const data: DashboardEmployeeMovementsData = {
  summary: { count: 12, arrivals_count: 3, departures_count: 2 },
  items: [
    { key: '1', name: 'Alice Martin', href: '/app/employees/1', role: 'Postdoc', team_name: 'Team A', team_href: '/app/teams/1', state: 'arriving', date: '2026-10-14', days_until: 6 },
    { key: '2', name: 'Bob Dupont', href: '/app/employees/2', role: 'Engineer', team_name: 'Team B', team_href: '/app/teams/2', state: 'leaving', date: '2026-10-31', days_until: 23 },
    { key: '3', name: 'Carol Recent', href: '/app/employees/3', role: null, team_name: null, team_href: null, state: 'arrived_recently', date: '2026-10-01', days_until: -7 },
    { key: '4', name: 'Dan Active', href: '/app/employees/4', role: null, team_name: null, team_href: null, state: 'active', date: null, days_until: null },
    { key: '5', name: 'Eva Inactive', href: '/app/employees/5', role: null, team_name: null, team_href: null, state: 'inactive', date: null, days_until: null },
    { key: '6', name: 'Fran Sixth', href: '/app/employees/6', role: null, team_name: null, team_href: null, state: 'departed', date: '2026-09-01', days_until: -37 },
  ],
}
const widget = (payload: unknown, renderer_key = 'employee-movements'): DashboardWidget => ({
  id: 'one', definition_key: 'core.employees', source_key: 'core.employees', renderer_key,
  title: '', config: {}, x: 0, y: 0, width: 6, height: 5, logical_order: 0, available: true, data: payload, error: false,
})

describe('employee movements dashboard renderer', () => {
  it('is registered for normal view and print', () => {
    expect(getDashboardRenderer('employee-movements')).toBe(EmployeeMovementsRenderer)
    expect(getDashboardRenderer('employee-movements', 'print')).toBe(EmployeeMovementsRenderer)
  })

  it('shows the scope summary and two priority movements in compact size', () => {
    render(<I18nProvider><EmployeeMovementsRenderer widget={widget(data)} size="compact" /></I18nProvider>)
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('employees in scope')).toBeInTheDocument()
    expect(screen.getByText('Alice Martin')).toBeInTheDocument()
    expect(screen.getByText('Bob Dupont')).toBeInTheDocument()
    expect(screen.getByText('in 6 days')).toBeInTheDocument()
    expect(screen.queryByText('Postdoc')).not.toBeInTheDocument()
    expect(screen.queryByText('Carol Recent')).not.toBeInTheDocument()
  })

  it('shows role, Team and movement dates in standard size', () => {
    render(<I18nProvider><EmployeeMovementsRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Alice Martin' })).toHaveAttribute('href', '/app/employees/1')
    expect(screen.getByRole('link', { name: 'Team A' })).toHaveAttribute('href', '/app/teams/1')
    expect(screen.getByText('Postdoc')).toBeInTheDocument()
    expect(screen.getByText('Engineer')).toBeInTheDocument()
    expect(screen.getAllByText('Arrival')).toHaveLength(2)
    expect(screen.getByText('Departure')).toBeInTheDocument()
    expect(screen.getByText('7 days ago')).toBeInTheDocument()
    expect(screen.queryByText('Fran Sixth')).not.toBeInTheDocument()
  })

  it('shows configured rows expanded and all rows in print without links', () => {
    const view = render(<I18nProvider><EmployeeMovementsRenderer widget={widget(data)} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Fran Sixth')).toBeInTheDocument()
    view.rerender(<I18nProvider><EmployeeMovementsRenderer widget={widget(data)} size="standard" mode="presentation" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Alice Martin' })).toBeInTheDocument()
    view.rerender(<I18nProvider><EmployeeMovementsRenderer widget={widget(data)} size="standard" mode="print" /></I18nProvider>)
    expect(screen.getByText('Fran Sixth')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Alice Martin' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Team A' })).not.toBeInTheDocument()
  })

  it('keeps compact and alert lists distinct from the enhanced renderer', () => {
    const list = { items: [{ key: '1', label: 'Alice Martin', severity: 'info' as const }] }
    const view = render(<I18nProvider><CompactListRenderer widget={widget(list, 'compact-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-compact')).toBeInTheDocument()
    expect(screen.queryByText('employees in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><AlertListRenderer widget={widget(list, 'alert-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-alert')).toBeInTheDocument()
    expect(screen.queryByText('employees in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><EmployeeMovementsRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('employees in scope')).toBeInTheDocument()
  })
})
