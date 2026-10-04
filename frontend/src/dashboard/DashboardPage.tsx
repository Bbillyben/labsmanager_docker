import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowDown, ArrowUp, Copy, LayoutDashboard, Pencil, Plus, Presentation, Save, Star, Trash2 } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { listDashboards, getDashboard, getDashboardCatalog, getProjectDashboard, createDashboard, renameDashboard, deleteDashboard, duplicateDashboard, setDefaultDashboard, reorderDashboards, addDashboardWidget, updateDashboardWidget, deleteDashboardWidget, saveDashboardLayout, type DashboardSummary, type DashboardDetail, type DashboardCatalog, type DashboardWidget, type LayoutUpdate } from '../api/dashboards'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Input } from '../components/ui/input'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { Alert } from '../ui/Alert'
import { DashboardGrid } from './DashboardGrid'
import { DashboardWidgetEditor } from './DashboardWidgetEditor'
import { PrintButton } from '../print/PrintButton'
import type { DashboardPrintState } from './printLayout'
import { dashboardCategoryLabel, dashboardRendererLabel, dashboardSourceDescription, dashboardSourceLabel } from './labels'
import './DashboardPage.css'

const templateKeys = ['employee', 'leader', 'lab-manager', 'blank'] as const
type TemplateKey = typeof templateKeys[number]

