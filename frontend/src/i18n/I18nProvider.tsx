import { useEffect, useMemo, useReducer, type PropsWithChildren } from 'react'
import { browserLanguage, I18nContext, translate, type I18nContextValue } from './i18n'

export function I18nProvider({ children }: PropsWithChildren) {
  const [, refreshLanguage] = useReducer((value: number) => value + 1, 0)
  const language = browserLanguage()
  const value = useMemo<I18nContextValue>(() => ({
    language,
    t: (key, variables) => translate(language, key, variables),
  }), [language])

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  useEffect(() => {
    window.addEventListener('languagechange', refreshLanguage)
    return () => window.removeEventListener('languagechange', refreshLanguage)
  }, [])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
