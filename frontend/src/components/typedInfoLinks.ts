import type { InfoType } from '../api/organizations'

export type InfoKind = InfoType['type']

export function typedInfoHref(kind: InfoKind, value: string | null, mapProvider: 'gmap' | 'opensm') {
  if (!value?.trim()) return null
  if (kind === 'tel') return `tel:${value.trim()}`
  if (kind === 'mail') return `mailto:${value.trim()}`
  if (kind === 'addr') return mapProvider === 'opensm'
    ? `https://www.openstreetmap.org/search?query=${encodeURIComponent(value)}`
    : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(value)}`
  if (kind === 'link') {
    try {
      const url = new URL(value)
      return ['https:', 'http:'].includes(url.protocol) ? url.href : null
    } catch { return null }
  }
  return null
}

