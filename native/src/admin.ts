/** Запросы «Панели команды» — те же, что у админки сайта. */
import { authed } from './api'
import { getLang } from './i18n'

export type Counters = { moderation?: number; support?: number; team_chats?: number; flagged_chats?: number; volunteers?: number }
export type ModItem = { id: string; title?: string | null; description?: string | null; price?: number | null; currency?: string | null; city?: string | null
  photos: string[]; owner_name?: string | null; owner_days?: number; owner_active?: number; owner_rejected?: number; owner_verified?: boolean
  looks_duplicate?: boolean; category_name?: string | null; created_at?: string | null }
export type Ticket = { id: string; subject: string; topic: string; status: string; contact?: string | null; listing_id?: string | null; updated_at?: string | null
  messages?: { id: string; body: string; from_staff: boolean; author?: string | null; created_at?: string | null }[] }

export const counters = (t: string) => authed<Counters>('/moderation/counters', t)
export const stats = (t: string, days: number) => authed<{ listings: { active: number; pending: number } }>(`/admin/stats?days=${days}`, t)
export const daily = (t: string, days: number) => authed<{ items: { day: string; visitors?: number; own?: number; signups?: number }[] }>(`/admin/stats/daily?days=${days}`, t)
export const modQueue = (t: string) => authed<{ total: number; items: ModItem[] }>(`/moderation/queue?lang=${getLang()}`, t)
export const modApprove = (t: string, id: string) => authed<unknown>(`/moderation/${id}/approve`, t, 'POST')
export const modReject = (t: string, id: string, reason: string) => authed<unknown>(`/moderation/${id}/reject`, t, 'POST', { reason })
export const supportQueue = async (t: string, status: string) => {
  const r = await authed<{ items: Ticket[] } | Ticket[]>(`/support/queue?status=${status}&limit=100`, t)
  return Array.isArray(r) ? r : r.items
}
export const supportTicket = (t: string, id: string) => authed<Ticket>(`/support/${id}`, t)
export const supportAnswer = (t: string, id: string, body: string) => authed<unknown>(`/support/${id}/answer`, t, 'POST', { body })
export const supportClose = (t: string, id: string) => authed<unknown>(`/support/${id}/close`, t, 'POST')
export const modMove = (t: string, id: string, categoryId: string) => authed<unknown>(`/moderation/${id}/move`, t, 'POST', { category_id: categoryId })
export const deleteListingStaff = (t: string, id: string, force?: boolean) => authed<unknown>(`/listings/${id}${force ? '?force=true' : ''}`, t, 'DELETE')

export type AdminUser = { id: string; display_name?: string | null; avatar_url?: string | null; email?: string | null; phone?: string | null; role: string
  is_blocked?: boolean; block_reason?: string | null; document_verified?: boolean; company_name?: string | null; rating_count?: number
  listings?: number; listings_active?: number; created_at?: string | null; last_seen_at?: string | null }
export const adminUsers = (t: string, q: string) => authed<{ items: AdminUser[]; total?: number }>(`/admin/users?sort=new&limit=100${q ? `&q=${encodeURIComponent(q)}` : ''}`, t)
export const adminUser = (t: string, id: string) => authed<AdminUser>(`/admin/users/${id}`, t)
export const adminSetRole = (t: string, id: string, role: string) => authed<unknown>(`/admin/users/${id}/role`, t, 'POST', { role })
export const adminVerify = (t: string, id: string, verified: boolean) => authed<{ document_verified: boolean }>(`/admin/users/${id}/verify`, t, 'POST', { verified })
export const adminBlock = (t: string, id: string, reason: string) => authed<unknown>(`/admin/users/${id}/block`, t, 'POST', { reason })
export const adminUnblock = (t: string, id: string) => authed<unknown>(`/admin/users/${id}/unblock`, t, 'POST')
