import { CalendarDays, Copy, ExternalLink, Info, Link as LinkIcon, Play } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ComponentProps, type ReactNode } from 'react'
import { getUIActionModule, getUIContributions, getUISection, runUIAction, type UIContribution, type UIContributionScope, type UICalendarType, type UIModuleDescriptor, type UISection } from '../api/uiContributions'
import { useTranslation } from '../i18n/i18n'
import { useEmployeeResource } from '../pages/useEmployeeResource'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { ConfirmDialog } from './common/ConfirmDialog'
import { EntityActionMenu, type EntityActionGroup } from './EntityActionMenu'
import { copyPluginToken } from './copyPluginToken'
import { PluginModule } from './PluginModule'

type ContributionContext = { scope: UIContributionScope; actionSlot: string; sectionSlot: string | null; items: UIContribution[]; error: unknown; retry: () => void }
const Context = createContext<ContributionContext | null>(null)

function useContributions() {
  const context = useContext(Context)
  if (!context) throw new Error('PluginContributionsProvider is required')
  return context
}

export function PluginEntityTabs({ base, linkClassName, activeClassName, state }: { base: string; linkClassName: string; activeClassName: string; state?: unknown }) {
  const { items, scope } = useContributions()
  const slot = 'entity' in scope ? `${scope.entity}.detail.tabs` : null
  return <>{items.filter((item) => item.type === 'tab' && item.slot === slot && item.local_id).map((item) => <NavLink
    className={({ isActive }) => `${linkClassName} ${isActive ? activeClassName : ''}`}
    key={item.id}
    to={`${base}/plugins/${encodeURIComponent(item.plugin_slug)}/${encodeURIComponent(item.local_id!)}`}
    state={state}
  >{item.label}</NavLink>)}</>
}

export function PluginContributionsProvider({ scope, children }: { scope: UIContributionScope; children: ReactNode }) {
  const entity = 'entity' in scope ? scope.entity : null
  const calendarType = 'calendarType' in scope ? scope.calendarType : null
  const pluginKey = 'pluginKey' in scope ? scope.pluginKey : null
  const providerSlug = 'providerSlug' in scope ? scope.providerSlug : null
  const calendarId = 'calendarId' in scope ? scope.calendarId : null
  const objectId = 'objectId' in scope ? scope.objectId : null
  const stableScope = useMemo((): UIContributionScope => entity !== null
    ? { entity, objectId: objectId! }
    : calendarType !== null ? { calendarType, objectId: objectId! }
      : providerSlug !== null ? { providerSlug, calendarId: calendarId! }
        : { pluginKey: pluginKey! }, [entity, calendarType, pluginKey, providerSlug, calendarId, objectId])
  const key = entity !== null ? `${entity}:${objectId}` : calendarType !== null ? `calendar:${calendarType}:${objectId}`
    : providerSlug !== null ? `published:${providerSlug}:${calendarId}` : `plugin:${pluginKey}`
  const loader = useCallback((_key: string, signal: AbortSignal) => getUIContributions(stableScope, signal), [stableScope])
  const resource = useEmployeeResource(key, loader)
  const actionSlot = entity !== null ? `${entity}.detail.actions` : calendarType !== null ? 'calendar.toolbar.actions'
    : providerSlug !== null ? 'published-calendar.actions' : 'user.plugin.settings.actions'
  const sectionSlot = entity !== null ? `${entity}.detail.sections` : null
  return <Context.Provider value={{ scope: stableScope, actionSlot, sectionSlot, items: resource.data?.contributions ?? [], error: resource.error, retry: resource.retry }}>{children}</Context.Provider>
}

const icons: Record<string, ReactNode> = {
  calendar: <CalendarDays aria-hidden="true" />, copy: <Copy aria-hidden="true" />,
  'external-link': <ExternalLink aria-hidden="true" />, link: <LinkIcon aria-hidden="true" />,
  info: <Info aria-hidden="true" />, play: <Play aria-hidden="true" />,
}

