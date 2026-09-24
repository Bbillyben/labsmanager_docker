import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ProjectWorkload } from '../api/employees'
import { ProjectWorkloadTimeline } from '../components/ProjectWorkloadTimeline'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { EmployeeProjectWorkload } from './EmployeeProjectWorkload'
import { workloadWindow } from './projectWorkloadWindow'

const workload: ProjectWorkload = {
  range: { start: '2026-06-21', end: '2027-06-21' },
  segments: [
    { start: '2026-06-21', end: '2026-09-30', total_quotity: '0.800', projects: [{ id: 1, name: 'NUMETAB', quotity: '0.800', can_view: true }] },
    { start: '2026-10-01', end: '2027-06-21', total_quotity: '1.500', projects: [{ id: 1, name: 'NUMETAB', quotity: '0.800', can_view: true }, { id: 2, name: 'PreciseIT', quotity: '0.700', can_view: false }] },
  ],
}

function renderTranslated(node: ReactNode) {
  return render(<I18nProvider>{node}</I18nProvider>)
}

describe('Employee project workload container', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date('2026-09-21T12:00:00Z'))
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('uses the prospective 1-year window by default and changes presets on demand', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const requests: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      requests.push(String(input))
      return jsonResponse(workload)
    })

    renderTranslated(<EmployeeProjectWorkload employeeId="12" />)

    await screen.findByRole('group', { name: 'Charge projet au cours du temps' })
    expect(requests).toEqual(['/api/v1/employees/12/project-workload/?start=2026-06-21&end=2027-06-21'])
    expect(screen.getByRole('button', { name: '1 an' })).toHaveAttribute('aria-pressed', 'true')
    expect(requests.some((url) => url.includes('range=all'))).toBe(false)

    await user.click(screen.getByRole('button', { name: '5 ans' }))
    await waitFor(() => expect(requests.at(-1)).toBe('/api/v1/employees/12/project-workload/?start=2025-09-21&end=2030-09-21'))

    await user.click(screen.getByRole('button', { name: 'Tout' }))
    await waitFor(() => expect(requests.at(-1)).toBe('/api/v1/employees/12/project-workload/?range=all'))
    expect(screen.queryByRole('button', { name: /fenêtre de 6 mois/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Aujourd’hui' })).not.toBeInTheDocument()
  })

  it('moves either bounded preset by six months and returns to today', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const requests: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      requests.push(String(input))
      return jsonResponse(workload)
    })
    renderTranslated(<EmployeeProjectWorkload employeeId="12" />)
    await screen.findByRole('group', { name: 'Charge projet au cours du temps' })

    await user.click(screen.getByRole('button', { name: 'Avancer la fenêtre de 6 mois' }))
    await waitFor(() => expect(requests.at(-1)).toContain('start=2026-12-21&end=2027-12-21'))
    expect(screen.getByRole('button', { name: 'Aujourd’hui' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reculer la fenêtre de 6 mois' }))
    await waitFor(() => expect(requests.at(-1)).toContain('start=2026-06-21&end=2027-06-21'))
    expect(screen.queryByRole('button', { name: 'Aujourd’hui' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reculer la fenêtre de 6 mois' }))
    await waitFor(() => expect(requests.at(-1)).toContain('start=2025-12-21&end=2026-12-21'))
    await user.click(screen.getByRole('button', { name: 'Aujourd’hui' }))
    await waitFor(() => expect(requests.at(-1)).toContain('start=2026-06-21&end=2027-06-21'))
  })

  it('calculates clamped calendar windows without daily sampling', () => {
    expect(workloadWindow(new Date('2026-05-31T00:00:00Z'), 'year', 0)).toEqual({ start: '2026-02-28', end: '2027-02-28' })
    expect(workloadWindow(new Date('2026-09-21T00:00:00Z'), 'fiveYears', 0)).toEqual({ start: '2025-09-21', end: '2030-09-21' })
  })
})

describe('ProjectWorkloadTimeline', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  })

  it('shows the 100% threshold, only the excess area, and keyboard-accessible composition', async () => {
    const user = userEvent.setup()
    const props = { onPresetChange: vi.fn(), onPrevious: vi.fn(), onNext: vi.fn(), onToday: vi.fn() }
    const { container } = renderTranslated(<ProjectWorkloadTimeline data={workload} preset="year" shifted={false} {...props} />)

    expect(container.querySelector('[data-threshold="100"]')).toBeInTheDocument()
    expect(container.querySelectorAll('[data-overload="true"]')).toHaveLength(1)
    expect(screen.getByLabelText(/Surcharge de 50 % au-dessus de 100 %/)).toBeInTheDocument()

    const overloadedPeriod = screen.getByRole('button', { name: /Charge projet : 150/ })
    overloadedPeriod.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('status')).toHaveTextContent(/Charge projet : 150 %/)
    expect(screen.getByText('NUMETAB')).toBeInTheDocument()
    expect(screen.getByText('PreciseIT')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'PreciseIT' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Fermer le détail de la période' })).toBeInTheDocument()
  })

  it('renders a valid zero-workload window as an empty state', () => {
    const empty: ProjectWorkload = { range: { start: '2026-01-01', end: '2026-12-31' }, segments: [{ start: '2026-01-01', end: '2026-12-31', total_quotity: '0', projects: [] }] }
    renderTranslated(<ProjectWorkloadTimeline data={empty} preset="year" shifted={false} onPresetChange={vi.fn()} onPrevious={vi.fn()} onNext={vi.fn()} onToday={vi.fn()} />)
    expect(screen.getAllByText('Aucune participation dans cette période.')).toHaveLength(2)
  })
})
