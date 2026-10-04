import type { ComponentType } from 'react'

export type PrintPage = { size: 'A4' | 'A3'; orientation: 'portrait' | 'landscape' }
export type PrintRequest = { renderer: string; title: string; subtitle?: string; state: unknown; page?: PrintPage }
export type PrintRendererProps<T = unknown> = { state: T; onReady: () => void }
export type PrintRendererDefinition = {
  key: string
  label: string
  render: ComponentType<PrintRendererProps<never>>
  defaultPage: PrintPage
}

const renderers = new Map<string, PrintRendererDefinition>()

export function registerPrintRenderer(definition: PrintRendererDefinition) {
  if (renderers.has(definition.key)) throw new Error(`Print renderer already registered: ${definition.key}`)
  renderers.set(definition.key, definition)
}

export function getPrintRenderer(key: string) { return renderers.get(key) ?? null }
