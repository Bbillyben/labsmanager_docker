import { apiRequest } from './client'

export const DATA_CONSISTENCY_CHANGED = 'data-consistency:changed'

export type ConsistencySummary = {
  total: number
  accepted_total: number
  categories: { key: string; count: number }[]
  rules: { rule_key: string; category: string; count: number; accepted_count: number }[]
  capabilities: { can_accept: boolean; can_reopen: boolean }
}

export type ConsistencyIssue = {
  rule_key: string
  category: string
  contract_id?: number
  fund_id?: number
  milestone_id?: number
  expense_id?: number
  employee_id?: number
  project_id: number
  label: string
  employee_name?: string
  project_name: string
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
  apiRequest<ConsistencyIssue>(`${base}issues/${encodeURIComponent(issue.rule_key)}/${issue.expense_id ?? issue.milestone_id ?? issue.contract_id ?? issue.fund_id ?? issue.project_id}/accept/`, {
    method: 'POST', ...json({ ...(issue.employee_id && { employee_id: issue.employee_id }), project_id: issue.project_id, reason }),
  })

export const reopenConsistencyIssue = (exceptionId: number) =>
  apiRequest<{ id: number; status: 'reopened' }>(`${base}exceptions/${exceptionId}/reopen/`, { method: 'POST' })
