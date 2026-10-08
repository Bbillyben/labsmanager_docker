import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DashboardContractData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { ContractListRenderer } from './ContractListRenderer'
import { AlertListRenderer, CompactListRenderer } from './PilotRenderers'
import { getDashboardRenderer } from './renderers'

const data: DashboardContractData = {
  summary: { count: 8, ending_soon_count: 2, stale_count: 3 },
  items: [
    { key: '1', employee_name: 'Alice Martin', employee_href: '/app/employees/1', contract_type: 'CDD', project_name: 'NUMETAB', project_href: '/app/projects/1', date: '2026-10-31', days_until: 23, state: 'ending_soon' },
    { key: '2', employee_name: 'Bob Dupont', employee_href: '/app/employees/2', contract_type: 'Postdoc', project_name: 'PreciseIT', project_href: '/app/projects/2', date: '2026-11-12', days_until: 35, state: 'stale' },
    { key: '3', employee_name: 'Carol Other', employee_href: null, contract_type: '', project_name: 'Hidden project', project_href: null, date: '2027-05-01', days_until: 200, state: 'current' },
    { key: '4', employee_name: 'Dan Ended', employee_href: null, contract_type: '', project_name: 'Old', project_href: null, date: '2026-09-01', days_until: -37, state: 'ended' },
    { key: '5', employee_name: 'Eva Fifth', employee_href: null, contract_type: '', project_name: 'Other', project_href: null, date: null, days_until: null, state: 'no_date' },
    { key: '6', employee_name: 'Fran Sixth', employee_href: null, contract_type: '', project_name: 'Other', project_href: null, date: null, days_until: null, state: 'no_date' },
  ],
}
const widget = (payload: unknown, renderer_key = 'contract-list'): DashboardWidget => ({
  id: 'one', definition_key: 'core.contracts', source_key: 'core.contracts', renderer_key,
  title: '', config: {}, x: 0, y: 0, width: 6, height: 5, logical_order: 0, available: true, data: payload, error: false,
})

describe('contract overview dashboard renderer', () => {
  it('is available through the registry in view and print', () => {
    expect(getDashboardRenderer('contract-list')).toBe(ContractListRenderer)
    expect(getDashboardRenderer('contract-list', 'print')).toBe(ContractListRenderer)
  })

  it('shows a compact summary and two priority contracts', () => {
    render(<I18nProvider><ContractListRenderer widget={widget(data)} size="compact" /></I18nProvider>)
    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('contracts in scope')).toBeInTheDocument()
    expect(screen.getByText('Alice Martin')).toBeInTheDocument()
    expect(screen.getByText('Bob Dupont')).toBeInTheDocument()
    expect(screen.queryByText('Carol Other')).not.toBeInTheDocument()
    expect(screen.queryByText('NUMETAB')).not.toBeInTheDocument()
  })

  it('shows Employee and Project links with due states in standard size', () => {
    render(<I18nProvider><ContractListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Alice Martin' })).toHaveAttribute('href', '/app/employees/1')
    expect(screen.getByRole('link', { name: 'NUMETAB' })).toHaveAttribute('href', '/app/projects/1')
    expect(screen.getByText('CDD')).toBeInTheDocument()
    expect(screen.getByText('in 23 days')).toBeInTheDocument()
    expect(screen.getByText('Postdoc')).toBeInTheDocument()
    expect(screen.getByText('Hidden project')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Hidden project' })).not.toBeInTheDocument()
    expect(screen.queryByText('Fran Sixth')).not.toBeInTheDocument()
  })

  it('uses all configured rows expanded or printed, while print removes links', () => {
    const view = render(<I18nProvider><ContractListRenderer widget={widget(data)} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Fran Sixth')).toBeInTheDocument()
    view.rerender(<I18nProvider><ContractListRenderer widget={widget(data)} size="standard" mode="presentation" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Alice Martin' })).toBeInTheDocument()
    view.rerender(<I18nProvider><ContractListRenderer widget={widget(data)} size="standard" mode="print" /></I18nProvider>)
    expect(screen.getByText('Fran Sixth')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Alice Martin' })).not.toBeInTheDocument()
  })

  it('keeps Contract compact and alert lists distinct from the enhanced cards', () => {
    const listData = { items: [{ key: '1', label: 'Alice Martin', severity: 'warning' as const }], contracts: data }
    const view = render(<I18nProvider><CompactListRenderer widget={widget(listData, 'compact-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-compact')).toBeInTheDocument()
    expect(screen.getByText('Alice Martin')).toBeInTheDocument()
    expect(screen.queryByText('contracts in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><AlertListRenderer widget={widget(listData, 'alert-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-alert')).toBeInTheDocument()
    expect(screen.getByText('Alice Martin')).toBeInTheDocument()
    expect(screen.queryByText('contracts in scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><ContractListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('contracts in scope')).toBeInTheDocument()
  })
})
