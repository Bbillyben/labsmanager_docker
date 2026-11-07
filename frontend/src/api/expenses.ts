import { apiRequest } from './client';
import type { CostType } from './funding';

/** Expense actions the backend authorizes in the current context. */
export type ExpenseCapabilities = { can_change: boolean; can_delete: boolean };
export type Expense = {
  admin_url?: string | null;
  id: number;
  expense_id: string;
  desc: string;
  date: string;
  type: CostType;
  amount: string;
  status: 'e' | 'r' | 'p';
  contract: { id: number; name: string } | null;
  budget: { id: number; name: string } | null;
  capabilities: ExpenseCapabilities;
  nature?: EquipmentExpenseNature;
  fund?: { id: number; name: string };
  link_capabilities?: { can_change: boolean; can_unlink: boolean };
  can_view_business_assignments?: boolean;
};
export type EquipmentExpenseNature = 'purchase' | 'maintenance' | 'repair' | 'other';
/** Paginated Expense rows and creation capabilities. */
export type ExpenseCollection = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Expense[];
  total_visible?: string;
  capabilities: {
    expense_mode: 's' | 'e' | 'h';
    can_add: boolean;
    can_sync_expenses: boolean;
    can_link?: boolean;
  };
};
export type ExpenseOptions = {
  cost_types: CostType[];
  hr_type_ids: number[];
  contracts: Array<{ id: number; name: string; fund_id?: number }>;
  budgets: Array<{ id: number; name: string; fund_id?: number }>;
  funds?: Array<{ id: number; name: string; expense_mode: 's' | 'e' | 'h' }>;
};
export type ExpenseWrite = {
  expense_id: string;
  desc: string;
  date: string;
  type_id: number | undefined;
  amount: string;
  status: Expense['status'];
  contract_id: number | null;
  budget_id: number | null;
  fund_id?: number;
  nature?: EquipmentExpenseNature;
};
/** Fund or Contract context used to scope Expense requests. */
export type ExpenseScope =
  | {
      equipmentId: number;
      fundId?: never;
      employeeId?: never;
      contractId?: never;
      projectId?: never;
      budgetId?: never;
      hubContractId?: never;
    }
  | { fundId: number; employeeId?: never; contractId?: never; projectId?: never; budgetId?: never }
  | { employeeId: number; contractId: number; fundId?: never; projectId?: never; budgetId?: never }
  | { projectId: string; contractId: number; fundId?: never; employeeId?: never; budgetId?: never }
  | { projectId: string; budgetId: number; fundId?: never; employeeId?: never; contractId?: never }
  | {
      hubContractId: number;
      fundId?: never;
      employeeId?: never;
      projectId?: never;
      budgetId?: never;
      contractId?: never;
    };
export type ExpenseFilters = {
  search: string;
  type: string;
  date_from: string;
  date_to: string;
  page: number;
};

const base = (scope: ExpenseScope) =>
  'equipmentId' in scope
    ? `/api/v1/equipment/${scope.equipmentId}/expenses/`
    : 'hubContractId' in scope
      ? `/api/v1/contracts/${scope.hubContractId}/expenses/`
      : 'budgetId' in scope
        ? `/api/v1/projects/${scope.projectId}/budgets/${scope.budgetId}/expenses/`
        : 'fundId' in scope
          ? `/api/v1/funds/${scope.fundId}/expenses/`
          : 'projectId' in scope
            ? `/api/v1/projects/${scope.projectId}/contracts/${scope.contractId}/expenses/`
            : `/api/v1/employees/${scope.employeeId}/contracts/${scope.contractId}/expenses/`;

const write = (method: 'POST' | 'PATCH', body: Partial<ExpenseWrite>) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
/** Fetch visible Expenses using the selected scope and filters. */
export function getExpenses(scope: ExpenseScope, filters: ExpenseFilters, signal: AbortSignal) {
  const query = new URLSearchParams();
  for (const key of ['search', 'type', 'date_from', 'date_to'] as const)
    if (filters[key]) query.set(key, filters[key]);
  query.set('page', String(filters.page));
  return apiRequest<ExpenseCollection>(`${base(scope)}?${query}`, { signal });
}
export const getExpenseOptions = (scope: ExpenseScope, signal: AbortSignal) =>
  apiRequest<ExpenseOptions>(`${base(scope)}options/`, { signal });
export const createExpense = (scope: ExpenseScope, body: ExpenseWrite) =>
  apiRequest<Expense>(base(scope), write('POST', body));
export const updateExpense = (scope: ExpenseScope, id: number, body: ExpenseWrite) =>
  apiRequest<Expense>(`${base(scope)}${id}/`, write('PATCH', body));
export const deleteExpense = (scope: ExpenseScope, id: number) =>
  apiRequest<void>(`${base(scope)}${id}/`, { method: 'DELETE' });
export const syncExpenses = (fundId: number) =>
  apiRequest<{ detail: string }>(`/api/v1/funds/${fundId}/expenses/sync/`, { method: 'POST' });

export const getEquipmentExpenseCandidates = (
  equipmentId: number,
  search: string,
  signal: AbortSignal,
) =>
  apiRequest<{ results: Expense[] }>(
    `/api/v1/equipment/${equipmentId}/expenses/candidates/?search=${encodeURIComponent(search)}`,
    { signal },
  );
export const linkEquipmentExpense = (
  equipmentId: number,
  expenseId: number,
  nature: EquipmentExpenseNature,
) =>
  apiRequest<Expense>(`/api/v1/equipment/${equipmentId}/expenses/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ existing_expense_id: expenseId, nature }),
  });
export const changeEquipmentExpenseNature = (
  equipmentId: number,
  expenseId: number,
  nature: EquipmentExpenseNature,
) =>
  apiRequest<Expense>(`/api/v1/equipment/${equipmentId}/expenses/${expenseId}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nature }),
  });
export const deleteEquipmentExpense = (equipmentId: number, expenseId: number) =>
  apiRequest<void>(`/api/v1/equipment/${equipmentId}/expenses/${expenseId}/delete-expense/`, {
    method: 'DELETE',
  });

export type ExpenseBusinessAssignments = {
  equipment: {
    equipment: { id: number; name: string; internal_reference: string };
    nature: EquipmentExpenseNature;
  } | null;
  capabilities: { can_link: boolean; can_change: boolean; can_unlink: boolean };
};
const assignmentsUrl = (expenseId: number) => `/api/v1/expenses/${expenseId}/business-assignments/`;
export const getExpenseBusinessAssignments = (expenseId: number, signal: AbortSignal) =>
  apiRequest<ExpenseBusinessAssignments>(assignmentsUrl(expenseId), { signal });
export const createExpenseEquipmentAssignment = (
  expenseId: number,
  equipmentId: number,
  nature: EquipmentExpenseNature,
) =>
  apiRequest(assignmentsUrl(expenseId), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ equipment_id: equipmentId, nature }),
  });
export const updateExpenseEquipmentAssignment = (
  expenseId: number,
  body: { equipment_id?: number; nature?: EquipmentExpenseNature },
) =>
  apiRequest(assignmentsUrl(expenseId), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
export const deleteExpenseEquipmentAssignment = (expenseId: number) =>
  apiRequest<void>(assignmentsUrl(expenseId), { method: 'DELETE' });
