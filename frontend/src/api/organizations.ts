import { apiRequest } from './client'

export type OrganizationKind = 'institutions' | 'funders'
export type Capabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type Organization = { id: number; short_name: string; name: string; admin_url: string | null; capabilities: Capabilities }
export type OrganizationList = { count: number; next: string | null; previous: string | null; results: Organization[]; capabilities: { can_add: boolean } }
export type InfoType = { id: number; name: string; icon: string | null; type: 'none' | 'tel' | 'mail' | 'link' | 'addr' }
export type ContactType = { id: number; name: string }
export type OrganizationOptions = { organization_info_types: InfoType[]; contact_types: ContactType[]; contact_info_types: InfoType[]; map_provider: 'gmap' | 'opensm' }
export type OrganizationInfo = { id: number; info: InfoType; value: string | null; comment: string | null; admin_url: string | null; capabilities: Capabilities }
export type Contact = { id: number; first_name: string; last_name: string; type: ContactType; comment: string | null; admin_url: string | null; capabilities: Capabilities }
export type ContactInfo = OrganizationInfo
export type Collection<T> = { items: T[]; capabilities: { can_add: boolean } }
export type OrganizationSummary = { projects: { total: number; open: number; total_amount: string; available_amount: string; available_amount_focus: string }; contracts: { total: number; current: number; active: number; man_months: number } }
export type OrganizationProject = import('./projects').ProjectItem
export type OrganizationContract = import('./contracts').ContractHubItem
export type OrganizationWrite = { name: string; short_name: string }
export type InfoWrite = { info_id: number; value: string; comment: string }
export type ContactWrite = { type_id: number; first_name: string; last_name: string; comment: string }

const base = (kind: OrganizationKind) => `/api/v1/organizations/${kind}/`
const detail = (kind: OrganizationKind, id: number | string) => `${base(kind)}${encodeURIComponent(id)}/`
const write = (method: 'POST' | 'PATCH', data: object) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
export const listOrganizations = (kind: OrganizationKind, query: string, signal: AbortSignal) => apiRequest<OrganizationList>(`${base(kind)}?${query}`, { signal })
export const getOrganization = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<Organization>(detail(kind, id), { signal })
export const createOrganization = (kind: OrganizationKind, data: OrganizationWrite) => apiRequest<Organization>(base(kind), write('POST', data))
export const updateOrganization = (kind: OrganizationKind, id: number | string, data: OrganizationWrite) => apiRequest<Organization>(detail(kind, id), write('PATCH', data))
export const deleteOrganization = (kind: OrganizationKind, id: number | string) => apiRequest<void>(detail(kind, id), { method: 'DELETE' })
export const getOrganizationOptions = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<OrganizationOptions>(`${detail(kind, id)}options/`, { signal })
export const getOrganizationSummary = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<OrganizationSummary>(`${detail(kind, id)}summary/`, { signal })
export const getOrganizationProjects = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<OrganizationProject[]>(`${detail(kind, id)}projects/`, { signal })
export const getOrganizationContracts = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<OrganizationContract[]>(`${detail(kind, id)}contracts/`, { signal })
export const getOrganizationInfos = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<Collection<OrganizationInfo>>(`${detail(kind, id)}infos/`, { signal })
export const getContacts = (kind: OrganizationKind, id: string, signal: AbortSignal) => apiRequest<Collection<Contact>>(`${detail(kind, id)}contacts/`, { signal })
export const getContactInfos = (kind: OrganizationKind, id: string, contactId: number, signal: AbortSignal) => apiRequest<Collection<ContactInfo>>(`${detail(kind, id)}contacts/${contactId}/infos/`, { signal })
export const createOrganizationInfo = (kind: OrganizationKind, id: string, data: InfoWrite) => apiRequest<OrganizationInfo>(`${detail(kind, id)}infos/`, write('POST', data))
export const updateOrganizationInfo = (kind: OrganizationKind, id: string, itemId: number, data: InfoWrite) => apiRequest<OrganizationInfo>(`${detail(kind, id)}infos/${itemId}/`, write('PATCH', data))
export const deleteOrganizationInfo = (kind: OrganizationKind, id: string, itemId: number) => apiRequest<void>(`${detail(kind, id)}infos/${itemId}/`, { method: 'DELETE' })
export const createContact = (kind: OrganizationKind, id: string, data: ContactWrite) => apiRequest<Contact>(`${detail(kind, id)}contacts/`, write('POST', data))
export const updateContact = (kind: OrganizationKind, id: string, contactId: number, data: ContactWrite) => apiRequest<Contact>(`${detail(kind, id)}contacts/${contactId}/`, write('PATCH', data))
export const deleteContact = (kind: OrganizationKind, id: string, contactId: number) => apiRequest<void>(`${detail(kind, id)}contacts/${contactId}/`, { method: 'DELETE' })
export const createContactInfo = (kind: OrganizationKind, id: string, contactId: number, data: InfoWrite) => apiRequest<ContactInfo>(`${detail(kind, id)}contacts/${contactId}/infos/`, write('POST', data))
export const updateContactInfo = (kind: OrganizationKind, id: string, contactId: number, itemId: number, data: InfoWrite) => apiRequest<ContactInfo>(`${detail(kind, id)}contacts/${contactId}/infos/${itemId}/`, write('PATCH', data))
export const deleteContactInfo = (kind: OrganizationKind, id: string, contactId: number, itemId: number) => apiRequest<void>(`${detail(kind, id)}contacts/${contactId}/infos/${itemId}/`, { method: 'DELETE' })
