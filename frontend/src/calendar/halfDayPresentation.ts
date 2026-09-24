import type { I18nContextValue } from '../i18n/i18n'

type HalfDayData = {
  start_date?: unknown
  end_date?: unknown
  start_period?: unknown
  end_period?: unknown
}

export function halfDayLabel(data: HalfDayData, t: I18nContextValue['t']) {
  const startsAtMidday = data.start_period === 'MI'
  const endsAtMidday = data.end_period === 'MI'
  if (!startsAtMidday && !endsAtMidday) return ''
  if (data.start_date === data.end_date) {
    return startsAtMidday ? t('leaves.afternoon') : t('leaves.morning')
  }
  if (startsAtMidday && endsAtMidday) return t('leaves.middayRange')
  return startsAtMidday ? t('leaves.halfDayStart') : t('leaves.halfDayEnd')
}
