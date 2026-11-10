import { apiRequest } from './client';
import type { ProjectCollection, ProjectGenericInfo } from './projects';

export type EquipmentStatus = 'in_service' | 'out_of_service' | 'in_maintenance' | 'retired';
export type InventoryStatus = 'registered' | 'closed';
export type EquipmentCategory = {
  id: number;
  name: string;
  is_active: boolean;
  parent: number | null;
  level: number;
  path: string;
};

/** Match the parent marker used by the mutable-list tree renderer. */
export const equipmentCategoryLabel = (category: EquipmentCategory) =>
  `${'└─ '.repeat(category.level ?? 0)}${category.name}`;
export type EquipmentInfoType = { id: number; name: string; icon: string | null };
export type EquipmentCapabilities = {
  can_view: boolean;
  can_view_maintenance?: boolean;
  can_add: boolean;
  can_change: boolean;
  can_delete: boolean;
  can_export_word?: boolean;
  can_export_pdf?: boolean;
};
export type Equipment = {
  id: number;
  admin_url: string | null;
  name: string;
  internal_reference: string;
  category: EquipmentCategory;
  current_responsibles: Array<{ id: number | null; name: string | null }>;
  current_institutions: Array<{ id: number | null; name: string | null }>;
  status: EquipmentStatus;
  status_label: string;
  acquisition_date: string | null;
  commissioning_date: string | null;
  decommissioning_date: string | null;
  capabilities: EquipmentCapabilities;
};
export type EquipmentWrite = {
  name: string;
  internal_reference?: string;
  category_id: number;
  status: EquipmentStatus;
  acquisition_date: string | null;
  commissioning_date: string | null;
  decommissioning_date: string | null;
};
export type EquipmentList = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Equipment[];
  capabilities: EquipmentCapabilities;
};
export type EquipmentCatalogue<T> = {
  items: T[];
  capabilities: { can_add: boolean; can_change: boolean; can_delete: boolean };
};
export type EquipmentResponsibility = {
  id: number;
  employee: {
    id: number | null;
    name: string | null;
    is_active: boolean | null;
    can_view: boolean;
  };
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
};
export type EquipmentInventory = {
  id: number;
  institution: {
    id: number | null;
    short_name: string | null;
    name: string | null;
    can_view: boolean;
  };
  start_date: string | null;
  end_date: string | null;
  inventory_number: string;
  status: InventoryStatus;
  status_label: string;
  is_active: boolean;
};
export type EquipmentChildKind = 'generic-info' | 'responsibilities' | 'institutions';
export type EquipmentChild = ProjectGenericInfo | EquipmentResponsibility | EquipmentInventory;

const base = '/api/v1/equipment/';
const detail = (id: string | number) => `${base}${encodeURIComponent(id)}/`;
const child = (id: string | number, kind: EquipmentChildKind) => `${detail(id)}${kind}/`;
const body = (method: 'POST' | 'PATCH', data: object) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});

/** List only the server page and filters requested by the current URL. */
export const listEquipment = (query: string, signal: AbortSignal) =>
  apiRequest<EquipmentList>(`${base}?${query}`, { signal });
export const getEquipment = (id: string, signal: AbortSignal) =>
  apiRequest<Equipment>(detail(id), { signal });
export const getEquipmentCapabilities = (signal: AbortSignal) =>
  apiRequest<EquipmentCapabilities>(`${base}capabilities/`, { signal });
export const createEquipment = (data: EquipmentWrite) =>
  apiRequest<Equipment>(base, body('POST', data));
export const updateEquipment = (id: number, data: Partial<EquipmentWrite>) =>
  apiRequest<Equipment>(detail(id), body('PATCH', data));
export const deleteEquipment = (id: number) => apiRequest<void>(detail(id), { method: 'DELETE' });

export const listEquipmentCategories = (signal: AbortSignal) =>
  apiRequest<EquipmentCatalogue<EquipmentCategory>>(`${base}categories/`, { signal });
export const createEquipmentCategory = (
  data: Pick<EquipmentCategory, 'name' | 'is_active'> & { parent?: number | null },
) => apiRequest<EquipmentCategory>(`${base}categories/`, body('POST', data));
export const updateEquipmentCategory = (
  id: number,
  data: Partial<Pick<EquipmentCategory, 'name' | 'is_active' | 'parent'>>,
) => apiRequest<EquipmentCategory>(`${base}categories/${id}/`, body('PATCH', data));
export const deleteEquipmentCategory = (id: number) =>
  apiRequest<void>(`${base}categories/${id}/`, { method: 'DELETE' });

export const listEquipmentInfoTypes = (signal: AbortSignal) =>
  apiRequest<EquipmentCatalogue<EquipmentInfoType>>(`${base}generic-info-types/`, { signal });
export const createEquipmentInfoType = (data: Pick<EquipmentInfoType, 'name' | 'icon'>) =>
  apiRequest<EquipmentInfoType>(`${base}generic-info-types/`, body('POST', data));
export const updateEquipmentInfoType = (
  id: number,
  data: Partial<Pick<EquipmentInfoType, 'name' | 'icon'>>,
) => apiRequest<EquipmentInfoType>(`${base}generic-info-types/${id}/`, body('PATCH', data));
export const deleteEquipmentInfoType = (id: number) =>
  apiRequest<void>(`${base}generic-info-types/${id}/`, { method: 'DELETE' });

export const getEquipmentInfo = (id: string, signal: AbortSignal) =>
  apiRequest<ProjectCollection<ProjectGenericInfo>>(child(id, 'generic-info'), { signal });
export const getEquipmentResponsibilities = (id: string, signal: AbortSignal) =>
  apiRequest<ProjectCollection<EquipmentResponsibility>>(child(id, 'responsibilities'), { signal });
export const getEquipmentInventories = (id: string, signal: AbortSignal) =>
  apiRequest<ProjectCollection<EquipmentInventory>>(child(id, 'institutions'), { signal });
export const createEquipmentChild = <T extends EquipmentChild>(
  id: string,
  kind: EquipmentChildKind,
  data: object,
) => apiRequest<T>(child(id, kind), body('POST', data));
export const updateEquipmentChild = <T extends EquipmentChild>(
  id: string,
  kind: EquipmentChildKind,
  itemId: number,
  data: object,
) => apiRequest<T>(`${child(id, kind)}${itemId}/`, body('PATCH', data));
export const deleteEquipmentChild = (id: string, kind: EquipmentChildKind, itemId: number) =>
  apiRequest<void>(`${child(id, kind)}${itemId}/`, { method: 'DELETE' });

type ChoiceResult = {
  results: Array<{ id: number; name: string; short_name: string }>;
  has_more: boolean;
};
export const getEquipmentInstitutionOptions = (query: URLSearchParams, signal: AbortSignal) =>
  apiRequest<ChoiceResult>(`${base}institution-options/?${query}`, { signal });
