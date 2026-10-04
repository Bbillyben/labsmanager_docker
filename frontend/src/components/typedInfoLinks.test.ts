import { describe, expect, it } from 'vitest'
import { typedInfoHref } from './typedInfoLinks'

describe('typed information links', () => {
  it('uses the selected map provider and encodes the address', () => {
    expect(typedInfoHref('addr', '1 rue des Écoles, Paris', 'gmap')).toBe('https://www.google.com/maps/search/?api=1&query=1%20rue%20des%20%C3%89coles%2C%20Paris')
    expect(typedInfoHref('addr', '1 rue des Écoles, Paris', 'opensm')).toBe('https://www.openstreetmap.org/search?query=1%20rue%20des%20%C3%89coles%2C%20Paris')
  })
  it('preserves copy-only values and rejects unsafe links', () => {
    expect(typedInfoHref('none', 'any', 'gmap')).toBeNull()
    expect(typedInfoHref('mail', 'a@example.org', 'gmap')).toBe('mailto:a@example.org')
    expect(typedInfoHref('tel', '0123456789', 'gmap')).toBe('tel:0123456789')
    expect(typedInfoHref('link', 'javascript:alert(1)', 'gmap')).toBeNull()
    expect(typedInfoHref('addr', '', 'gmap')).toBeNull()
  })
})
