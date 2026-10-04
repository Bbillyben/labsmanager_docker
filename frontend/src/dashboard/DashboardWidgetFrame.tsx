import { Component, createElement, type ReactNode } from 'react'
import { Ellipsis, Grip, Pencil, Trash2 } from 'lucide-react'
import type { DashboardWidget, WidgetDefinition } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu'
import { getDashboardRenderer } from './renderers'
import { dashboardSize } from './size'
import { dashboardSourceLabel } from './labels'
import type { DashboardMode } from './mode'

class WidgetErrorBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? this.props.fallback : this.props.children }
}

export function DashboardWidgetFrame({ widget, definition, mode, onConfigure, onRemove, width, height }: {
  widget: DashboardWidget; definition?: WidgetDefinition; mode: DashboardMode
  onConfigure?: () => void; onRemove?: () => void; width?: number; height?: number
}) {
  const { t } = useTranslation()
  const Renderer = getDashboardRenderer(widget.renderer_key, mode)
  const unavailable = !widget.available || !definition || !Renderer
  const title = widget.title || (definition ? dashboardSourceLabel(widget.source_key || definition.source_key, definition.title, t) : widget.definition_key)
  const fallback = <p role="alert" className="muted-text">{t('dashboard.widgetError')}</p>
  const sourceError = <p role="alert" className="muted-text">{t('dashboard.sourceError')}</p>
  return <article className="dashboard-widget-frame" aria-label={title}>
    <header className="dashboard-widget-header"><h2>{title}</h2>{(mode === 'view' || mode === 'edit') && <div className="dashboard-widget-actions">{mode === 'edit' && <span className="dashboard-drag-handle" aria-label={t('dashboard.dragHandle')}><Grip aria-hidden="true" /></span>}<DropdownMenu><DropdownMenuTrigger render={<Button size="icon-sm" variant="ghost" />} aria-label={t('dashboard.widgetActions', { name: title })}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger><DropdownMenuContent align="end">{!unavailable && <DropdownMenuItem onClick={onConfigure}><Pencil aria-hidden="true" />{t('dashboard.configure')}</DropdownMenuItem>}<DropdownMenuItem onClick={onRemove}><Trash2 aria-hidden="true" />{t('common.delete')}</DropdownMenuItem></DropdownMenuContent></DropdownMenu></div>}</header>
    <div className="dashboard-widget-body">{unavailable ? <p className="muted-text">{t('dashboard.unavailable')} · <code>{widget.definition_key}</code></p> : widget.error ? sourceError : widget.data === null ? <p className="muted-text">{t('dashboard.emptyWidget')}</p> : <WidgetErrorBoundary key={`${widget.id}-${widget.renderer_key}`} fallback={fallback}>{createElement(Renderer, { widget, size: mode === 'print' ? 'expanded' : dashboardSize(width ?? widget.width, height ?? widget.height), mode })}</WidgetErrorBoundary>}</div>
  </article>
}
