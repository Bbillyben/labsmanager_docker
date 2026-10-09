import { useMemo, useState } from 'react'
import { Responsive, useContainerWidth, type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import type { DashboardWidget, LayoutUpdate, WidgetDefinition } from '../api/dashboards'
import { DashboardWidgetFrame } from './DashboardWidgetFrame'
import type { DashboardMode } from './mode'

const breakpoints = { lg: 900, sm: 0 }
const cols = { lg: 12, sm: 1 }

export function DashboardGrid({ widgets, definitions, mode, layoutDraft, onLayout, onConfigure, onRemove }: {
  widgets: DashboardWidget[]; definitions: Map<string, WidgetDefinition>; mode: DashboardMode
  layoutDraft?: LayoutUpdate[] | null; onLayout?: (layout: LayoutUpdate[]) => void; onConfigure?: (widget: DashboardWidget) => void; onRemove?: (widget: DashboardWidget) => void
}) {
  const editing = mode === 'edit'
  const { width, containerRef, mounted } = useContainerWidth()
  const [breakpoint, setBreakpoint] = useState('lg')
  const desktopLayout = useMemo<Layout>(() => widgets.map((widget) => {
    const definition = definitions.get(widget.definition_key)
    const draft = layoutDraft?.find((item) => item.id === widget.id)
    return {
      i: widget.id, x: draft?.x ?? widget.x, y: draft?.y ?? widget.y,
      w: draft?.width ?? widget.width, h: draft?.height ?? widget.height,
      minW: definition?.min_size[0] ?? 1, minH: definition?.min_size[1] ?? 1,
      maxW: definition?.max_size[0] ?? 24, maxH: definition?.max_size[1] ?? 24
    }
  }), [widgets, definitions, layoutDraft])
  const mobileLayout = useMemo<Layout>(() => [...widgets].sort((a, b) => a.logical_order - b.logical_order).map((widget, index) => ({ i: widget.id, x: 0, y: index * Math.max(2, widget.height), w: 1, h: Math.max(2, widget.height), minW: 1, maxW: 1 })), [widgets])
  const update = (layout: Layout) => {
    if (breakpoint !== 'lg') return
    onLayout?.(layout.map((item, index) => ({ id: item.i, x: item.x, y: item.y, width: item.w, height: item.h, logical_order: widgets.find((widget) => widget.id === item.i)?.logical_order ?? index })))
  }
  return <div ref={containerRef} className="dashboard-grid-container">{mounted && <Responsive
    width={width} breakpoints={breakpoints} cols={cols} layouts={{ lg: desktopLayout, sm: mobileLayout }}
    rowHeight={56} margin={[12, 12]} onBreakpointChange={setBreakpoint}
    dragConfig={{ enabled: editing && breakpoint === 'lg', handle: '.dashboard-drag-handle', cancel: 'button' }}
    resizeConfig={{ enabled: editing && breakpoint === 'lg', handles: ['se'] }}
    onDragStop={update} onResizeStop={update}
  >{widgets.map((widget) => { const layout = desktopLayout.find((item) => item.i === widget.id); return <div key={widget.id}><DashboardWidgetFrame widget={widget} definition={definitions.get(widget.definition_key)} mode={mode} width={breakpoint === 'lg' ? layout?.w : 1} height={breakpoint === 'lg' ? layout?.h : widget.height} onConfigure={() => onConfigure?.(widget)} onRemove={() => onRemove?.(widget)} /></div> })}</Responsive>}</div>
}
