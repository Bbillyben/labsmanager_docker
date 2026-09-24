import { describe, expect, it } from 'vitest'
import { getPageContext } from './pageContext'

describe('topbar page context', () => {
  it('maps only the current React pages without creating breadcrumbs', () => {
    expect(getPageContext('/')?.label).toBe('page.home')
    expect(getPageContext('/employees/')?.label).toBe('page.employees')
    expect(getPageContext('/employees/42')?.label).toBe('page.employees')
    expect(getPageContext('/unknown')).toBeNull()
  })
})
