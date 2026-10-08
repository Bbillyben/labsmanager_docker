import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { DataConsistencyRenderer } from '../dashboard/DataConsistencyRenderer'
import { DataConsistencyPage } from './DataConsistencyPage'

const state = vi.hoisted(() => ({ accepted: false, canAccept: true, canReopen: true }))
const api = vi.hoisted(() => ({
  getConsistencySummary: vi.fn(), getConsistencyIssues: vi.fn(),
  acceptConsistencyIssue: vi.fn(), reopenConsistencyIssue: vi.fn(),
}))
vi.mock('../api/dataConsistency', () => ({ ...api, DATA_CONSISTENCY_CHANGED: 'data-consistency:changed' }))

const issue = {
  rule_key: 'contract_employee_not_project_participant', category: 'contracts',
  contract_id: 42, employee_id: 7, project_id: 3,
  label: 'Alice is not a participant in Atlas', employee_name: 'Alice', project_name: 'Atlas',
}
const acceptedIssue = { ...issue, exception: { id: 19, accepted_by: 'admin', accepted_at: '2026-10-07T12:00:00Z', reason: 'Intentional' } }

beforeEach(() => {
  vi.clearAllMocks()
  state.accepted = false; state.canAccept = true; state.canReopen = true
  api.getConsistencySummary.mockImplementation(async () => ({
    total: state.accepted ? 0 : 1, accepted_total: state.accepted ? 1 : 0,
    categories: [{ key: 'contracts', count: state.accepted ? 0 : 1 }], rules: [],
    capabilities: { can_accept: state.canAccept, can_reopen: state.canReopen },
  }))
  api.getConsistencyIssues.mockImplementation(async (status: string) => {
    const results = status === 'active' ? state.accepted ? [] : [issue] : state.accepted ? [acceptedIssue] : []
    return { count: results.length, next: null, previous: null, results }
  })
  api.acceptConsistencyIssue.mockImplementation(async () => { state.accepted = true; return acceptedIssue })
  api.reopenConsistencyIssue.mockImplementation(async () => { state.accepted = false; return { id: 19, status: 'reopened' } })
})

const renderPage = () => render(<MemoryRouter><I18nProvider><DataConsistencyPage /></I18nProvider></MemoryRouter>)

describe('Data Consistency frontend', () => {
  it('shows the Dashboard summary count, category and review link', async () => {
    render(<MemoryRouter><I18nProvider><DataConsistencyRenderer /></I18nProvider></MemoryRouter>)
    expect(await screen.findByText('1 issue(s)')).toBeInTheDocument()
    expect(screen.getByText('Contracts')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review issues' })).toHaveAttribute('href', '/tools/data-consistency')
  })

  it('reviews active and accepted issues, accepts with an optional reason, and reopens', async () => {
    const user = userEvent.setup()
    renderPage()
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Alice' })).toHaveAttribute('href', '/employees/7')
    await user.click(screen.getByRole('button', { name: 'Accept exception' }))
    const dialog = screen.getByRole('dialog')
    await user.type(within(dialog).getByRole('textbox', { name: 'Reason (optional)' }), 'Intentional')
    await user.click(within(dialog).getByRole('button', { name: 'Accept exception' }))
    await waitFor(() => expect(api.acceptConsistencyIssue).toHaveBeenCalledWith(issue, 'Intentional'))
    expect(await screen.findByText('No issues in this category.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Accepted/ }))
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    expect(screen.getByText('Intentional')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reopen issue' }))
    await waitFor(() => expect(api.reopenConsistencyIssue).toHaveBeenCalledWith(19))
    await user.click(screen.getByRole('button', { name: /Active/ }))
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
  })

  it('does not show mutation actions without backend capabilities', async () => {
    state.canAccept = false; state.canReopen = false
    renderPage()
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Accept exception' })).not.toBeInTheDocument()
  })
})
