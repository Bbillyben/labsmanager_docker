import { describe, expect, it, vi } from 'vitest'
import type { UIModuleDescriptor } from '../api/uiContributions'
import { loadPluginComponent } from './pluginModuleLoader'

const descriptor = (version: string): UIModuleDescriptor => ({
  id: 'plugin:demo:page', plugin_slug: 'demo', local_id: 'page', slot: 'plugin.page', type: 'page',
  label: 'Demo', icon: null, behavior: null, confirm: false, priority: 0,
  module: 'main', component: 'Page', api_version: 1,
  module_url: `/static/plugins/demo/assets/main-${version}.js?v=${version}`,
  css_urls: [`/static/plugins/demo/assets/main-${version}.css?v=${version}`],
  asset_version: version, context: {},
})

describe('plugin module loader', () => {
  it('loads CSS once, reuses the module and invalidates it by asset version', async () => {
    const Page = () => null
    const importer = vi.fn(async () => ({ Page }))
    const first = loadPluginComponent(descriptor('cache-a'), importer)
    const repeated = loadPluginComponent(descriptor('cache-a'), importer)
    const link = document.head.querySelector<HTMLLinkElement>('link[href*="main-cache-a.css"]')!
    expect(link).toBeTruthy()
    link.dispatchEvent(new Event('load'))
    expect(await first).toBe(Page)
    expect(await repeated).toBe(Page)
    expect(importer).toHaveBeenCalledTimes(1)
    const updated = loadPluginComponent(descriptor('cache-b'), importer)
    document.head.querySelector<HTMLLinkElement>('link[href*="main-cache-b.css"]')!.dispatchEvent(new Event('load'))
    expect(await updated).toBe(Page)
    expect(importer).toHaveBeenCalledTimes(2)
  })

  it('rejects a remote script and an incompatible API version', async () => {
    const importer = vi.fn(async () => ({ Page: () => null }))
    await expect(loadPluginComponent({ ...descriptor('remote'), module_url: 'https://example.com/main.js' }, importer)).rejects.toThrow('Invalid plugin asset URL')
    await expect(loadPluginComponent({ ...descriptor('old'), api_version: 2 }, importer)).rejects.toThrow('Incompatible plugin UI API')
    expect(importer).not.toHaveBeenCalled()
  })
})
