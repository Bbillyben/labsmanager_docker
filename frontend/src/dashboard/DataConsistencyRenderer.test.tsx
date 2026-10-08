import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getConsistencySummary } from '../api/dataConsistency'
import { I18nProvider } from '../i18n/I18nProvider'
import { DataConsistencyRenderer } from './DataConsistencyRenderer'

vi.mock('../api/dataConsistency', () => ({
  DATA_CONSISTENCY_CHANGED: 'data-consistency:changed',
  getConsistencySummary: vi.fn(),
}))

describe('DataConsistencyRenderer', () => {
  beforeEach(() => {
    vi.mocked(getConsistencySummary).mockResolvedValue({
      total: 3, accepted_total: 0,
      categories: [
        { key: 'planning', count: 1 },
        { key: 'expenses', count: 1 },
        { key: 'projects', count: 1 },
      ],
      rules: [], capabilities: { can_accept: false, can_reopen: false },
    })
  })

  it('shows the added categories and the existing review destination', async () => {
    render(<MemoryRouter><I18nProvider><DataConsistencyRenderer /></I18nProvider></MemoryRouter>)
    expect(await screen.findByText('Planning')).toBeInTheDocument()
    expect(screen.getByText('Expenses')).toBeInTheDocument()
    expect(screen.getByText('Projects')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review issues' })).toHaveAttribute('href', '/tools/data-consistency')
  })
})
