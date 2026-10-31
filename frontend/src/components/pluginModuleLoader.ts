import type { ComponentType } from 'react'
import type { UIModuleDescriptor } from '../api/uiContributions'

/** Named export rendered with the context supplied by the host API. */
export type PluginComponent = ComponentType<{ context: UIModuleDescriptor['context']; onClose?: () => void }>
type PluginExports = Record<string, unknown>
type Importer = (url: string) => Promise<PluginExports>
const modules = new Map<string, Promise<PluginExports>>()
const styles = new Map<string, Promise<void>>()

function assetUrl(raw: string, slug: string, extension: 'js' | 'css') {
  // The server resolves assets from the plugin manifest; the browser repeats
  // the same-origin and plugin-directory boundary before importing code.
  const url = new URL(raw, window.location.href)
  if (url.origin !== window.location.origin || !url.pathname.startsWith(`/static/plugins/${slug}/assets/`)
      || !url.pathname.endsWith(`.${extension}`)) throw new Error('Invalid plugin asset URL')
  return url.href
}

function loadStyle(url: string) {
  if (styles.has(url)) return styles.get(url)!
  const pending = new Promise<void>((resolve, reject) => {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = url
    link.onload = () => resolve()
    link.onerror = () => { link.remove(); reject(new Error('Plugin stylesheet unavailable')) }
    document.head.appendChild(link)
  })
  styles.set(url, pending)
  pending.catch(() => styles.delete(url))
  return pending
}

const importModule: Importer = (url) => import(/* @vite-ignore */ url) as Promise<PluginExports>

/** Load one versioned plugin entry and its CSS, then find its named component.
 *
 * Successful imports and stylesheet loads are shared across mounts. Failed
 * loads are evicted so a later render can retry. The optional importer exists
 * for isolated tests; production uses a dynamic browser import.
 *
 * @param descriptor - Server-validated module URL, styles, version, and export.
 * @param importer - Module loader used in place of the browser import in tests.
 * @returns The named React component supplied by the plugin entry.
 * @throws If the descriptor, asset URL, network load, or named export is invalid.
 */
export async function loadPluginComponent(descriptor: UIModuleDescriptor, importer: Importer = importModule): Promise<PluginComponent> {
  if (descriptor.api_version !== 1 || !descriptor.component) throw new Error('Incompatible plugin UI API')
  const moduleUrl = assetUrl(descriptor.module_url, descriptor.plugin_slug, 'js')
  const css = descriptor.css_urls.map((url) => assetUrl(url, descriptor.plugin_slug, 'css'))
  let pending = modules.get(moduleUrl)
  if (!pending) {
    pending = importer(moduleUrl)
    modules.set(moduleUrl, pending)
    pending.catch(() => modules.delete(moduleUrl))
  }
  const [exports] = await Promise.all([pending, ...css.map(loadStyle)])
  const component = exports[descriptor.component]
  if (typeof component !== 'function') throw new Error('Plugin component missing')
  return component as PluginComponent
}