function DashboardCreationForm({ onCreate, pending, error, onCancel, onboarding }: {
  onCreate: (name: string, template: TemplateKey) => void; pending: boolean; error: string | null
  onCancel?: () => void; onboarding: boolean
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [template, setTemplate] = useState<TemplateKey | null>(null)
  return <form className="dashboard-form" onSubmit={(event) => { event.preventDefault(); if (template) onCreate(name.trim(), template) }}>
    <label htmlFor="dashboard-name">{t('dashboard.name')}</label>
    <Input id="dashboard-name" value={name} maxLength={120} required onChange={(event) => setName(event.target.value)} />
    <fieldset><legend>{t('dashboard.chooseTemplate')}</legend><div className="dashboard-template-options">{templateKeys.map((key) => <label key={key} className={`dashboard-template ${template === key ? 'selected' : ''}`}><input type="radio" name="template" value={key} checked={template === key} onChange={() => setTemplate(key)} /><strong>{t(`dashboard.template.${key}`)}</strong><span>{t(`dashboard.templateDescription.${key}`)}</span></label>)}</div></fieldset>
    {error && <Alert tone="danger">{error}</Alert>}
    <div className="dashboard-form-actions">{!onboarding && onCancel && <Button variant="ghost" onClick={onCancel}>{t('common.cancel')}</Button>}<Button variant="default" type="submit" disabled={pending || !template || !name.trim()}><Plus aria-hidden="true" />{t('dashboard.create')}</Button></div>
  </form>
}

export function DashboardPage({ projectId }: { projectId?: string } = {}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [dashboards, setDashboards] = useState<DashboardSummary[] | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<DashboardDetail | null>(null)
  const [catalog, setCatalog] = useState<DashboardCatalog | null>(null)
  const [loadingError, setLoadingError] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [editing, setEditing] = useState(false)
  const [creating, setCreating] = useState(false)
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [configuring, setConfiguring] = useState<DashboardWidget | null>(null)
  const [addingSource, setAddingSource] = useState<string | null>(null)
  const [catalogSearch, setCatalogSearch] = useState('')
  const [removingWidget, setRemovingWidget] = useState<DashboardWidget | null>(null)
  const [removingDashboard, setRemovingDashboard] = useState(false)
  const [layoutDraft, setLayoutDraft] = useState<LayoutUpdate[] | null>(null)
  const returnFocus = useRef<HTMLElement | null>(null)

  async function loadAll(preferredId?: number | null) {
    if (projectId) {
      const [loaded, available] = await Promise.all([getProjectDashboard(projectId), getDashboardCatalog(projectId)])
      setDashboards([loaded]); setCatalog(available); setSelectedId(loaded.id); setDetail(loaded); setLayoutDraft(null)
      return
    }
    const [items, available] = await Promise.all([listDashboards(), getDashboardCatalog()])
    setDashboards(items)
    setCatalog(available)
    const id = preferredId && items.some((item) => item.id === preferredId) ? preferredId : items.find((item) => item.is_default)?.id ?? items[0]?.id ?? null
    setSelectedId(id)
    setDetail(id ? await getDashboard(id) : null)
    setLayoutDraft(null)
  }

  useEffect(() => { let active = true; if (projectId) {
    Promise.all([getProjectDashboard(projectId), getDashboardCatalog(projectId)]).then(([loaded, available]) => {
      if (active) { setDashboards([loaded]); setCatalog(available); setSelectedId(loaded.id); setDetail(loaded) }
    }).catch(() => { if (active) setLoadingError(true) })
    return () => { active = false }
  } Promise.all([listDashboards(), getDashboardCatalog()]).then(async ([items, available]) => {
    const requestedId = Number(new URLSearchParams(location.search).get('selected'))
    const id = items.find((item) => item.id === requestedId)?.id ?? items.find((item) => item.is_default)?.id ?? items[0]?.id ?? null
    const loaded = id ? await getDashboard(id) : null
    if (active) { setDashboards(items); setCatalog(available); setSelectedId(id); setDetail(loaded) }
  }).catch(() => { if (active) setLoadingError(true) }); return () => { active = false } }, [location.search, projectId])

  async function mutate(action: () => Promise<unknown>, preferredId: number | null = selectedId) {
    setPending(true); setError(null)
    try { await action(); await loadAll(preferredId); return true }
    catch { setError(t('dashboard.actionError')); return false }
    finally { setPending(false) }
  }

  async function selectDashboard(id: number) {
    setSelectedId(id); setDetail(null); setLayoutDraft(null); setEditing(false); setError(null)
    try { setDetail(await getDashboard(id)) } catch { setLoadingError(true) }
  }

  const definitions = useMemo(() => new Map((catalog?.definitions ?? []).map((item) => [item.key, item])), [catalog])
  const selected = dashboards?.find((item) => item.id === selectedId)
  const selectedIndex = dashboards?.findIndex((item) => item.id === selectedId) ?? -1
  const create = async (name: string, template: TemplateKey) => {
    setPending(true); setError(null)
    try {
      const item = await createDashboard(name, template)
      await loadAll(item.id)
      setCreating(false)
    } catch { setError(t('dashboard.actionError')) }
    finally { setPending(false) }
  }
  const swap = async (direction: -1 | 1) => {
    if (!dashboards || selectedIndex < 0 || selectedIndex + direction < 0 || selectedIndex + direction >= dashboards.length) return
    const ids = dashboards.map((item) => item.id)
    const next = selectedIndex + direction
    ;[ids[selectedIndex], ids[next]] = [ids[next], ids[selectedIndex]]
    await mutate(() => reorderDashboards(ids))
  }
  const openConfig = (widget: DashboardWidget) => setConfiguring(widget)
  const closeDialogs = () => { setCreating(false); setRenaming(false); setConfiguring(null); setAddingSource(null); setError(null) }
  const sourceLabel = (key: string, fallback: string) => dashboardSourceLabel(key, fallback, t)
  const sourceDescription = (key: string, fallback: string) => dashboardSourceDescription(key, fallback, t)
  const categoryLabel = (category: string) => dashboardCategoryLabel(category, t)
  const visibleSources = catalog?.sources.filter((source) => `${source.label} ${source.description} ${source.category} ${sourceLabel(source.key, source.label)} ${sourceDescription(source.key, source.description)} ${categoryLabel(source.category)}`.toLocaleLowerCase().includes(catalogSearch.toLocaleLowerCase())) ?? []
  const categories = [...new Set(visibleSources.map((source) => source.category))]

  if (loadingError) return <div className="dashboard-feedback"><Alert tone="danger">{t('dashboard.loadError')}</Alert><Button onClick={() => { setLoadingError(false); void loadAll().catch(() => setLoadingError(true)) }}>{t('common.retry')}</Button></div>
  if (dashboards === null || catalog === null) return <p className="muted-text" role="status" aria-busy="true">{t('common.loading')}</p>
  if (!dashboards.length && !projectId) return <div className="dashboard-page"><PageHeader title={t('dashboard.title')} description={t('dashboard.welcome')} /><section className="surface-section dashboard-onboarding"><h2>{t('dashboard.chooseStarting')}</h2><DashboardCreationForm onCreate={(name, template) => void create(name, template)} pending={pending} error={error} onboarding /></section></div>

  return <div className="dashboard-page">
    <PageHeader title={t(projectId ? 'dashboard.projectTitle' : 'dashboard.title')} description={t(projectId ? 'dashboard.projectDescription' : 'dashboard.description')} actions={<div className="dashboard-header-actions">{!projectId && <Button variant="secondary" onClick={() => setCreating(true)}><Plus aria-hidden="true" />{t('dashboard.new')}</Button>}<Button variant={editing ? 'default' : 'secondary'} onClick={() => { setEditing(!editing); setLayoutDraft(null) }}><Pencil aria-hidden="true" />{editing ? t('dashboard.finishEditing') : t('dashboard.customize')}</Button><Button variant="secondary" disabled={!detail || !selected} onClick={() => { if (selected) navigate(`/dashboard/${selected.id}/present`) }}><Presentation aria-hidden="true" />{t('dashboard.presentation')}</Button><PrintButton disabled={!detail || !selected} createRequest={() => ({ renderer: 'dashboard', title: selected?.name ?? t('dashboard.title'), state: { dashboard: { id: detail!.id, name: detail!.name, scope: detail!.scope }, widgets: detail!.widgets, definitions: catalog.definitions } satisfies DashboardPrintState })} /></div>} />
    {!projectId && <div className="dashboard-toolbar"><label htmlFor="dashboard-switcher">{t('dashboard.switcher')}</label><select id="dashboard-switcher" value={selectedId ?? ''} onChange={(event) => void selectDashboard(Number(event.target.value))}>{dashboards.map((item) => <option key={item.id} value={item.id}>{item.name}{item.is_default ? ` ★` : ''}</option>)}</select>{selected?.is_default && <span className="dashboard-default"><Star size={15} aria-hidden="true" />{t('dashboard.default')}</span>}</div>}
    {error && <Alert tone="danger">{error}</Alert>}
    {editing && selected && !projectId && <div className="dashboard-management">
      <Button variant="ghost" disabled={pending} onClick={() => { setRenameValue(selected.name); setRenaming(true) }}><Pencil aria-hidden="true" />{t('dashboard.rename')}</Button>
      <Button variant="ghost" disabled={pending || selected.is_default} onClick={() => void mutate(() => setDefaultDashboard(selected.id))}><Star aria-hidden="true" />{t('dashboard.makeDefault')}</Button>
      <Button variant="ghost" disabled={pending} onClick={async () => { setPending(true); setError(null); try { const copy = await duplicateDashboard(selected.id); await loadAll(copy.id) } catch { setError(t('dashboard.actionError')) } finally { setPending(false) } }}><Copy aria-hidden="true" />{t('dashboard.duplicate')}</Button>
      <Button variant="ghost" disabled={pending || selectedIndex <= 0} onClick={() => void swap(-1)}><ArrowUp aria-hidden="true" />{t('dashboard.moveUp')}</Button>
      <Button variant="ghost" disabled={pending || selectedIndex >= dashboards.length - 1} onClick={() => void swap(1)}><ArrowDown aria-hidden="true" />{t('dashboard.moveDown')}</Button>
      <Button variant="ghost" disabled={pending} onClick={() => { returnFocus.current = document.getElementById('dashboard-switcher'); setRemovingDashboard(true) }}><Trash2 aria-hidden="true" />{t('dashboard.delete')}</Button>
    </div>}
    {editing && selected && <div className="dashboard-edit-toolbar"><Button disabled={pending || !layoutDraft} onClick={() => void mutate(() => saveDashboardLayout(selected.id, layoutDraft ?? []))}><Save aria-hidden="true" />{t('dashboard.saveLayout')}</Button><span className="muted-text">{t('dashboard.dragHint')}</span></div>}
    {detail ? <>{editing && <section className="dashboard-catalog" aria-label={t('dashboard.catalog')}><h2>{t('dashboard.catalog')}</h2><label htmlFor="dashboard-catalog-search">{t('dashboard.searchSources')}</label><Input id="dashboard-catalog-search" value={catalogSearch} onChange={(event) => setCatalogSearch(event.target.value)} /><div className="dashboard-catalog-items">{categories.map((category) => <div key={category} className="dashboard-catalog-group"><h3>{categoryLabel(category)}</h3>{visibleSources.filter((source) => source.category === category).map((source) => {
      const disabled = !source.allow_multiple && detail.widgets.some((item) => (item.source_key || definitions.get(item.definition_key)?.source_key) === source.key)
      return <div className="dashboard-catalog-item" key={source.key}><Button variant="secondary" disabled={pending || disabled} onClick={() => setAddingSource(source.key)}><Plus aria-hidden="true" />{sourceLabel(source.key, source.label)}</Button><small>{sourceDescription(source.key, source.description)} · {source.compatible_renderers.map((key) => dashboardRendererLabel(key, catalog.renderers[key]?.label ?? key, t)).join(', ')}</small>{disabled && <small>{t('dashboard.alreadyAdded')}</small>}</div>
    })}</div>)}</div></section>}
      {detail.widgets.length ? <DashboardGrid key={detail.id} widgets={detail.widgets} definitions={definitions} mode={editing ? 'edit' : 'view'} layoutDraft={layoutDraft} onLayout={setLayoutDraft} onConfigure={openConfig} onRemove={(widget) => { returnFocus.current = document.getElementById('dashboard-switcher'); setRemovingWidget(widget) }} /> : <div className="dashboard-empty"><LayoutDashboard aria-hidden="true" /><p>{t('dashboard.noWidgets')}</p></div>}
    </> : <p className="muted-text" role="status" aria-busy="true">{t('common.loading')}</p>}
    <Sheet open={creating} onOpenChange={(open) => { if (!open && !pending) closeDialogs() }}><SheetContent><SheetHeader><SheetTitle>{t('dashboard.new')}</SheetTitle><SheetDescription>{t('dashboard.chooseStarting')}</SheetDescription></SheetHeader><DashboardCreationForm onCreate={(name, template) => void create(name, template)} pending={pending} error={error} onCancel={closeDialogs} onboarding={false} /></SheetContent></Sheet>
    <Sheet open={renaming} onOpenChange={(open) => { if (!open && !pending) closeDialogs() }}><SheetContent><SheetHeader><SheetTitle>{t('dashboard.rename')}</SheetTitle><SheetDescription>{t('dashboard.name')}</SheetDescription></SheetHeader><form className="dashboard-form" onSubmit={async (event) => { event.preventDefault(); if (selected && await mutate(() => renameDashboard(selected.id, renameValue))) closeDialogs() }}><label htmlFor="dashboard-rename">{t('dashboard.name')}</label><Input id="dashboard-rename" value={renameValue} onChange={(event) => setRenameValue(event.target.value)} required maxLength={120} /><Button type="submit" disabled={pending || !renameValue.trim()}>{t('common.save')}</Button></form></SheetContent></Sheet>
    <Sheet open={Boolean(addingSource || configuring)} onOpenChange={(open) => { if (!open && !pending) closeDialogs() }}><SheetContent><SheetHeader><SheetTitle>{configuring ? t('dashboard.configure') : t('dashboard.catalog')}</SheetTitle><SheetDescription>{sourceLabel(addingSource || configuring?.source_key || '', catalog.sources.find((item) => item.key === (addingSource || configuring?.source_key))?.label ?? '')}</SheetDescription></SheetHeader>{(() => {
      const source = catalog.sources.find((item) => item.key === (addingSource || configuring?.source_key || definitions.get(configuring?.definition_key ?? '')?.source_key))
      if (!source || !detail) return null
      return <DashboardWidgetEditor key={configuring?.id ?? source.key} source={source} catalog={catalog} widget={configuring ?? undefined} pending={pending} onCancel={closeDialogs} onSave={async (renderer, title, config) => {
        const ok = configuring ? await mutate(() => updateDashboardWidget(detail.id, configuring.id, title, config, renderer)) : await mutate(() => addDashboardWidget(detail.id, source.key, renderer, title, config))
        if (ok) closeDialogs()
      }} />
    })()}</SheetContent></Sheet>
    {removingWidget && detail && <ConfirmDialog title={t('dashboard.removeWidget', { name: removingWidget.title || removingWidget.definition_key })} description={t('dashboard.removeWidgetConfirm')} pending={pending} error={error && <Alert tone="danger">{error}</Alert>} returnFocus={returnFocus} onCancel={() => { setRemovingWidget(null); setError(null) }} onConfirm={async () => { if (await mutate(() => deleteDashboardWidget(detail.id, removingWidget.id))) setRemovingWidget(null) }} />}
    {removingDashboard && selected && <ConfirmDialog title={t('dashboard.delete')} description={t('dashboard.deleteConfirm', { name: selected.name })} pending={pending} error={error && <Alert tone="danger">{error}</Alert>} returnFocus={returnFocus} onCancel={() => { setRemovingDashboard(false); setError(null) }} onConfirm={async () => { if (await mutate(() => deleteDashboard(selected.id), null)) { setRemovingDashboard(false); setEditing(false) } }} />}
  </div>
}
