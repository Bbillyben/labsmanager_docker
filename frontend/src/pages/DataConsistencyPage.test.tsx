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
  acceptConsistencyIssue: vi.fn(), reopenConsistencyIssue: vi.fn(), acceptConsistencyBatch: vi.fn(), correctConsistencyIssue: vi.fn(), correctConsistencyBatch: vi.fn(),
}))
const projectApi = vi.hoisted(() => ({ getProject: vi.fn(), createProjectParticipant: vi.fn(), updateProject: vi.fn() }))
const employeeApi = vi.hoisted(() => ({ getEmployee: vi.fn(), updateEmployee: vi.fn() }))
const fundingApi = vi.hoisted(() => ({ getFundDetail: vi.fn(), updateFund: vi.fn() }))
vi.mock('../api/dataConsistency', async (importOriginal) => ({
  ...await importOriginal<typeof import('../api/dataConsistency')>(),
  ...api, DATA_CONSISTENCY_CHANGED: 'data-consistency:changed',
}))
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
      { rule_key: 'contract_employee_not_project_participant', category: 'contracts', count: 1, accepted_count: 0, correction_action: state.canAdd ? 'add_participants' : null },
      { rule_key: 'contract_outside_project_dates', category: 'contracts', count: 1, accepted_count: 0, correction_action: state.canChange ? 'extend_dates' : null },
      { rule_key: 'fund_outside_project_dates', category: 'funds', count: 1, accepted_count: 0, correction_action: state.canChange ? 'extend_dates' : null },
      ...Object.keys(extraIssues).map((rule_key) => ({ rule_key, category: 'other', count: 1, accepted_count: 0, correction_action: state.canChange && rule_key !== 'project_without_leader' ? 'extend_dates' : null })),
    ],
    capabilities: { can_accept: state.canAccept, can_reopen: state.canReopen },
  }))
  api.getConsistencyIssues.mockImplementation(async (status: string, _offset: number, _limit: number, _signal: AbortSignal, ruleKey: string) => {
    const results = extraIssues[ruleKey] ? status === 'active' && !state.dateResolved ? [extraIssues[ruleKey]] : []
      : ruleKey === 'contract_outside_project_dates' ? status === 'active' && !state.dateResolved ? [contractDateIssue] : []
      : ruleKey === 'fund_outside_project_dates' ? status === 'active' && !state.dateResolved ? [fundDateIssue] : []
        : status === 'active' ? state.accepted || state.resolved ? [] : [issue] : state.accepted ? [acceptedIssue] : []
    return { count: results.length, next: null, previous: null, results: results.map((item) => ({
      ...item,
      can_add_participant: state.canAdd,
      correction_action: state.canChange ? 'extend_dates' : null,
      parent_start_date: '2025-01-01', parent_end_date: '2025-12-31',
    })) }
  })
  api.acceptConsistencyIssue.mockImplementation(async () => { state.accepted = true; return acceptedIssue })
  api.reopenConsistencyIssue.mockImplementation(async () => { state.accepted = false; return { id: 19, status: 'reopened' } })
  api.acceptConsistencyBatch.mockResolvedValue({ initially_selected: 1, processed: 1, succeeded: 1, skipped: 0, failed: 0 })
  api.correctConsistencyIssue.mockImplementation(async () => { state.dateResolved = true; return { status: 'corrected' } })
  api.correctConsistencyBatch.mockImplementation(async () => { state.dateResolved = true; return { selected: 1, corrected: 1, already_resolved: 0, ignored: 0, failed: 0 } })
  projectApi.getProject.mockImplementation(async () => ({ id: 3, name: 'Atlas', status: true, start_date: '2025-01-01', end_date: '2025-12-31', capabilities: { can_change: state.canChange }, participants: { capabilities: { can_add: state.canAdd, can_change: false, can_delete: false }, items: [] } }))
  projectApi.createProjectParticipant.mockImplementation(async () => { state.resolved = true; return { data: { id: 91 } } })
  projectApi.updateProject.mockImplementation(async () => { state.dateResolved = true; return { data: { id: 3 } } })
  employeeApi.getEmployee.mockImplementation(async () => ({ id: 7, entry_date: '2025-01-01', exit_date: '2025-12-31', capabilities: { can_change: state.canChange } }))
  employeeApi.updateEmployee.mockImplementation(async () => { state.dateResolved = true; return { data: { id: 7 } } })
  fundingApi.getFundDetail.mockImplementation(async () => ({ fund: { id: 8, start_date: '2025-01-01', end_date: '2025-12-31', capabilities: { can_change: state.canChange } } }))
  fundingApi.updateFund.mockImplementation(async () => { state.dateResolved = true; return { data: { id: 8 } } })
})

