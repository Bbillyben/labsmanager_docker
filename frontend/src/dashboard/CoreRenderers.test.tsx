import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import type { DashboardWidget } from '../api/dashboards'
import { dashboardSize } from './size'
import { AlertListRenderer, CompactListRenderer, KpiRenderer, ProgressListRenderer } from './PilotRenderers'
import { LineChartRenderer } from './LineChartRenderer'

const widget = (data: unknown): DashboardWidget => ({ id: 'one', definition_key: 'test', source_key: 'test', renderer_key: 'kpi', title: '', config: {}, x: 0, y: 0, width: 4, height: 3, logical_order: 0, available: true, data, error: false })

describe('core dashboard renderers', () => {
  it('uses the shared size variants', () => {
    expect(dashboardSize(2, 3)).toBe('compact')
    expect(dashboardSize(4, 3)).toBe('standard')
    expect(dashboardSize(8, 5)).toBe('expanded')
  })
  it('renders KPI semantics and adapts detail to size', () => {
    const data = { value: 7, label: 'Projects', context: 'Current scope', secondary: 'Updated today', tone: 'positive' }
    const view = render(<I18nProvider><KpiRenderer widget={widget(data)} size="compact" /></I18nProvider>)
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.queryByText('Current scope')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><KpiRenderer widget={widget(data)} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Current scope')).toBeInTheDocument()
    expect(screen.getByText('Updated today')).toBeInTheDocument()
  })
  it('renders compact, alert and progress lists from normalized items', () => {
    const data = { items: [{ key: 'a', label: 'Alpha', secondary: 'Detail', href: '/app/projects/1/', severity: 'warning', percent: 40 }] }
    const view = render(<I18nProvider><CompactListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Alpha' })).toHaveAttribute('href', '/app/projects/1/')
    view.rerender(<I18nProvider><AlertListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('Warning')).toBeInTheDocument()
    view.rerender(<I18nProvider><ProgressListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByRole('progressbar', { name: 'Alpha' })).toHaveAttribute('value', '40')
  })
  it('shows an empty state for a list without items', () => {
    render(<I18nProvider><CompactListRenderer widget={widget({ items: [] })} size="standard" /></I18nProvider>)
    expect(screen.getByText('No content yet.')).toBeInTheDocument()
  })
  it('renders a centered financial ratio without hiding the actual value', () => {
    render(<I18nProvider><KpiRenderer widget={widget({ value: '3.40', label: 'Financial advancement', centered_ratio: 3.4, budget_percent: 90, time_percent: 27 })} size="standard" /></I18nProvider>)
    expect(screen.getByText('3.40')).toBeInTheDocument()
    expect(screen.getByRole('img')).toBeInTheDocument()
    expect(document.querySelector('.dashboard-centered-ratio-marker')).toHaveStyle({ left: '100%' })
  })
  it('plots multiple dated series with an accessible value table', () => {
    render(<I18nProvider><LineChartRenderer widget={widget({ series: [
      { key: 'spent', label: 'Spent', points: [{ date: '2026-01-01', value: 10 }, { date: '2026-02-01', value: 20 }] },
      { key: 'target', label: 'Target', kind: 'reference', points: [{ date: '2026-01-01', value: 12 }, { date: '2026-02-01', value: 24 }] },
    ] })} size="expanded" /></I18nProvider>)
    expect(screen.getByRole('img')).toBeInTheDocument()
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Spent' })).toBeInTheDocument()
    expect(document.querySelectorAll('polyline')).toHaveLength(2)
  })
})
