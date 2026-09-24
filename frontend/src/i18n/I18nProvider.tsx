import { useEffect, useMemo, type PropsWithChildren } from 'react'
import { browserLanguage, I18nContext, translate, type I18nContextValue } from './i18n'

export function I18nProvider({ children }: PropsWithChildren) {
  const language = browserLanguage()
  const value = useMemo<I18nContextValue>(() => ({
    language,
    t: (key, variables) => translate(language, key, variables),
  }), [language])

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
