import { apiRequest } from './client'

export type RecentUrlId = 'project' | 'employee' | 'fund' | 'budget' | 'contract' | 'institution' | 'funder' | 'team' | 'calendar' | 'fund-explorer' | 'budget-explorer' | 'expenses'
export type RecentItem = { url_id: RecentUrlId; obj_id: number | null; type: string; title: string; subtitle: string; icon: string; url: string; last_viewed_at: string }

export const listRecentItems = (signal?: AbortSignal) => apiRequest<RecentItem[]>('/api/v1/recent-items/', { signal })
export const trackRecentItem = (url_id: RecentUrlId, obj_id?: number) => apiRequest<RecentItem>('/api/v1/recent-items/', {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url_id, ...(obj_id === undefined ? {} : { obj_id }) }),
})
