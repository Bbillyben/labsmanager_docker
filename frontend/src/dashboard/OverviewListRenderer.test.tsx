import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DashboardOverviewData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { OverviewListRenderer } from './OverviewListRenderer'
import { CompactListRenderer, ProgressListRenderer } from './PilotRenderers'
import { getDashboardRenderer } from './renderers'

const data: DashboardOverviewData = {
  summary: { amount: 1000, spent: 400, percent: 40, count: 4, count_label: 'Funds', attention_count: 1 },
  items: [
    { key: '1', label: 'ANR', href: '/app/projects/1/funding', current: 40, total: 100, percent: 40, remaining_days: 10, status: 'ending_soon' },
    { key: '2', label: 'FRAME', current: 30, total: 100, percent: 30, remaining_days: 60, status: 'normal' },
    { key: '3', label: 'BT1D', current: 20, total: 100, percent: 20, remaining_days: 90, status: 'normal' },
    { key: '4', label: 'Other', current: 10, total: 100, percent: 10, remaining_days: null, status: 'normal' },
  ],
}
const widget = (payload: unknown, renderer_key = 'overview-list'): DashboardWidget => ({
  id: 'one', definition_key: 'core.funds', source_key: 'core.funds', renderer_key, title: '', config: {},
  x: 0, y: 0, width: 4, height: 3, logical_order: 0, available: true, data: payload, error: false,
})

describe('overview-list dashboard renderer', () => {
  it('resolves locally for view and print', () => {
    expect(getDashboardRenderer('overview-list')).toBe(OverviewListRenderer)
    expect(getDashboardRenderer('overview-list', 'print')).toBe(OverviewListRenderer)
  })

  it('shows a compact hierarchy with only two rows', () => {
    render(<I18nProvider><OverviewListRenderer widget={widget(data)} size="compact" /></I18nProvider>)
    expect(screen.getByText('Total')).toBeInTheDocument()
    expect(screen.getAllByText('40 %')).toHaveLength(2)
    expect(screen.getByText('ANR')).toBeInTheDocument()
    expect(screen.getByText('FRAME')).toBeInTheDocument()
    expect(screen.queryByText('BT1D')).not.toBeInTheDocument()
    expect(screen.queryByText('Funds')).not.toBeInTheDocument()
  })

  it('shows three rows, textual progress, deadline and attention in standard size', () => {
    render(<I18nProvider><OverviewListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('Funds')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Overall consumption' })).toHaveAttribute('value', '40')
    expect(screen.getByRole('progressbar', { name: 'Consumption of ANR' })).toHaveAttribute('value', '40')
    expect(screen.getByRole('link', { name: 'ANR' })).toHaveAttribute('href', '/app/projects/1/funding')
    expect(screen.getByText('10 days remaining')).toBeInTheDocument()
    expect(screen.getByText('Ending soon')).toBeInTheDocument()
    expect(screen.getByText('Require attention: 1')).toBeInTheDocument()
    expect(screen.queryByText('Other')).not.toBeInTheDocument()
  })

  it('shows configured rows in expanded and presentation, and all rows without links in print', () => {
    const view = render(<I18nProvider><OverviewListRenderer widget={widget(data)} size="expanded" /></I18nProvider>)
    expect(screen.getByText('Other')).toBeInTheDocument()
    view.rerender(<I18nProvider><OverviewListRenderer widget={widget(data)} size="standard" mode="presentation" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'ANR' })).toBeInTheDocument()
    view.rerender(<I18nProvider><OverviewListRenderer widget={widget(data)} size="standard" mode="print" /></I18nProvider>)
    expect(screen.getByText('Other')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'ANR' })).not.toBeInTheDocument()
  })

  it('handles empty and unknown consumption without inventing a percentage', () => {
    render(<I18nProvider><OverviewListRenderer widget={widget({ summary: { ...data.summary, amount: 0, spent: 0, percent: null, count: 0, attention_count: 0 }, items: [] })} size="standard" /></I18nProvider>)
    expect(screen.getByText('No content yet.')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Overall consumption' })).toHaveAttribute('value', '0')
  })

  it('keeps Fund compact and progress lists distinct from the enhanced overview', () => {
    const listData = { items: [{ key: 'fund', label: 'ANR', current: 25, total: 100, percent: 25 }], overview: data }
    const view = render(<I18nProvider><CompactListRenderer widget={widget(listData, 'compact-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-compact')).toBeInTheDocument()
    expect(screen.getByText('ANR')).toBeInTheDocument()
    expect(screen.queryByText('Total')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><ProgressListRenderer widget={widget(listData, 'progress-list')} size="standard" /></I18nProvider>)
    expect(view.container.querySelector('.dashboard-list-progress')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'ANR' })).toHaveAttribute('value', '25')
    expect(screen.queryByText('Total')).not.toBeInTheDocument()
    view.rerender(<I18nProvider><OverviewListRenderer widget={widget(data)} size="standard" /></I18nProvider>)
    expect(screen.getByText('Total')).toBeInTheDocument()
  })
})
