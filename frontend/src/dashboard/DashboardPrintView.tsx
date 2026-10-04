import { useEffect, useMemo } from 'react'
import { useTranslation } from '../i18n/i18n'
import type { PrintRendererProps } from '../print/registry'
import { DashboardWidgetFrame } from './DashboardWidgetFrame'
import { printableWidgets, type DashboardPrintState } from './printLayout'
import './DashboardPage.css'
import './DashboardPrint.css'

export function DashboardPrintView({ state, onReady }: PrintRendererProps<DashboardPrintState>) {
  const { t } = useTranslation()
  const definitions = useMemo(() => new Map(state.definitions.map((item) => [item.key, item])), [state.definitions])
  const widgets = useMemo(() => printableWidgets(state), [state])
  useEffect(() => { onReady() }, [onReady])
  return <section className="dashboard-print" data-testid="dashboard-print" aria-label={state.dashboard.name}>
    {widgets.length ? <div className="dashboard-print-grid">{widgets.map((widget) => <div className="dashboard-print-item" data-wide={widget.width > 6} data-renderer={widget.renderer_key} key={widget.id}>
      <DashboardWidgetFrame widget={widget} definition={definitions.get(widget.definition_key)} mode="print" />
    </div>)}</div> : <p className="muted-text">{t('dashboard.printEmpty')}</p>}
  </section>
}
