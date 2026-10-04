import { CircleQuestionMark } from 'lucide-react'
import { describe, expect, it } from 'vitest'
import { genericInfoIcon } from './genericInfoIcons'

describe('Organization Lucide icons', () => {
  it('resolves every R2.24a migrated icon and keeps the shared fallback', () => {
    for (const name of ['Signpost', 'Dna', 'PiggyBank', 'BookUser', 'Flag', 'Printer', 'Landmark', 'BadgeDollarSign', 'IdCard', 'Building2', 'Phone', 'Link', 'MapPin', 'Mail']) {
      expect(genericInfoIcon(name)).not.toBe(CircleQuestionMark)
    }
    expect(genericInfoIcon('Unknown')).toBe(CircleQuestionMark)
  })
})
