import { useCallback } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { getUIPage, getUITab } from '../api/uiContributions'
import { PluginModule } from '../components/PluginModule'
import { CalendarPageNavigation } from '../components/CalendarPageNavigation'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { useEmployeeResource } from './useEmployeeResource'

export function PluginPage() {
  const { pluginSlug = '', pageId = '' } = useParams()
  const location = useLocation()
  const { t } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getUIPage(pluginSlug, pageId, signal), [pluginSlug, pageId])
  const resource = useEmployeeResource(`${pluginSlug}:${pageId}`, loader)
  const content = resource.loading ? <p role="status">{t('common.loading')}</p>
    : resource.error ? <Alert tone="danger">{t('pluginUI.pageError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>
      : resource.data ? <PluginModule descriptor={resource.data} /> : null
  const hasCalendarNavigation = resource.data?.navigation?.location === 'calendars'
    || (resource.loading && location.state?.navigationLocation === 'calendars')
  return hasCalendarNavigation
    ? <div className="grid gap-5"><CalendarPageNavigation active={`plugin:${pluginSlug}:${pageId}`} />{content}</div>
    : content
}

export function EntityPluginTab({ entity }: { entity: 'employee' | 'team' | 'project' }) {
  const { employeeId, teamId, projectId, pluginSlug = '', tabId = '' } = useParams()
  const objectId = entity === 'employee' ? employeeId : entity === 'team' ? teamId : projectId
  const { t } = useTranslation()
  const identity = `plugin:${pluginSlug}:${tabId}`
  const loader = useCallback((_key: string, signal: AbortSignal) => getUITab(entity, Number(objectId), identity, signal), [entity, objectId, identity])
  const resource = useEmployeeResource(`${entity}:${objectId}:${identity}`, loader)
  if (resource.loading) return <p role="status">{t('common.loading')}</p>
  if (resource.error) return <Alert tone="danger">{t('pluginUI.tabError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>
  return resource.data ? <PluginModule descriptor={resource.data} /> : null
}

export function EmployeePluginTab() { return <EntityPluginTab entity="employee" /> }
