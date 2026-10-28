import { Component as ReactComponent, useEffect, useState, type ReactNode } from 'react'
import type { UIModuleDescriptor } from '../api/uiContributions'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { loadPluginComponent, type PluginComponent } from './pluginModuleLoader'

function logPluginError(descriptor: UIModuleDescriptor, error: unknown) {
  console.error('Plugin React module failed', {
    plugin: descriptor.plugin_slug,
    contribution: descriptor.id,
    moduleUrl: descriptor.module_url,
    error,
  })
}

class PluginRenderBoundary extends ReactComponent<{ children: ReactNode; fallback: ReactNode; descriptor: UIModuleDescriptor }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() { return { failed: true } }

  componentDidCatch(error: Error) { logPluginError(this.props.descriptor, error) }

  render() { return this.state.failed ? this.props.fallback : this.props.children }
}

export function PluginModule({ descriptor, onClose }: { descriptor: UIModuleDescriptor; onClose?: () => void }) {
  return <PluginModuleContent key={`${descriptor.module_url}:${descriptor.component}:${descriptor.asset_version}`} descriptor={descriptor} onClose={onClose} />
}

function PluginModuleContent({ descriptor, onClose }: { descriptor: UIModuleDescriptor; onClose?: () => void }) {
  const { t } = useTranslation()
  const [component, setComponent] = useState<PluginComponent | null>(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)

  const retry = () => { setComponent(null); setError(false); setAttempt((value) => value + 1) }

  useEffect(() => {
    let live = true
    loadPluginComponent(descriptor).then((loaded) => { if (live) setComponent(() => loaded) }, (reason: unknown) => {
      logPluginError(descriptor, reason)
      if (live) setError(true)
    })
    return () => { live = false }
  }, [descriptor, attempt])

  if (error) return <Alert tone="danger">{t('pluginUI.moduleError')} <Button onClick={retry}>{t('common.retry')}</Button>{onClose && <Button onClick={onClose}>{t('common.close')}</Button>}</Alert>
  if (!component) return <p role="status">{t('common.loading')}</p>
  const Component = component
  return <PluginRenderBoundary key={`${descriptor.module_url}:${attempt}`} descriptor={descriptor} fallback={<Alert tone="danger">{t('pluginUI.moduleError')} <Button onClick={retry}>{t('common.retry')}</Button>{onClose && <Button onClick={onClose}>{t('common.close')}</Button>}</Alert>}>
    <Component context={descriptor.context} onClose={onClose} />
  </PluginRenderBoundary>
}
