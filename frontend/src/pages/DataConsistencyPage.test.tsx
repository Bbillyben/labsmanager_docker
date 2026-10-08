import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { DataConsistencyRenderer } from '../dashboard/DataConsistencyRenderer'
import { DataConsistencyPage } from './DataConsistencyPage'

const state = vi.hoisted(() => ({ accepted: false, resolved: false, dateResolved: false, canAccept: true, canReopen: true, canAdd: true, canChange: true }))
const api = vi.hoisted(() => ({
  getConsistencySummary: vi.fn(), getConsistencyIssues: vi.fn(),
  acceptConsistencyIssue: vi.fn(), reopenConsistencyIssue: vi.fn(),
}))
const projectApi = vi.hoisted(() => ({ getProject: vi.fn(), createProjectParticipant: vi.fn(), updateProject: vi.fn() }))
const employeeApi = vi.hoisted(() => ({ getEmployee: vi.fn(), updateEmployee: vi.fn() }))
const fundingApi = vi.hoisted(() => ({ getFundDetail: vi.fn(), updateFund: vi.fn() }))
vi.mock('../api/dataConsistency', () => ({ ...api, DATA_CONSISTENCY_CHANGED: 'data-consistency:changed' }))
vi.mock('../api/projects', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/projects')>(), ...projectApi }))
vi.mock('../api/employees', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/employees')>(), ...employeeApi }))
vi.mock('../api/funding', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/funding')>(), ...fundingApi }))
vi.mock('../config/employeeFilterSources', () => ({ employeeFilterSources: { allEmployees: { resolve: async () => ({ value: '7', label: 'Alice' }), search: async () => ({ options: [], hasMore: false }) } } }))

const issue = {
  rule_key: 'contract_employee_not_project_participant', category: 'contracts',
  contract_id: 42, employee_id: 7, project_id: 3,
  label: 'Alice is not a participant in Atlas', employee_name: 'Alice', project_name: 'Atlas',
}
const acceptedIssue = { ...issue, exception: { id: 19, accepted_by: 'admin', accepted_at: '2026-10-07T12:00:00Z', reason: 'Intentional' } }
const contractDateIssue = {
  rule_key: 'contract_outside_project_dates', category: 'contracts', contract_id: 42, employee_id: 7,
  project_id: 3, label: 'Contract dates outside Atlas', employee_name: 'Alice', project_name: 'Atlas',
  reason: 'both', project_start_date: '2025-01-01', project_end_date: '2025-12-31',
  child_start_date: '2024-12-01', child_end_date: '2026-01-01',
}
const fundDateIssue = { ...contractDateIssue, rule_key: 'fund_outside_project_dates', category: 'funds', contract_id: undefined, employee_id: undefined, employee_name: undefined, fund_id: 8, label: 'Fund dates outside Atlas' }
const employeeDateIssue = { ...contractDateIssue, rule_key: 'contract_outside_employee_dates', parent_kind: 'employee', label: 'Contract dates outside Alice' }
const milestoneDateIssue = { ...contractDateIssue, rule_key: 'milestone_outside_project_dates', category: 'planning', contract_id: undefined, employee_id: undefined, employee_name: undefined, milestone_id: 91, label: 'Milestone dates outside Atlas' }
const taskDateIssue = { ...milestoneDateIssue, rule_key: 'task_outside_project_dates', milestone_id: 92, label: 'Task dates outside Atlas' }
const contractFundIssue = { ...contractDateIssue, rule_key: 'contract_outside_fund_dates', fund_id: 8, parent_kind: 'fund', label: 'Contract dates outside fund' }
const expenseFundIssue = { ...fundDateIssue, rule_key: 'expense_outside_fund_dates', category: 'expenses', expense_id: 93, fund_id: 8, parent_kind: 'fund', label: 'Expense date outside fund' }
const leaderIssue = { rule_key: 'project_without_leader', category: 'projects', project_id: 3, label: 'Atlas has no leader', project_name: 'Atlas' }
const extraIssues: Record<string, object> = {
  contract_outside_employee_dates: employeeDateIssue,
  milestone_outside_project_dates: milestoneDateIssue,
  task_outside_project_dates: taskDateIssue,
  contract_outside_fund_dates: contractFundIssue,
  expense_outside_fund_dates: expenseFundIssue,
  project_without_leader: leaderIssue,
}

beforeEach(() => {
  vi.clearAllMocks()
  state.accepted = false; state.resolved = false; state.dateResolved = false; state.canAccept = true; state.canReopen = true; state.canAdd = true; state.canChange = true
  api.getConsistencySummary.mockImplementation(async () => ({
    total: state.accepted || state.resolved ? 0 : 1, accepted_total: state.accepted ? 1 : 0,
    categories: [{ key: 'contracts', count: state.accepted || state.resolved ? 0 : 1 }],
    rules: [
      { rule_key: 'contract_employee_not_project_participant', category: 'contracts', count: 1, accepted_count: 0 },
      { rule_key: 'contract_outside_project_dates', category: 'contracts', count: 1, accepted_count: 0 },
      { rule_key: 'fund_outside_project_dates', category: 'funds', count: 1, accepted_count: 0 },
      ...Object.keys(extraIssues).map((rule_key) => ({ rule_key, category: 'other', count: 1, accepted_count: 0 })),
    ],
    capabilities: { can_accept: state.canAccept, can_reopen: state.canReopen },
  }))
  api.getConsistencyIssues.mockImplementation(async (status: string, _offset: number, _limit: number, _signal: AbortSignal, ruleKey: string) => {
    const results = extraIssues[ruleKey] ? status === 'active' && !state.dateResolved ? [extraIssues[ruleKey]] : []
      : ruleKey === 'contract_outside_project_dates' ? status === 'active' && !state.dateResolved ? [contractDateIssue] : []
      : ruleKey === 'fund_outside_project_dates' ? status === 'active' && !state.dateResolved ? [fundDateIssue] : []
        : status === 'active' ? state.accepted || state.resolved ? [] : [issue] : state.accepted ? [acceptedIssue] : []
    return { count: results.length, next: null, previous: null, results }
  })
  api.acceptConsistencyIssue.mockImplementation(async () => { state.accepted = true; return acceptedIssue })
  api.reopenConsistencyIssue.mockImplementation(async () => { state.accepted = false; return { id: 19, status: 'reopened' } })
  projectApi.getProject.mockImplementation(async () => ({ id: 3, name: 'Atlas', status: true, start_date: '2025-01-01', end_date: '2025-12-31', capabilities: { can_change: state.canChange }, participants: { capabilities: { can_add: state.canAdd, can_change: false, can_delete: false }, items: [] } }))
  projectApi.createProjectParticipant.mockImplementation(async () => { state.resolved = true; return { data: { id: 91 } } })
  projectApi.updateProject.mockImplementation(async () => { state.dateResolved = true; return { data: { id: 3 } } })
  employeeApi.getEmployee.mockImplementation(async () => ({ id: 7, entry_date: '2025-01-01', exit_date: '2025-12-31', capabilities: { can_change: state.canChange } }))
  employeeApi.updateEmployee.mockImplementation(async () => { state.dateResolved = true; return { data: { id: 7 } } })
  fundingApi.getFundDetail.mockImplementation(async () => ({ fund: { id: 8, start_date: '2025-01-01', end_date: '2025-12-31', capabilities: { can_change: state.canChange } } }))
  fundingApi.updateFund.mockImplementation(async () => { state.dateResolved = true; return { data: { id: 8 } } })
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

  it('offers the existing Participant form when Project permits adding participants', async () => {
    const user = userEvent.setup()
    renderPage()
    expect(await screen.findByRole('button', { name: 'Add employee to project participants' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept exception' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Add employee to project participants' }))
    expect(await within(screen.getByRole('dialog')).findByRole('combobox', { name: 'Employee' })).toHaveValue('Alice')
  })

  it('hides the corrective action when Project cannot add participants', async () => {
    state.canAdd = false
    renderPage()
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    await waitFor(() => expect(projectApi.getProject).toHaveBeenCalledWith('3', expect.any(AbortSignal)))
    expect(screen.queryByRole('button', { name: 'Add employee to project participants' })).not.toBeInTheDocument()
  })

  it('creates the Participant and refreshes the issues and summary', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(await screen.findByRole('button', { name: 'Add employee to project participants' }))
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(projectApi.createProjectParticipant).toHaveBeenCalledWith('3', expect.objectContaining({ employee_id: 7 })))
    expect(await screen.findByText('No issues in this category.')).toBeInTheDocument()
    expect(api.getConsistencySummary).toHaveBeenCalledTimes(2)
    expect(api.acceptConsistencyIssue).not.toHaveBeenCalled()
  })

  it('offers Project date correction on Contract and Fund issues when Project is editable', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'contract_outside_project_dates')
    expect(await screen.findByRole('button', { name: 'Extend project dates to include this contract' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept exception' })).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'fund_outside_project_dates')
    expect(await screen.findByRole('button', { name: 'Extend project dates to include this fund' })).toBeInTheDocument()
  })

  it('hides Project date correction without Project change capability', async () => {
    state.canChange = false
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'fund_outside_project_dates')
    expect(await screen.findByText(fundDateIssue.label)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Extend project dates to include this fund' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept exception' })).toBeInTheDocument()
  })

  it('previews and extends only Project bounds then refreshes issues and summary', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'fund_outside_project_dates')
    await user.click(await screen.findByRole('button', { name: 'Extend project dates to include this fund' }))
    expect(screen.getByText(/1 Jan 2025 → 1 Dec 2024/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Extend project dates', hidden: true }))
    await waitFor(() => expect(projectApi.updateProject).toHaveBeenCalledWith(3, {
      start_date: '2024-12-01', end_date: '2026-01-01',
    }))
    expect(await screen.findByText('No issues in this category.')).toBeInTheDocument()
    expect(api.getConsistencySummary).toHaveBeenCalledTimes(2)
    expect(api.acceptConsistencyIssue).not.toHaveBeenCalled()
  })

  it('lists all six added rules and their contextual correction actions', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    const select = screen.getByRole('combobox', { name: 'Rule' })
    const expected = [
      ['contract_outside_employee_dates', 'Extend employee dates to include this contract'],
      ['milestone_outside_project_dates', 'Extend project dates to include this milestone'],
      ['task_outside_project_dates', 'Extend project dates to include this task'],
      ['contract_outside_fund_dates', 'Extend fund dates to include this contract'],
      ['expense_outside_fund_dates', 'Extend fund dates to include this expense'],
    ]
    for (const [key, label] of expected) {
      await user.selectOptions(select, key)
      expect(await screen.findByRole('button', { name: label })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Accept exception' })).toBeInTheDocument()
    }
    await user.selectOptions(select, 'project_without_leader')
    expect(await screen.findByRole('link', { name: 'Edit project participants' })).toHaveAttribute('href', '/projects/3#project-participants-heading')
    expect(screen.queryByRole('button', { name: /Extend/ })).not.toBeInTheDocument()
  })

  it('extends only Employee dates and refreshes the issue', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'contract_outside_employee_dates')
    await user.click(await screen.findByRole('button', { name: 'Extend employee dates to include this contract' }))
    expect(screen.getByText(/Employee entry date: 1 Jan 2025 → 1 Dec 2024/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Extend employee dates', hidden: true }))
    await waitFor(() => expect(employeeApi.updateEmployee).toHaveBeenCalledWith(7, { entry_date: '2024-12-01', exit_date: '2026-01-01' }))
    expect(await screen.findByText('No issues in this category.')).toBeInTheDocument()
  })

  it('keeps an already open Employee boundary open during correction', async () => {
    employeeApi.getEmployee.mockResolvedValue({ id: 7, entry_date: null, exit_date: '2025-12-31', capabilities: { can_change: true } })
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'contract_outside_employee_dates')
    await user.click(await screen.findByRole('button', { name: 'Extend employee dates to include this contract' }))
    await user.click(screen.getByRole('button', { name: 'Extend employee dates', hidden: true }))
    await waitFor(() => expect(employeeApi.updateEmployee).toHaveBeenCalledWith(7, {
      entry_date: null, exit_date: '2026-01-01',
    }))
  })

  it('extends only Fund dates and respects the Fund capability', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    const select = screen.getByRole('combobox', { name: 'Rule' })
    await user.selectOptions(select, 'expense_outside_fund_dates')
    await user.click(await screen.findByRole('button', { name: 'Extend fund dates to include this expense' }))
    await user.click(screen.getByRole('button', { name: 'Extend fund dates', hidden: true }))
    await waitFor(() => expect(fundingApi.updateFund).toHaveBeenCalledWith('3', 8, { start_date: '2024-12-01', end_date: '2026-01-01' }))
    expect(await screen.findByText('No issues in this category.')).toBeInTheDocument()
  })

  it('hides Employee and Fund mutations without parent change capability', async () => {
    state.canChange = false; state.canAdd = false
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    const select = screen.getByRole('combobox', { name: 'Rule' })
    await user.selectOptions(select, 'contract_outside_employee_dates')
    expect(await screen.findByText(employeeDateIssue.label)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Extend employee dates to include this contract' })).not.toBeInTheDocument()
    await user.selectOptions(select, 'contract_outside_fund_dates')
    expect(await within(screen.getByRole('table')).findByText(contractFundIssue.label)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Extend fund dates to include this contract' })).not.toBeInTheDocument()
    await user.selectOptions(select, 'project_without_leader')
    expect(await screen.findByRole('link', { name: 'Open project' })).toHaveAttribute('href', '/projects/3#project-participants-heading')
  })
})
