import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import type { DashboardWidget, WidgetDefinition } from '../api/dashboards'
import { getPrintRenderer } from '../print/registry'
import { registerBuiltinPrintRenderers } from '../print/renderers'
import { DashboardPrintView } from './DashboardPrintView'
import { printableWidgets, type DashboardPrintState } from './printLayout'
import { registerDashboardRenderer } from './renderers'

const definition = (key: string, renderer_key: string, printable = true): WidgetDefinition => ({
  key, title: key, category: 'Test', renderer_key, source_key: key, supported_scopes: ['user'],
  default_size: [4, 3], min_size: [2, 2], max_size: [12, 8], allow_multiple: true,
  printable, icon: 'LayoutDashboard', config_fields: {},
})
const widget = (id: string, renderer_key: string, logical_order: number, data: unknown): DashboardWidget => ({
  id, definition_key: id, source_key: id, renderer_key, title: id, config: { limit: 5 },
  x: logical_order ? 0 : 8, y: 0, width: 4, height: 3, logical_order,
  available: true, data, error: false,
})

describe('Dashboard print', () => {
  it('registers the central A4 landscape renderer and prints logical order with core renderers', () => {
    registerBuiltinPrintRenderers()
    expect(getPrintRenderer('dashboard')?.defaultPage).toEqual({ size: 'A4', orientation: 'landscape' })
    const state: DashboardPrintState = {
      dashboard: { id: 1, name: 'Team summary', scope: 'user' },
      widgets: [
        { ...widget('progress', 'progress-list', 3, { items: [{ key: 'a', label: 'Fund', percent: 40 }] }), width: 8 },
        widget('alert', 'alert-list', 2, { items: [{ key: 'a', label: 'Deadline', severity: 'warning' }] }),
        widget('list', 'compact-list', 1, { items: [{ key: 'a', label: 'Project' }] }),
        { ...widget('kpi', 'kpi', 0, { value: 7, label: 'Projects' }), definition_key: 'core.projects-count', source_key: 'core.projects', config: { active_only: true } },
        widget('hidden', 'kpi', 4, { value: 99 }),
        { ...widget('missing', 'kpi', 5, null), available: false },
      ],
      definitions: [definition('progress', 'progress-list'), definition('alert', 'alert-list'), definition('list', 'compact-list'), { ...definition('core.projects-count', 'kpi'), source_key: 'core.projects' }, definition('hidden', 'kpi', false)],
    }
    expect(printableWidgets(state).map((item) => item.id)).toEqual(['kpi', 'list', 'alert', 'progress', 'missing'])
    const ready = vi.fn()
    render(<I18nProvider><DashboardPrintView state={state} onReady={ready} /></I18nProvider>)
    expect(ready).toHaveBeenCalledOnce()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('Project')).toBeInTheDocument()
    expect(screen.getByText('Deadline')).toBeInTheDocument()
    expect(screen.getByText('Fund')).toBeInTheDocument()
    expect(screen.queryByText('99')).not.toBeInTheDocument()
    expect(screen.getAllByRole('article').map((item) => item.getAttribute('aria-label'))).toEqual(['kpi', 'list', 'alert', 'progress', 'missing'])
    expect(document.querySelector('[data-renderer="progress-list"]')).toHaveAttribute('data-wide', 'true')
    expect(screen.getByText(/Widget unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Actions for/ })).not.toBeInTheDocument()
  })

  it('uses a plugin print component when provided and falls back to its normal renderer otherwise', () => {
    registerDashboardRenderer('test-custom-print', ({ widget }) => <span>Screen {widget.config.limit}</span>, ({ widget }) => <span>Paper {widget.config.limit}</span>)
    registerDashboardRenderer('test-print-fallback', ({ widget }) => <span>Fallback {widget.config.limit}</span>)
    const state: DashboardPrintState = { dashboard: { id: 2, name: 'Plugins', scope: 'user' }, widgets: [widget('custom', 'test-custom-print', 0, {}), widget('fallback', 'test-print-fallback', 1, {})], definitions: [definition('custom', 'test-custom-print'), definition('fallback', 'test-print-fallback')] }
    render(<I18nProvider><DashboardPrintView state={state} onReady={vi.fn()} /></I18nProvider>)
    expect(screen.getByText('Paper 5')).toBeInTheDocument()
    expect(screen.getByText('Fallback 5')).toBeInTheDocument()
    expect(screen.queryByText('Screen 5')).not.toBeInTheDocument()
  })
})
