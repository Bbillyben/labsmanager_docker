/** Public host exports for independently built plugin UI modules (contract v1).
 *
 * Plugin bundles import supported React components and helpers from this
 * stable entry instead of bundling their own copy. The host publishes the
 * versioned entry at `/static/frontend/plugin-api.js` during the build.
 * Extend this surface deliberately: removing an export breaks deployed plugin
 * bundles even when the host's internal import paths still work.
 */
export const PLUGIN_UI_API_VERSION = 1 as const

export { EntitySearch } from './filters/EntitySearch'
export { employeeFilterSources } from './config/employeeFilterSources'
export { teamFilterSources } from './config/teamFilterSources'
export { projectFilterSources } from './config/projectFilterSources'
export { Button } from './ui/Button'
export { Input } from './components/ui/input'
export { EntityActionMenu } from './components/EntityActionMenu'
export type { EntityAction, EntityActionGroup } from './components/EntityActionMenu'
export { Alert } from './ui/Alert'
export { copyPluginToken } from './components/copyPluginToken'
export { PluginPublishedCalendarActions } from './components/PluginContributions'
export { PluginCalendarView } from './calendar/PluginCalendarView'
export type { PluginCalendarEvent, PluginCalendarResource, PluginCalendarRange, PluginCalendarMode } from './calendar/pluginCalendarPresentation'
export { ConfirmDialog } from './components/common/ConfirmDialog'
export { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './components/ui/sheet'
export { useTranslation } from './i18n/i18n'
export { registerPluginTranslations, usePluginTranslation } from './i18n/pluginTranslations'
export type { PluginTranslations } from './i18n/pluginTranslations'
export { apiRequest } from './api/client'
export type { EntitySearchSource } from './filters/types'
