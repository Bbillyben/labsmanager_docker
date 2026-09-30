import type { useTranslation } from '../i18n/i18n'

type Translator = ReturnType<typeof useTranslation>['t']

export function contractPeriod(start: string | null, end: string | null, language: string, t: Translator) {
  const format = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  if (start && end) return t('employee.fromTo', { start: format(start), end: format(end) })
  if (start) return t('employee.since', { date: format(start) })
  if (end) return t('employee.until', { date: format(end) })
  return t('contracts.openPeriod')
}

export function contractPercent(value: string, language: string) {
  return `${new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(Number(value) * 100)} %`
}
