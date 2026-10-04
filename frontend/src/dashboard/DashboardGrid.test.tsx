import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import type { DashboardWidget, WidgetDefinition } from '../api/dashboards'
import { DashboardGrid } from './DashboardGrid'
import { DashboardWidgetFrame } from './DashboardWidgetFrame'
import { registerDashboardRenderer } from './renderers'

const grid = vi.hoisted(() => ({ props: vi.fn() }))
vi.mock('react-grid-layout', () => ({
  useContainerWidth: () => ({ width: 1200, containerRef: { current: null }, mounted: true }),
  Responsive: (props: { children: React.ReactNode; layouts: { lg: { i: string; minW: number; maxW: number }[] }; dragConfig: { enabled: boolean }; resizeConfig: { enabled: boolean }; onDragStop: (layout: { i: string; x: number; y: number; w: number; h: number }[]) => void }) => {
    grid.props(props)
    return <div data-testid="responsive-grid">{props.children}<button onClick={() => props.onDragStop([{ i: 'widget-1', x: 2, y: 1, w: 5, h: 3 }])}>Simulate drag</button></div>
  },
}))

const widget: DashboardWidget = { id: 'widget-1', definition_key: 'core.note', source_key: 'core.note', renderer_key: 'empty', title: '', config: {}, x: 0, y: 0, width: 4, height: 3, logical_order: 0, available: true, data: { message: 'A real note' }, error: false }
const definition: WidgetDefinition = { key: 'core.note', title: 'Note', category: 'General', renderer_key: 'empty', source_key: 'core.note', supported_scopes: ['user'], default_size: [4, 3], min_size: [2, 2], max_size: [8, 6], allow_multiple: true, printable: true, icon: 'LayoutDashboard', config_fields: { message: 'string' } }

describe('Dashboard grid and renderer registry', () => {
  it('applies size constraints, edits only in edit mode and emits one layout batch', async () => {
    const onLayout = vi.fn()
    const user = userEvent.setup()
    const view = render(<I18nProvider><DashboardGrid widgets={[widget]} definitions={new Map([['core.note', definition]])} mode="view" layoutDraft={null} onLayout={onLayout} onConfigure={vi.fn()} onRemove={vi.fn()} /></I18nProvider>)
    expect(screen.getByText('A real note')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Actions for Note|Actions pour Note/ })).toBeInTheDocument()
    expect(grid.props.mock.lastCall?.[0].dragConfig.enabled).toBe(false)
    expect(grid.props.mock.lastCall?.[0].resizeConfig.enabled).toBe(false)
    expect(grid.props.mock.lastCall?.[0].layouts.lg[0]).toMatchObject({ minW: 2, maxW: 8 })
    view.rerender(<I18nProvider><DashboardGrid widgets={[widget]} definitions={new Map([['core.note', definition]])} mode="edit" layoutDraft={null} onLayout={onLayout} onConfigure={vi.fn()} onRemove={vi.fn()} /></I18nProvider>)
    expect(grid.props.mock.lastCall?.[0].dragConfig.enabled).toBe(true)
    expect(screen.getByLabelText(/Move widget|Déplacer le widget/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Simulate drag' }))
    expect(onLayout).toHaveBeenCalledWith([{ id: 'widget-1', x: 2, y: 1, width: 5, height: 3, logical_order: 0 }])
  })

  it('shows a missing-definition placeholder and isolates renderer failure', () => {
    const missing = { ...widget, definition_key: 'missing.plugin.widget', available: false }
    const onRemove = vi.fn()
    const view = render(<I18nProvider><DashboardWidgetFrame widget={missing} mode="edit" onConfigure={vi.fn()} onRemove={onRemove} /></I18nProvider>)
    expect(screen.getAllByText('missing.plugin.widget')).toHaveLength(2)
    expect(screen.getByText(/Widget unavailable/)).toBeInTheDocument()
    registerDashboardRenderer('test-failing-renderer', () => { throw new Error('Broken widget') })
    view.rerender(<I18nProvider><DashboardWidgetFrame widget={{ ...widget, renderer_key: 'test-failing-renderer' }} definition={definition} mode="view" onConfigure={vi.fn()} onRemove={onRemove} /></I18nProvider>)
    expect(screen.getByRole('alert')).toHaveTextContent('This widget encountered an error.')
  })

  it('shows the instance title without changing the definition title', () => {
    render(<I18nProvider><DashboardWidgetFrame widget={{ ...widget, title: 'Private title' }} definition={definition} mode="view" onConfigure={vi.fn()} onRemove={vi.fn()} /></I18nProvider>)
    expect(screen.getByRole('heading', { name: 'Private title' })).toBeInTheDocument()
    expect(definition.title).toBe('Note')
  })

  it('separates source failure from renderer failure', () => {
    render(<I18nProvider><DashboardWidgetFrame widget={{ ...widget, error: true }} definition={definition} mode="view" onConfigure={vi.fn()} onRemove={vi.fn()} /></I18nProvider>)
    expect(screen.getByRole('alert')).toHaveTextContent('Could not load this widget’s data.')
  })

  it('keeps the same widget data and layout in presentation without edit controls', () => {
    render(<I18nProvider><DashboardGrid widgets={[widget]} definitions={new Map([['core.note', definition]])} mode="presentation" /></I18nProvider>)
    expect(screen.getByText('A real note')).toBeInTheDocument()
    expect(grid.props.mock.lastCall?.[0].layouts.lg[0]).toMatchObject({ i: widget.id, x: widget.x, y: widget.y, w: widget.width, h: widget.height })
    expect(grid.props.mock.lastCall?.[0].dragConfig.enabled).toBe(false)
    expect(grid.props.mock.lastCall?.[0].resizeConfig.enabled).toBe(false)
    expect(screen.queryByRole('button', { name: /Actions for/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Move widget')).not.toBeInTheDocument()
  })

  it('keeps business links active in presentation', () => {
    const project = { ...widget, renderer_key: 'compact-list', data: { items: [{ key: 'project-3', label: 'Research project', href: '/app/projects/3' }] } }
    render(<I18nProvider><DashboardWidgetFrame widget={project} definition={definition} mode="presentation" /></I18nProvider>)
    expect(screen.getByRole('link', { name: 'Research project' })).toHaveAttribute('href', '/app/projects/3')
    expect(screen.queryByRole('button', { name: /Actions for|Actions pour/ })).not.toBeInTheDocument()
  })
})
