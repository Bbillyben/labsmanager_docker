import { describe, expect, it } from 'vitest'
import { translate, translations, type TranslationKey } from './i18n'

const placeholders = (value: string) => [...value.matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map((match) => match[1]).sort()

describe('React translation catalogues', () => {
  it('has the same keys and interpolation variables in French and English', () => {
    const french = Object.keys(translations.fr).sort()
    const english = Object.keys(translations.en).sort()
    expect(english).toEqual(french)
    for (const key of french) {
      const translationKey = key as TranslationKey
      expect(placeholders(translations.en[translationKey])).toEqual(placeholders(translations.fr[translationKey]))
    }
  })

  it('renders shared and domain text in both languages', () => {
    expect(translate('fr', 'common.active')).toBe('Actif')
    expect(translate('en', 'common.active')).toBe('Active')
    expect(translate('fr', 'project.dateRange', { start: '01/01/2026', end: '31/12/2026' })).toBe('Du 01/01/2026 au 31/12/2026')
    expect(translate('en', 'project.dateRange', { start: '01/01/2026', end: '31/12/2026' })).toBe('From 01/01/2026 to 31/12/2026')
  })
})
