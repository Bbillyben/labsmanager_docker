import { useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPersonalPlugins, getPluginUserSettings, resetPluginUserSetting, updatePluginUserSetting } from '../api/pluginPersonal'
import { SettingList } from '../components/SettingList'
import { PluginTokensSection } from '../components/PluginTokensSection'
import { UserPluginActions } from '../components/PluginContributions'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './SettingsHubPage.module.css'

export function UserPluginsPage() {
  const { t } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getPersonalPlugins(signal), [])
  const resource = useEmployeeResource('personal-plugins', loader)
  return <section className={styles.section}><h2>{t('pluginSettings.mine')}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('pluginSettings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <div>
      {resource.data.results.length === 0 && <p className={styles.empty}>{t('pluginSettings.empty')}</p>}
      {resource.data.results.map((plugin) => <div className={styles.row} key={plugin.key}><div>
        <Link to={`/settings/my-plugins/${encodeURIComponent(plugin.key)}`}>{plugin.human_name}</Link>
        {plugin.description && <p className={styles.description}>{plugin.description}</p>}
      </div></div>)}
    </div>}
  </section>
}

function PluginPreferences({ pluginKey }: { pluginKey: string }) {
  const { t } = useTranslation()
  const loader = useCallback((key: string, signal: AbortSignal) => getPluginUserSettings(key, signal), [])
  const resource = useEmployeeResource(pluginKey, loader)
  return <section className={styles.section}><h2>{t('pluginSettings.preferences')}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('pluginSettings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <SettingList key={pluginKey} settings={resource.data.settings} onChange={(key, value) => updatePluginUserSetting(pluginKey, key, value)} onReset={(key) => resetPluginUserSetting(pluginKey, key)} />}
  </section>
}

export function UserPluginDetailPage() {
  const { pluginKey = '' } = useParams()
  const { t } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getPersonalPlugins(signal), [])
  const resource = useEmployeeResource(pluginKey, loader)
  const plugin = resource.data?.results.find((item) => item.key === pluginKey)
  return <div className={styles.content}><Link to="/settings/my-plugins">← {t('pluginSettings.mine')}</Link>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('pluginSettings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && !plugin && <Alert tone="danger">{t('pluginSettings.unavailable')}</Alert>}
    {plugin && <><section className={styles.section}><h2>{plugin.human_name}</h2>{plugin.description && <p className={styles.description}>{plugin.description}</p>}</section>
      {plugin.user_settings && <PluginPreferences key={pluginKey} pluginKey={pluginKey} />}
      {plugin.user_tokens && <PluginTokensSection key={`${pluginKey}-user`} pluginKey={pluginKey} kind="user" />}
      {plugin.ui_actions && <UserPluginActions pluginKey={pluginKey} className={styles.section} />}
    </>}
  </div>
}
