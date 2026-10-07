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