const renderPage = (path = '/') => render(<MemoryRouter initialEntries={[path]}><I18nProvider><DataConsistencyPage /></I18nProvider></MemoryRouter>)

describe('Data Consistency frontend', () => {
  it('loads the overview and current results without fetching Project details', async () => {
    renderPage()
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Atlas' })).toHaveAttribute('href', '/projects/3')
    expect(projectApi.getProject).not.toHaveBeenCalled()
  })

  it('restores the selected check and result page from the URL', async () => {
    renderPage('/?rule=contract_outside_project_dates&offset=25')
    await waitFor(() => expect(api.getConsistencyIssues).toHaveBeenCalledWith('active', 25, 25, expect.any(AbortSignal), 'contract_outside_project_dates'))
    expect(screen.getByRole('combobox', { name: 'Rule' })).toHaveValue('contract_outside_project_dates')
  })

  it('shows every check including zero counts, filters issues, and uses backend labels for new checks', async () => {
    api.getConsistencySummary.mockResolvedValueOnce({
      total: 2, accepted_total: 0, categories: [],
      rules: [
        { rule_key: 'contract_employee_not_project_participant', category: 'contracts', count: 2, accepted_count: 0 },
        { rule_key: 'fund_outside_project_dates', category: 'funds', count: 0, accepted_count: 0 },
        { rule_key: 'future_check', category: 'projects', label: 'Future check', count: 0, accepted_count: 0 },
      ], capabilities: { can_accept: true, can_reopen: true },
    })
    const user = userEvent.setup()
    renderPage()
    const overview = await screen.findByRole('region', { name: 'Check overview' })
    expect(within(overview).getByText('Future check')).toBeInTheDocument()
    expect(within(overview).getByText('detected occurrences').closest('span')).toHaveTextContent('2 detected occurrences')
    expect(within(overview).getByText('available checks').closest('span')).toHaveTextContent('3 available checks')
    await user.click(screen.getByRole('button', { name: 'With issues' }))
    expect(within(overview).queryByText('Future check')).not.toBeInTheDocument()
    expect(within(overview).getByText('Contract employee not in project participants')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'All' }))
    await user.click(within(overview).getByRole('button', { name: 'View details: Future check' }))
    await waitFor(() => expect(api.getConsistencyIssues).toHaveBeenCalledWith('active', 0, 25, expect.any(AbortSignal), 'future_check'))
  })

  it('keeps visible and global selection distinct across pages, supports exclusions, and clears on rule change', async () => {
    const issues = Array.from({ length: 30 }, (_, index) => ({ ...issue, contract_id: 100 + index, label: `Issue ${index + 1}` }))
    api.getConsistencyIssues.mockImplementation(async (_status: string, offset: number, _limit: number, _signal: AbortSignal, ruleKey: string) =>
      ruleKey === issue.rule_key
        ? { count: 30, next: offset === 0 ? '/next/' : null, previous: offset ? '/previous/' : null, results: issues.slice(offset, offset + 25) }
        : { count: 0, next: null, previous: null, results: [] })
    api.acceptConsistencyBatch.mockResolvedValueOnce({ initially_selected: 29, processed: 29, succeeded: 28, skipped: 1, failed: 0 })
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Issue 1')
    await user.click(screen.getByRole('button', { name: 'Select' }))
    await user.click(screen.getByRole('button', { name: 'Select 25 shown' }))
    expect(screen.getByText('25 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next' }))
    await screen.findByRole('checkbox', { name: 'Select: Issue 26' })
    expect(screen.getByText('25 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Select all 30 results' }))
    expect(screen.getByText('30 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Select: Issue 26' }))
    expect(screen.getByText('29 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Accept 29 selected' }))
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Contract employee not in project participants')
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Accept 29 selected' }))
    await waitFor(() => expect(api.acceptConsistencyBatch).toHaveBeenCalledWith(issue.rule_key,
      { mode: 'all', excluded_ids: [125], selected_count: 29 }, ''))
    expect(await screen.findByText(/Initially selected: 29.*Skipped: 1/)).toBeInTheDocument()
  }, 20000)

  it('clears an explicit selection when switching checks and hides batch actions without permission', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.click(screen.getByRole('button', { name: 'Select' }))
    await user.click(screen.getByRole('checkbox', { name: `Select: ${issue.label}` }))
    expect(screen.getByText('1 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear selection' }))
    expect(screen.getByText('0 selected')).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: `Select: ${issue.label}` }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'contract_outside_project_dates')
    expect(screen.queryByText('1 selected')).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox', { name: `Select: ${issue.label}` })).not.toBeInTheDocument()
  })

  it('submits only individually selected issue identities after confirmation', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.click(screen.getByRole('button', { name: 'Select' }))
    await user.click(screen.getByRole('checkbox', { name: `Select: ${issue.label}` }))
    await user.click(screen.getByRole('button', { name: 'Accept 1 selected' }))
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Accept 1 selected' }))
    await waitFor(() => expect(api.acceptConsistencyBatch).toHaveBeenCalledWith(issue.rule_key,
      { mode: 'selected', issues: [{ id: 42, project_id: 3, employee_id: 7 }], selected_count: 1 }, ''))
  })

  it('offers participant creation in batch with contract dates and keeps Project leader manual', async () => {
    api.correctConsistencyBatch.mockImplementationOnce(async () => {
      state.resolved = true
      return { selected: 1, corrected: 1, already_resolved: 0, ignored: 0, failed: 0 }
    })
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.click(screen.getByRole('button', { name: 'Select' }))
    await user.click(screen.getByRole('checkbox', { name: `Select: ${issue.label}` }))
    expect(screen.getByRole('button', { name: 'Accept 1 selected' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Add employees to project participants (1)' }))
    expect(within(screen.getByRole('alertdialog')).getByText(/Each participation will use its contract dates/)).toBeInTheDocument()
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Add employees to project participants (1)' }))
    await waitFor(() => expect(api.correctConsistencyBatch).toHaveBeenCalledWith(issue.rule_key,
      { mode: 'selected', issues: [{ id: 42, project_id: 3, employee_id: 7 }], selected_count: 1 }))
    expect(await screen.findByText(/Corrected: 1/)).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'project_without_leader')
    expect(await screen.findByText(leaderIssue.label)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Add employees to project participants/ })).not.toBeInTheDocument()
  })
  it('shows lifecycle checks from the registry and runs a deterministic unit correction', async () => {
    const key = 'active_employee_past_exit_date'
    const lifecycleIssue = { rule_key: key, category: 'employees', employee_id: 7,
      project_id: null, project_name: '', employee_name: 'Alice Example', label: 'Alice Example',
      object_label: 'Alice Example', correction_action: 'apply_correction' }
    api.getConsistencySummary.mockImplementation(async () => ({
      total: 1, accepted_total: 0, categories: [{ key: 'employees', count: 1 }],
      rules: [{ rule_key: key, category: 'employees', count: 1, accepted_count: 0,
        correction_action: 'apply_correction' }], capabilities: { can_accept: true, can_reopen: true },
    }))
    api.getConsistencyIssues.mockImplementation(async () => ({ count: state.dateResolved ? 0 : 1,
      next: null, previous: null, results: state.dateResolved ? [] : [lifecycleIssue] }))
    const user = userEvent.setup()
    renderPage(`/?rule=${key}`)
    expect(await screen.findByRole('heading', { name: 'Active employee past the exit date' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Alice Example' })).toHaveAttribute('href', '/employees/7')
    await user.click(screen.getByRole('button', { name: 'Mark employee inactive' }))
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Mark employee inactive' }))
    await waitFor(() => expect(api.correctConsistencyIssue).toHaveBeenCalledWith(lifecycleIssue))
    expect(await screen.findByText('No issues in this category.')).toBeInTheDocument()
  }, 12000)

  it('offers lifecycle batch correction and keeps unknown dates manual', async () => {
    const teamKey = 'inactive_employee_active_team_mate'
    const manualKey = 'inactive_employee_without_exit_date'
    const teamIssue = { rule_key: teamKey, category: 'teams', teammate_id: 16, team_id: 4,
      employee_id: 7, employee_name: 'Alice Example', project_id: null, project_name: '', team_name: 'Core',
      label: 'Alice Example · Core', object_label: 'Core', correction_action: 'apply_correction' }
    const manualIssue = { rule_key: manualKey, category: 'employees', employee_id: 7,
      employee_name: 'Alice Example', project_id: null, project_name: '', label: 'Alice Example',
      object_label: 'Alice Example', manual_url: '/employees/7' }
    api.getConsistencySummary.mockImplementation(async () => ({ total: 2, accepted_total: 0,
      categories: [{ key: 'teams', count: 1 }, { key: 'employees', count: 1 }],
      rules: [
        { rule_key: teamKey, category: 'teams', count: 1, accepted_count: 0, correction_action: 'apply_correction' },
        { rule_key: manualKey, category: 'employees', count: 1, accepted_count: 0, correction_action: null },
      ], capabilities: { can_accept: true, can_reopen: true } }))
    api.getConsistencyIssues.mockImplementation(async (_status: string, _offset: number, _limit: number,
      _signal: AbortSignal, key: string) => ({ count: 1, next: null, previous: null,
      results: [key === manualKey ? manualIssue : teamIssue] }))
    const user = userEvent.setup()
    renderPage(`/?rule=${teamKey}`)
    expect(await screen.findByText(teamIssue.label)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Core' })).toHaveAttribute('href', '/teams/4')
    await user.click(screen.getByRole('button', { name: 'Select' }))
    await user.click(screen.getByRole('button', { name: 'Select all 1 results' }))
    await user.click(screen.getByRole('button', { name: 'Close team membership (1)' }))
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Close team membership (1)' }))
    await waitFor(() => expect(api.correctConsistencyBatch).toHaveBeenCalledWith(teamKey,
      { mode: 'all', excluded_ids: [], selected_count: 1 }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), manualKey)
    expect(await screen.findByRole('link', { name: 'Edit employee' })).toHaveAttribute('href', '/employees/7')
    expect(screen.queryByRole('button', { name: /Close team membership/ })).not.toBeInTheDocument()
  }, 15000)
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
    await waitFor(() => expect(api.acceptConsistencyIssue).toHaveBeenCalledWith(expect.objectContaining(issue), 'Intentional'))
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
    state.canAccept = false; state.canReopen = false; state.canAdd = false
    renderPage()
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Accept exception' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Select' })).not.toBeInTheDocument()
  })

  it('offers the existing Participant form when Project permits adding participants', async () => {
    const user = userEvent.setup()
    renderPage()
    expect(await screen.findByRole('button', { name: 'Add employee to project participants' })).toBeInTheDocument()
    expect(projectApi.getProject).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Accept exception' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Add employee to project participants' }))
    await waitFor(() => expect(projectApi.getProject).toHaveBeenCalledTimes(1))
    expect(await within(screen.getByRole('dialog')).findByRole('combobox', { name: 'Employee' })).toHaveValue('Alice')
  })

  it('hides the corrective action when Project cannot add participants', async () => {
    state.canAdd = false
    renderPage()
    expect(await screen.findByText(issue.label)).toBeInTheDocument()
    expect(projectApi.getProject).not.toHaveBeenCalled()
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
    expect(projectApi.getProject).not.toHaveBeenCalled()
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

  it('offers correction for a date check and keeps exception acceptance distinct', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'contract_outside_project_dates')
    await user.click(screen.getByRole('button', { name: 'Select' }))
    await user.click(screen.getByRole('button', { name: /Select all 1 results/ }))
    expect(screen.getByRole('button', { name: 'Accept 1 selected' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Correct 1 selected' }))
    expect(screen.getByText(/fewer objects than issues may be modified/)).toBeInTheDocument()
    await user.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Correct 1 selected' }))
    await waitFor(() => expect(api.correctConsistencyBatch).toHaveBeenCalledWith('contract_outside_project_dates', expect.objectContaining({ mode: 'all', excluded_ids: [], selected_count: 1 })))
    expect(api.acceptConsistencyBatch).not.toHaveBeenCalled()
    expect(await screen.findByText(/Already resolved: 0/)).toBeInTheDocument()
  })

  it('previews and extends only Project bounds then refreshes issues and summary', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Rule' }), 'fund_outside_project_dates')
    await user.click(await screen.findByRole('button', { name: 'Extend project dates to include this fund' }))
    expect(screen.getByText(/1 Jan 2025 → 1 Dec 2024/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Extend project dates', hidden: true }))
    await waitFor(() => expect(api.correctConsistencyIssue).toHaveBeenCalledWith(expect.objectContaining({ fund_id: 8, rule_key: 'fund_outside_project_dates' })))
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
    await waitFor(() => expect(api.correctConsistencyIssue).toHaveBeenCalledWith(expect.objectContaining({ employee_id: 7, rule_key: 'contract_outside_employee_dates' })))
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
    await waitFor(() => expect(api.correctConsistencyIssue).toHaveBeenCalledWith(expect.objectContaining({ employee_id: 7 })))
  })

  it('extends only Fund dates and respects the Fund capability', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(issue.label)
    const select = screen.getByRole('combobox', { name: 'Rule' })
    await user.selectOptions(select, 'expense_outside_fund_dates')
    await user.click(await screen.findByRole('button', { name: 'Extend fund dates to include this expense' }))
    await user.click(screen.getByRole('button', { name: 'Extend fund dates', hidden: true }))
    await waitFor(() => expect(api.correctConsistencyIssue).toHaveBeenCalledWith(expect.objectContaining({ fund_id: 8, rule_key: 'expense_outside_fund_dates' })))
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
