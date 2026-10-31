import { useCallback } from 'react'
import { interpolate, useTranslation, type Language } from './i18n'

/** Literal FR/EN dictionaries registered by an independently built plugin. */
export type PluginTranslations = Partial<Record<Language, Record<string, string>>>

const dictionaries = new Map<string, PluginTranslations>()
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const keyPattern = /^[A-Za-z][A-Za-z0-9_.-]*$/

/** Register one plugin namespace for both supported languages.
 *
 * Repeating an identical registration is allowed for module reloads. A
 * conflicting registration or invalid namespace, key, or value throws.
 *
 * @param namespace - Plugin slug used as the translation namespace.
 * @param entries - Optional French and English key/value dictionaries.
 */
export function registerPluginTranslations(namespace: string, entries: PluginTranslations) {
  if (!slugPattern.test(namespace)) {
    throw new Error(`Invalid plugin translation namespace: ${namespace}`)
  }
  if (!entries || Array.isArray(entries) || typeof entries !== 'object') {
    throw new Error(`Invalid plugin translations: ${namespace}`)
  }
  const normalized: PluginTranslations = {}
  for (const language of ['fr', 'en'] as const) {
    const values = entries[language]
    if (values === undefined) continue
    if (!values || Array.isArray(values) || typeof values !== 'object') {
      throw new Error(`Invalid ${language} plugin translations: ${namespace}`)
    }
    const pairs = Object.entries(values)
    if (pairs.some(([key, value]) => !keyPattern.test(key) || typeof value !== 'string')) {
      throw new Error(`Invalid ${language} plugin translation entry: ${namespace}`)
    }
    normalized[language] = Object.fromEntries(pairs)
  }
  const existing = dictionaries.get(namespace)
  if (existing) {
    const same = (['fr', 'en'] as const).every((language) => {
      const previous = existing[language] ?? {}
      const next = normalized[language] ?? {}
      return Object.keys(previous).length === Object.keys(next).length &&
        Object.entries(next).every(([key, value]) => previous[key] === value)
    })
    if (!same) throw new Error(`Plugin translation namespace already registered: ${namespace}`)
    return
  }
  dictionaries.set(namespace, normalized)
}

/** Resolve a plugin key using the selected language, then FR and EN fallback.
 *
 * Missing keys render as `namespace.key`; variables are interpolated using
 * the same mechanism as host translations.
 */
export function pluginTranslate(language: Language, namespace: string, key: string,
  variables?: Record<string, string | number>) {
  const entries = dictionaries.get(namespace)
  const lookup = (selected: Language) => {
    const values = entries?.[selected]
    return values && Object.hasOwn(values, key) ? values[key] : undefined
  }
  const value = lookup(language) ?? lookup('fr') ?? lookup('en')
  return interpolate(value ?? `${namespace}.${key}`, variables)
}

/** Return the current language and a translation callback for one plugin. */
export function usePluginTranslation(namespace: string) {
  const { language } = useTranslation()
  const t = useCallback((key: string, variables?: Record<string, string | number>) =>
    pluginTranslate(language, namespace, key, variables), [language, namespace])
  return { language, t }
}
