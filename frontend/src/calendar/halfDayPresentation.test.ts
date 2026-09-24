import { describe, expect, it } from 'vitest'
import { translate } from '../i18n/i18n'
import { halfDayLabel } from './halfDayPresentation'

const t = (key: Parameters<typeof translate>[1]) => translate('fr', key)

describe('halfDayLabel', () => {
  it('distinguishes isolated and multi-day half-days', () => {
    expect(halfDayLabel({ start_date: '2026-09-10', end_date: '2026-09-10', start_period: 'ST', end_period: 'MI' }, t)).toBe('Matin')
    expect(halfDayLabel({ start_date: '2026-09-10', end_date: '2026-09-10', start_period: 'MI', end_period: 'EN' }, t)).toBe('Après-midi')
    expect(halfDayLabel({ start_date: '2026-09-10', end_date: '2026-09-12', start_period: 'MI', end_period: 'MI' }, t)).toBe('Midi → midi')
    expect(halfDayLabel({ start_date: '2026-09-10', end_date: '2026-09-12', start_period: 'ST', end_period: 'MI' }, t)).toBe('Jusqu’à midi')
  })
})