export function PluginEntityActions({ groups, presentation = 'menu', ...props }: ComponentProps<typeof EntityActionMenu> & { groups: EntityActionGroup[]; presentation?: 'menu' | 'buttons' }) {
  const { scope, actionSlot, items } = useContributions()
  const { t } = useTranslation()
  const [confirming, setConfirming] = useState<UIContribution | null>(null)
  const [pending, setPending] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [error, setError] = useState('')
  const [manualUrl, setManualUrl] = useState('')
  const [openUrl, setOpenUrl] = useState('')
  const [actionModule, setActionModule] = useState<UIModuleDescriptor | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const actions = items.filter((item) => item.slot === actionSlot && item.type === 'action')

  async function execute(item: UIContribution) {
    setConfirming(null)
    setPending(true); setError(''); setFeedback(''); setManualUrl(''); setOpenUrl('')
    let windowForUrl: Window | null = null
    try {
      if (item.behavior === 'module') {
        setActionModule(await getUIActionModule(scope, item.id))
        return
      }
      if (item.behavior === 'open_url') {
        windowForUrl = window.open('about:blank', '_blank')
        if (windowForUrl) windowForUrl.opener = null
      }
      const result = await runUIAction(scope, item.id)
      if (item.behavior === 'copy_url' && result.url) {
        const input = document.createElement('input')
        input.value = result.url
        document.body.appendChild(input)
        const copied = await copyPluginToken(input)
        input.remove()
        // The response reveals a newly created subscription URL only here.
        setManualUrl(result.url)
        if (copied) setFeedback(t('pluginUI.copied'))
      } else if (item.behavior === 'open_url' && result.url) {
        if (windowForUrl) windowForUrl.location.href = result.url
        else setOpenUrl(result.url)
      } else setFeedback(result.message || t('pluginUI.done'))
    } catch {
      windowForUrl?.close()
      setError(t('pluginUI.actionError'))
    } finally { setPending(false) }
  }

  const pluginGroup: EntityActionGroup = actions.map((item) => ({
    id: item.id, label: item.label, icon: item.icon ? icons[item.icon] : undefined, disabled: pending,
    onSelect: () => { if (item.confirm) setConfirming(item); else void execute(item) },
  }))
  return <>
    {presentation === 'buttons' ? actions.map((item) => <Button key={item.id} disabled={pending}
      onClick={() => void execute(item)}>{item.label}</Button>)
      : <EntityActionMenu {...props} groups={[...groups, pluginGroup]} onTrigger={(trigger) => { focus.current = trigger; props.onTrigger?.(trigger) }} />}
    {feedback && <span role="status" className="max-w-64 break-words text-sm text-muted-foreground">{feedback}</span>}
    {error && <span role="alert" className="max-w-64 break-words text-sm text-destructive">{error}</span>}
    {manualUrl && <label className="text-sm">{t('pluginUI.manualCopy')}<input className="ml-2 max-w-48 rounded border bg-background p-1" readOnly value={manualUrl} onFocus={(event) => event.currentTarget.select()} /></label>}
    {openUrl && <a href={openUrl} target="_blank" rel="noopener noreferrer">{t('pluginUI.openLink')}</a>}
    {confirming && <ConfirmDialog title={confirming.label} description={t('pluginUI.confirm', { name: confirming.label })} pending={pending} onCancel={() => setConfirming(null)} onConfirm={() => void execute(confirming)} returnFocus={focus} confirmLabel={t('pluginUI.run')} />}
    {actionModule && <PluginModule descriptor={actionModule} onClose={() => setActionModule(null)} />}
  </>
}

function PluginSection({ item, scope }: { item: UIContribution; scope: UIContributionScope }) {
  const { t } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getUISection(scope, item.id, signal), [scope, item.id])
  const resource = useEmployeeResource(item.id, loader)
  const content = resource.data
  return <section className="rounded-lg border border-border bg-card p-4" aria-label={item.label}>
    <h2 className="mb-3 text-lg font-semibold">{item.label}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('pluginUI.sectionError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {content && <SectionContent content={content} />}
  </section>
}

