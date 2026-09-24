import type { TranslationKey } from '../i18n/i18n'

type PageContext = {
  matches: (pathname: string) => boolean
  label: TranslationKey
}

// Deliberately small route metadata that can later grow into breadcrumb items.
const pageContexts: readonly PageContext[] = [
  { matches: (pathname) => pathname === '/', label: 'page.home' },
  { matches: (pathname) => /^\/employees\/?$/.test(pathname), label: 'page.employees' },
  { matches: (pathname) => /^\/employees\/\d+\/?$/.test(pathname), label: 'page.employees' },
]

export function getPageContext(pathname: string) {
  return pageContexts.find((context) => context.matches(pathname)) ?? null
}
