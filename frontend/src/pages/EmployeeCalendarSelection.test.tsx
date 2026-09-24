import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { EmployeeCalendar } from './EmployeeCalendar'

vi.mock('@fullcalendar/react', () => ({
  default: ({ selectable, select, initialView }: { selectable: boolean; select: (selection: { allDay: boolean; startStr: string; endStr: string }) => void; initialView: string }) =>
    <button disabled={!selectable} onClick={() => select(initialView === 'dayGridYear' ? { allDay: true, startStr: '2026-03-28', endStr: '2026-04-05' } : { allDay: true, startStr: '2026-10-06', endStr: '2026-10-11' })}>Select range</button>,
}))

const props = { anchor: new Date(2026, 9, 1), events: [], onOpen: vi.fn(), onCreate: vi.fn(), onChangeDates: vi.fn(), canCreate: true, canChange: false }

describe('Employee Calendar Leave selection', () => {
  it('opens creation with inclusive dates in month and year views', async () => {
    const user = userEvent.setup()
    for (const view of ['month', 'year'] as const) {
      const onCreate = vi.fn()
      const rendered = render(<EmployeeCalendar {...props} onCreate={onCreate} view={view} />)
      await user.click(screen.getByRole('button', { name: 'Select range' }))
      expect(onCreate).toHaveBeenCalledWith(view === 'year' ? { start_date: '2026-03-28', end_date: '2026-04-04' } : { start_date: '2026-10-06', end_date: '2026-10-10' })
      rendered.unmount()
    }
  })
  it('does not offer range selection in the five-year summary', () => {
    render(<EmployeeCalendar {...props} view="fiveYears" />)
    expect(screen.queryByRole('button', { name: 'Select range' })).not.toBeInTheDocument()
  })
})