function SectionContent({ content }: { content: UISection }) {
  const { t } = useTranslation()
  if (content.format === 'text') return content.text ? <p className="whitespace-pre-wrap">{content.text}</p> : <p>{t('pluginUI.empty')}</p>
  if (!content.items.length) return <p>{t('pluginUI.empty')}</p>
  if (content.format === 'properties') return <dl className="grid gap-2">{content.items.map((item, index) => <div key={index} className="grid gap-1 sm:grid-cols-[minmax(8rem,12rem)_minmax(0,1fr)]"><dt className="text-muted-foreground">{item.label}</dt><dd className="break-words">{item.value}</dd></div>)}</dl>
  if (content.format === 'links') return <ul className="list-inside list-disc space-y-1">{content.items.map((item, index) => <li key={index}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.label}</a></li>)}</ul>
  return <ul className="space-y-2">{content.items.map((item, index) => <li key={index}>{item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.label}</a> : <strong>{item.label}</strong>}{item.description && <p className="text-sm text-muted-foreground">{item.description}</p>}</li>)}</ul>
}

export function PluginContributionSections() {
  const { scope, sectionSlot, items, error, retry } = useContributions()
  const { t } = useTranslation()
  const sections = items.filter((item) => item.slot === sectionSlot && item.type === 'section')
  if (!error && !sections.length) return null
  return <div className="mt-5 grid gap-4">
    {!!error && <Alert tone="danger">{t('pluginUI.loadError')} <Button variant="ghost" onClick={retry}>{t('common.retry')}</Button></Alert>}
    {sections.map((item) => <PluginSection key={item.id} item={item} scope={scope} />)}
  </div>
}

export function CalendarPluginActions({ calendarType, objectId }: { calendarType: UICalendarType; objectId: number }) {
  const { t } = useTranslation()
  return <PluginContributionsProvider key={`${calendarType}:${objectId}`} scope={{ calendarType, objectId }}>
    <PluginEntityActions groups={[]} label={t('pluginUI.actions')} />
  </PluginContributionsProvider>
}

export function PluginPublishedCalendarActions({ providerSlug, calendarId }: { providerSlug: string; calendarId: string }) {
  return <PluginContributionsProvider key={`${providerSlug}:${calendarId}`} scope={{ providerSlug, calendarId }}>
    <PublishedCalendarActionButtons />
  </PluginContributionsProvider>
}

function PublishedCalendarActionButtons() {
  const { error, retry } = useContributions()
  const { t } = useTranslation()
  return <>
    {!!error && <Alert tone="danger">{t('pluginUI.loadError')} <Button variant="ghost" onClick={retry}>{t('common.retry')}</Button></Alert>}
    <PluginEntityActions groups={[]} presentation="buttons" label={t('pluginUI.actions')} />
  </>
}

export function UserPluginActions({ pluginKey, className }: { pluginKey: string; className?: string }) {
  return <PluginContributionsProvider key={pluginKey} scope={{ pluginKey }}><UserPluginActionSection className={className} /></PluginContributionsProvider>
}

function UserPluginActionSection({ className }: { className?: string }) {
  const { actionSlot, items, error, retry } = useContributions()
  const { t } = useTranslation()
  const actions = items.filter((item) => item.slot === actionSlot && item.type === 'action')
  if (!actions.length && !error) return null
  return <section className={className}>
    <h2>{t('pluginUI.actions')}</h2>
    {!!error && <Alert tone="danger">{t('pluginUI.loadError')} <Button variant="ghost" onClick={retry}>{t('common.retry')}</Button></Alert>}
    {actions.length > 0 && <PluginEntityActions groups={[]} label={t('pluginUI.actions')} />}
  </section>
}
