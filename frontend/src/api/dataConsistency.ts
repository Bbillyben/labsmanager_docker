import { apiRequest } from './client'

export const DATA_CONSISTENCY_CHANGED = 'data-consistency:changed'

export type ConsistencySummary = {
  total: number
  accepted_total: number
  categories: { key: string; count: number }[]
  rules: { rule_key: string; category: string; label?: string; count: number; accepted_count: number; correction_action?: 'extend_dates' | 'add_participants' | 'apply_correction' | null }[]
  capabilities: { can_accept: boolean; can_reopen: boolean }
}

export type ConsistencyIssue = {
  rule_key: string
  category: string
  contract_id?: number
  fund_id?: number
  milestone_id?: number
  expense_id?: number
  teammate_id?: number
  participant_id?: number
  team_id?: number
  employee_id?: number
  project_id: number | null
  label: string
  employee_name?: string
  project_name: string
  team_name?: string
  object_label?: string
  manual_url?: string
  correction_action?: 'apply_correction' | 'extend_dates' | null
  can_add_participant?: boolean
  employee_start_date?: string | null
  employee_end_date?: string | null
  reason?: 'starts_before_project' | 'ends_after_project' | 'both'
  parent_kind?: 'project' | 'fund' | 'employee'
  parent_start_date?: string | null
  parent_end_date?: string | null
  project_start_date?: string | null
  project_end_date?: string | null
  child_start_date?: string | null
  child_end_date?: string | null
  exception?: { id: number; accepted_by: string | null; accepted_at: string; reason: string }
}

export type ConsistencyIssues = {
  count: number
  next: string | null
  previous: string | null
  results: ConsistencyIssue[]
}

const base = '/api/v1/data-consistency/'
const json = (value: unknown) => ({ headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })

export const getConsistencySummary = (signal?: AbortSignal) =>
  apiRequest<ConsistencySummary>(`${base}summary/`, { signal })

export const getConsistencyIssues = (status: 'active' | 'accepted', offset = 0, limit = 25, signal?: AbortSignal, ruleKey?: string) =>
  apiRequest<ConsistencyIssues>(`${base}issues/?${new URLSearchParams({ status, offset: String(offset), limit: String(limit), ...(ruleKey && { rule_key: ruleKey }) })}`, { signal })

export const acceptConsistencyIssue = (issue: ConsistencyIssue, reason: string) =>
  apiRequest<ConsistencyIssue>(`${base}issues/${encodeURIComponent(issue.rule_key)}/${consistencyIssueId(issue)}/accept/`, {
    method: 'POST', ...json({ ...(issue.employee_id && { employee_id: issue.employee_id }), project_id: issue.project_id, ...(issue.team_id && { team_id: issue.team_id }), reason }),
  })

export const reopenConsistencyIssue = (exceptionId: number) =>
  apiRequest<{ id: number; status: 'reopened' }>(`${base}exceptions/${exceptionId}/reopen/`, { method: 'POST' })

export type ConsistencyBatchSelection =
  | { mode: 'selected'; issues: { id: number; project_id: number | null; employee_id?: number; fund_id?: number; team_id?: number }[]; selected_count: number }
  | { mode: 'all'; excluded_ids: number[]; selected_count: number }

export type ConsistencyBatchResult = {
  initially_selected: number
  processed: number
  succeeded: number
  skipped: number
  failed: number
}

export type ConsistencyCorrectionResult = {
  selected: number
  corrected: number
  already_resolved: number
  ignored: number
  failed: number
}

export const correctConsistencyIssue = (issue: ConsistencyIssue) =>
  apiRequest<{ status: 'corrected' }>(`${base}issues/${encodeURIComponent(issue.rule_key)}/${consistencyIssueId(issue)}/correct/`, {
    method: 'POST', ...json({ project_id: issue.project_id, ...(issue.employee_id && { employee_id: issue.employee_id }), ...(issue.fund_id && { fund_id: issue.fund_id }), ...(issue.team_id && { team_id: issue.team_id }) }),
  })

export const consistencyIssueId = (issue: ConsistencyIssue) =>
  issue.teammate_id ?? issue.participant_id ?? issue.expense_id ?? issue.milestone_id ?? issue.contract_id ?? issue.fund_id ?? issue.project_id ?? issue.employee_id!

export const correctConsistencyBatch = (ruleKey: string, selection: ConsistencyBatchSelection) =>
  apiRequest<ConsistencyCorrectionResult>(`${base}issues/${encodeURIComponent(ruleKey)}/correct-batch/`, {
    method: 'POST', ...json(selection),
  })

export const acceptConsistencyBatch = (ruleKey: string, selection: ConsistencyBatchSelection, reason: string) =>
  apiRequest<ConsistencyBatchResult>(`${base}issues/${encodeURIComponent(ruleKey)}/accept-batch/`, {
    method: 'POST', ...json({ ...selection, reason }),
  })
