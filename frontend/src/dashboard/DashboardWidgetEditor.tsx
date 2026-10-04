import { useState } from 'react'
import type { ConfigField, DashboardCatalog, DashboardSource, DashboardWidget } from '../api/dashboards'
import { Input } from '../components/ui/input'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { dashboardChoiceLabel, dashboardFieldLabel, dashboardRendererLabel } from './labels'

function fieldSpec(value: ConfigField | string): ConfigField {
  return typeof value === 'string' ? { type: 'string' } : value
}

export function DashboardWidgetEditor({ source, catalog, widget, pending, onCancel, onSave }: {
  source: DashboardSource; catalog: DashboardCatalog; widget?: DashboardWidget; pending: boolean
  onCancel: () => void; onSave: (renderer: string, title: string, config: DashboardWidget['config']) => void
}) {
  const { t } = useTranslation()
  const [renderer, setRenderer] = useState(widget?.renderer_key ?? source.default_renderer)
  const [title, setTitle] = useState(widget?.title ?? '')
  const [config, setConfig] = useState<DashboardWidget['config']>(widget?.config ?? {})
  const definition = catalog.definitions.find((item) => item.source_key === source.key)
  const fields = { ...source.config_fields, ...definition?.config_fields, ...catalog.renderers[renderer]?.config_fields }
  const setField = (key: string, value: string | number | boolean) => setConfig((current) => {
    const next = { ...current, [key]: value }
    if (key === 'project_scope' && value !== 'specific_project') delete next.project_id
    return next
  })
  const projectScope = String(config.project_scope ?? (catalog.scope === 'project' ? 'context' : 'all_visible'))
  return <form className="dashboard-form" onSubmit={(event) => { event.preventDefault(); onSave(renderer, title, 'project_scope' in fields ? { ...config, project_scope: projectScope } : config) }}>
    <p><i>{source.description}</i></p>
    <label htmlFor="dashboard-renderer">{t('dashboard.rendererLabel')}</label>
    <select id="dashboard-renderer" value={renderer} onChange={(event) => setRenderer(event.target.value)}>
      {source.compatible_renderers.map((key) => <option key={key} value={key}>{dashboardRendererLabel(key, catalog.renderers[key]?.label ?? key, t)}</option>)}
    </select>
    <label htmlFor="dashboard-widget-title">{t('dashboard.customTitle')}</label>
    <Input id="dashboard-widget-title" value={title} maxLength={160} onChange={(event) => setTitle(event.target.value)} />
    {Object.entries(fields).map(([key, raw]) => {
      const field = fieldSpec(raw)
      const label = dashboardFieldLabel(key, field.label ?? key, t, source.key)
      if (key === 'project_id' && projectScope !== 'specific_project') return null
      const value = key === 'project_scope' ? projectScope : config[key] ?? field.default ?? (field.type === 'boolean' ? false : '')
      if (field.type === 'project') return <label key={key} htmlFor={`dashboard-field-${key}`}>{label}<select id={`dashboard-field-${key}`} value={String(value)} required onChange={(event) => setField(key, Number(event.target.value))}><option value="">—</option>{(catalog.project_options ?? []).map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
      if (field.type === 'boolean') return <label key={key} className="dashboard-checkbox"><input type="checkbox" checked={value === true} onChange={(event) => setField(key, event.target.checked)} />{label}</label>
      if (field.type === 'choice') return <label key={key} htmlFor={`dashboard-field-${key}`}>{label}<select id={`dashboard-field-${key}`} value={String(value)} onChange={(event) => setField(key, event.target.value)}>{field.choices?.filter((option) => !(key === 'project_scope' && catalog.scope !== 'project' && option === 'context')).map((option) => <option key={option} value={option}>{dashboardChoiceLabel(String(option), t)}</option>)}</select></label>
      return <label key={key} htmlFor={`dashboard-field-${key}`}>{label}<Input id={`dashboard-field-${key}`} type={field.type === 'integer' ? 'number' : 'text'} value={String(value)} required={field.required} min={field.min} max={field.max} maxLength={field.max_length} onChange={(event) => setField(key, field.type === 'integer' ? Number(event.target.value) : event.target.value)} /></label>
    })}
    <div className="dashboard-form-actions"><Button type="button" variant="ghost" onClick={onCancel}>{t('common.cancel')}</Button><Button type="submit" disabled={pending}>{t('common.save')}</Button></div>
  </form>
}
