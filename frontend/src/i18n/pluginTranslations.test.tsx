import { render, screen, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { I18nProvider } from './I18nProvider'
import { translate } from './i18n'
import { pluginTranslate, registerPluginTranslations, usePluginTranslation } from './pluginTranslations'

function Example({ namespace }: { namespace: string }) {
  const { t } = usePluginTranslation(namespace)
  return <p>{t('greeting', { name: 'Ada' })}</p>
}

it('uses the host language, interpolation and French fallback without a second provider', async () => {
  const previous = Object.getOwnPropertyDescriptor(navigator, 'languages')
  registerPluginTranslations('first-fixture', {
    fr: { greeting: 'Bonjour {name}', fallback: 'Repli français' },
    en: { greeting: 'Hello {name}' },
  })
  try {
    Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    render(<I18nProvider><Example namespace="first-fixture" /></I18nProvider>)
    expect(screen.getByText('Bonjour Ada')).toBeInTheDocument()
    Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en-GB'] })
    window.dispatchEvent(new Event('languagechange'))
    await waitFor(() => expect(screen.getByText('Hello Ada')).toBeInTheDocument())
    expect(pluginTranslate('en', 'first-fixture', 'fallback')).toBe('Repli français')
    expect(pluginTranslate('en', 'first-fixture', 'absent')).toBe('first-fixture.absent')
    expect(pluginTranslate('en', 'first-fixture', 'constructor')).toBe('first-fixture.constructor')
  } finally {
    if (previous) Object.defineProperty(navigator, 'languages', previous)
  }
})

it('keeps namespaces isolated, rejects overwrites and accepts identical registration', () => {
  const first = { fr: { greeting: 'Premier' }, en: { greeting: 'First' } }
  registerPluginTranslations('isolation-first', first)
  registerPluginTranslations('isolation-first', first)
  registerPluginTranslations('isolation-second', { fr: { greeting: 'Second' } })
  expect(pluginTranslate('fr', 'isolation-first', 'greeting')).toBe('Premier')
  expect(pluginTranslate('fr', 'isolation-second', 'greeting')).toBe('Second')
  expect(() => registerPluginTranslations('isolation-first', { fr: { greeting: 'Écrasé' } })).toThrow('already registered')
  registerPluginTranslations('calendars', { fr: { title: 'Titre propre au plugin' } })
  expect(pluginTranslate('fr', 'calendars', 'title')).toBe('Titre propre au plugin')
  expect(translate('fr', 'calendars.title')).toBe('Calendriers')
  expect(() => registerPluginTranslations('bad.namespace', { fr: { greeting: 'No' } })).toThrow('Invalid')
  expect(pluginTranslate('fr', 'isolation-first', 'greeting')).toBe('Premier')
})

it('loads a plugin dictionary only with its module and tolerates plugins without one', async () => {
  expect(pluginTranslate('fr', 'lazy-fixture', 'ready')).toBe('lazy-fixture.ready')
  expect(pluginTranslate('fr', 'untranslated-plugin', 'title')).toBe('untranslated-plugin.title')
  await import('./pluginTranslations.lazy.fixture')
  expect(pluginTranslate('fr', 'lazy-fixture', 'ready')).toBe('Chargé à la demande')
})
