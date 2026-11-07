import { apiRequest } from './client';
import type { CalendarEvent } from './employees';

export type MaintenanceType = 'preventive' | 'corrective' | 'inspection' | 'calibration' | 'other';
export type MaintenanceStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled';
export type MaintenanceCapabilities = {
  can_view: boolean;
  can_add: boolean;
  can_change: boolean;
  can_delete: boolean;
};
export type EquipmentMaintenance = {
  id: number;
  equipment: { id: number; name: string };
  title: string;
  maintenance_type: MaintenanceType;
  status: MaintenanceStatus;
  scheduled_date: string;
  scheduled_start_time: string | null;
  scheduled_end_time: string | null;
  performed_date: string | null;
  description: string;
  report: string;
  expense_link: { id: number; expense_id: number; label: string } | null;
  capabilities: MaintenanceCapabilities;
};
export type MaintenanceWrite = Omit<
  EquipmentMaintenance,
  'id' | 'equipment' | 'capabilities' | 'expense_link'
> & { expense_link_id?: number | null };
export type MaintenanceCollection = {
  count: number;
  next: string | null;
  previous: string | null;
  results: EquipmentMaintenance[];
  capabilities: MaintenanceCapabilities;
};
export type MaintenanceCalendar = {
  events: CalendarEvent[];
  capabilities: MaintenanceCapabilities;
};

const root = '/api/v1/equipment/';
const scoped = (equipmentId: number | string) =>
  `${root}${encodeURIComponent(equipmentId)}/maintenances/`;
const detail = (id: number) => `${root}maintenances/${id}/`;
const json = (method: 'POST' | 'PATCH', value: object) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(value),
});

export const listEquipmentMaintenances = (
  equipmentId: string,
  query: string,
  signal: AbortSignal,
) => apiRequest<MaintenanceCollection>(`${scoped(equipmentId)}?${query}`, { signal });
export const getEquipmentMaintenance = (id: number, signal: AbortSignal) =>
  apiRequest<EquipmentMaintenance>(detail(id), { signal });
export const createEquipmentMaintenance = (equipmentId: string, value: MaintenanceWrite) =>
  apiRequest<EquipmentMaintenance>(scoped(equipmentId), json('POST', value));
export const updateEquipmentMaintenance = (id: number, value: Partial<MaintenanceWrite>) =>
  apiRequest<EquipmentMaintenance>(detail(id), json('PATCH', value));
export const actOnEquipmentMaintenance = (
  id: number,
  action: 'complete' | 'cancel',
  value: { performed_date?: string; report?: string } = {},
) => apiRequest<EquipmentMaintenance>(`${detail(id)}${action}/`, json('POST', value));
export const deleteEquipmentMaintenance = (id: number) =>
  apiRequest<void>(detail(id), { method: 'DELETE' });
export const equipmentMaintenanceExpenseOptions = (id: string, signal: AbortSignal) =>
  apiRequest<Array<{ id: number; label: string }>>(`${scoped(id)}expense-options/`, { signal });
export const equipmentMaintenanceCalendar = (
  equipmentId: string | null,
  query: string,
  signal: AbortSignal,
) =>
  apiRequest<MaintenanceCalendar>(
    `${equipmentId ? scoped(equipmentId) : `${root}maintenances/`}calendar/?${query}`,
    { signal },
  );
