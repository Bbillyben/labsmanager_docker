import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlanningDelayPreview } from '../api/planning'
import { ApiError } from '../api/errors'
import { I18nProvider } from '../i18n/I18nProvider'
import { ProjectPlanningDelaySheet } from './ProjectPlanningDelaySheet'

const api = vi.hoisted(() => ({ preview: vi.fn(), apply: vi.fn() }))
vi.mock('../api/planning', async (importOriginal) => ({
  ...await importOriginal<typeof import('../api/planning')>(),
  previewProjectPlanningDelay: api.preview,
  applyProjectPlanningDelay: api.apply,
}))

const nodes = [
  { id: 1, name: 'MS 1', project: { id: 7, name: 'Atlas' }, work_kind: 'milestone' as const, end_date: '2026-11-01', eligible: true, unavailable_reason: null },
  { id: 2, name: 'MS 1.1', project: { id: 7, name: 'Atlas' }, work_kind: 'milestone' as const, end_date: '2026-11-01', eligible: true, unavailable_reason: null },
  { id: 3, name: 'MS 1.1.1', project: { id: 7, name: 'Atlas' }, work_kind: 'milestone' as const, end_date: '2026-11-01', eligible: true, unavailable_reason: null },
  { id: 4, name: 'MS 1.1.2', project: { id: 7, name: 'Atlas' }, work_kind: 'milestone' as const, end_date: '2026-11-01', eligible: true, unavailable_reason: null },
  { id: 5, name: 'MS 1.2', project: { id: 7, name: 'Atlas' }, work_kind: 'milestone' as const, end_date: '2026-11-01', eligible: true, unavailable_reason: null },
]
const edges = [
  { id: 12, predecessor_id: 1, successor_id: 2 },
  { id: 23, predecessor_id: 2, successor_id: 3 },
  { id: 24, predecessor_id: 2, successor_id: 4 },
  { id: 15, predecessor_id: 1, successor_id: 5 },
]

function makePreview(roots: number[], cuts: number[]): PlanningDelayPreview {
  const included = cuts.includes(15) ? [1, 2, 3, 4] : [1, 2, 3, 4, 5]
  return {
    root_ids: roots, blocked_dependency_ids: cuts, days: 14,
    nodes: nodes.map((node) => ({ ...node, affected: included.includes(node.id) })), edges,
    affected: included.map((id) => ({ id, old_end_date: '2026-11-01', new_end_date: '2026-11-15' })),
    excluded_ids: nodes.filter((node) => !included.includes(node.id)).map((node) => node.id),
    revision: cuts.join(',') || 'initial',
  }
}

beforeEach(() => {
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en-US'] })
  api.preview.mockReset().mockImplementation((_project, intent) => Promise.resolve(makePreview(intent.root_ids, intent.blocked_dependency_ids)))
  api.apply.mockReset().mockResolvedValue({ affected_ids: [1, 2, 3, 4] })
})

describe('Project Planning delay Sheet', () => {
  it('previews a full branch, cuts one edge and applies only the recalculated intent', async () => {
    const user = userEvent.setup()
    const onApplied = vi.fn()
    render(<I18nProvider><ProjectPlanningDelaySheet projectId="7" rootIds={[1]} returnFocus={createRef<HTMLElement>()} onClose={vi.fn()} onApplied={onApplied} /></I18nProvider>)
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByRole('spinbutton', { name: /Delay by/ })).toHaveValue(14)
    expect(await within(sheet).findByText(/5 items will be delayed by 14 days/)).toBeInTheDocument()
    expect(within(sheet).getByText('MS 1.1.1')).toBeInTheDocument()
    expect(within(sheet).getByText('MS 1.1.2')).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Stop propagation to “MS 1.2”' }))
    expect(await within(sheet).findByText(/4 items will be delayed by 14 days/)).toHaveTextContent('1 excluded')
    await user.click(within(sheet).getByRole('button', { name: 'Apply delay' }))
    await waitFor(() => expect(api.apply).toHaveBeenCalledWith('7', { root_ids: [1], blocked_dependency_ids: [15], days: 14 }, '15'))
    expect(onApplied).toHaveBeenCalledOnce()
  })

  it('shows a shared descendant twice as one affected item and blocks duplicate submission', async () => {
    api.preview.mockImplementation((_project, intent) => {
      const affected = intent.blocked_dependency_ids.length === 2 ? [1, 2] : [1, 2, 3]
      return Promise.resolve({
        ...makePreview(intent.root_ids, intent.blocked_dependency_ids),
        nodes: nodes.slice(0, 3).map((node) => ({ ...node, affected: affected.includes(node.id) })),
        edges: [{ id: 13, predecessor_id: 1, successor_id: 3 }, { id: 23, predecessor_id: 2, successor_id: 3 }],
        affected: affected.map((id) => ({ id, old_end_date: '2026-11-01', new_end_date: '2026-11-15' })),
        excluded_ids: affected.length === 2 ? [3] : [],
      })
    })
    let finish!: (result: { affected_ids: number[] }) => void
    api.apply.mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    const user = userEvent.setup()
    render(<I18nProvider><ProjectPlanningDelaySheet projectId="7" rootIds={[1, 2]} returnFocus={createRef<HTMLElement>()} onClose={vi.fn()} onApplied={vi.fn()} /></I18nProvider>)
    expect(await screen.findByText(/3 items will be delayed by 14 days/)).toBeInTheDocument()
    expect(screen.getByText(/also present on another path/)).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Stop propagation to “MS 1.1.1”' })[0])
    await waitFor(() => expect(api.preview).toHaveBeenCalledTimes(2))
    expect(await screen.findByText(/3 items will be delayed by 14 days/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Stop propagation to “MS 1.1.1”' }))
    expect(await screen.findByText(/2 items will be delayed by 14 days/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Apply delay' }))
    expect(screen.getByRole('button', { name: 'Applying…' })).toBeDisabled()
    expect(api.apply).toHaveBeenCalledTimes(1)
    finish({ affected_ids: [1, 2, 3] })
  })

  it('refreshes the preview after a concurrent Planning change without claiming success', async () => {
    api.apply.mockRejectedValueOnce(new ApiError(409, { detail: 'Planning changed' }))
    const onApplied = vi.fn()
    render(<I18nProvider><ProjectPlanningDelaySheet projectId="7" rootIds={[1]} returnFocus={createRef<HTMLElement>()} onClose={vi.fn()} onApplied={onApplied} /></I18nProvider>)
    expect(await screen.findByText(/5 items will be delayed by 14 days/)).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Apply delay' }))
    expect(await screen.findByText(/Planning changed. Review the new preview/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Apply delay' })).toBeDisabled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(api.preview).toHaveBeenCalledTimes(2))
    expect(onApplied).not.toHaveBeenCalled()
  })
})
