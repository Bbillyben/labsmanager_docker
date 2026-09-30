import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { EmployeeCalendar } from './EmployeeCalendar'
import { projectCalendarScopes, type ProjectCalendarScope } from './projectCalendarScopes'

vi.mock('@fullcalendar/react', () => ({
  default: ({ selectable, select, initialView }: { selectable: boolean; select: (selection: { allDay: boolean; startStr: string; endStr: string }) => void; initialView: string }) =>
    <button data-view={initialView} disabled={!selectable} onClick={() => select(initialView === 'dayGridYearCustom' ? { allDay: true, startStr: '2026-03-28', endStr: '2026-04-05' } : { allDay: true, startStr: '2026-10-06', endStr: '2026-10-11' })}>Select range</button>,
}))

const props = { anchor: new Date(2026, 9, 1), events: [], onOpen: vi.fn(), onCreate: vi.fn(), onChangeDates: vi.fn(), canCreate: true, canChange: false }

describe('Employee Calendar Leave selection', () => {
  it('opens creation with inclusive dates in each shared scope', async () => {
    const user = userEvent.setup()
    for (const projectScope of ['fifteenDays', 'month', 'twoMonths', 'year'] as ProjectCalendarScope[]) {
      const onCreate = vi.fn()
      const rendered = render(<EmployeeCalendar {...props} onCreate={onCreate} projectScope={projectScope} />)
      const select = screen.getByRole('button', { name: 'Select range' })
      expect(select).toHaveAttribute('data-view', projectCalendarScopes[projectScope].calendarView)
      await user.click(select)
      expect(onCreate).toHaveBeenCalledWith(projectScope === 'year' ? { start_date: '2026-03-28', end_date: '2026-04-04' } : { start_date: '2026-10-06', end_date: '2026-10-10' })
      rendered.unmount()
    }
  })
  it('disables selection without the creation capability', () => {
    render(<EmployeeCalendar {...props} canCreate={false} projectScope="month" />)
    expect(screen.getByRole('button', { name: 'Select range' })).toBeDisabled()
  })
})
