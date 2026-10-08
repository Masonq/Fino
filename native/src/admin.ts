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

export type AdminStats = { days: number; listings: { total: number; active: number; pending: number; own: number; imported: number; fresh: number; fresh_own: number }; people: { total: number; fresh: number; sellers: number; blocked: number } }
export type DayRow = { day: string; listings: number; own: number; visitors: number; signups: number; logins: number }
export const adminStats = (t: string, days: number) => authed<AdminStats>(`/admin/stats?days=${days}`, t)
export const adminDaily = (t: string, days: number) => authed<{ items: DayRow[] }>(`/admin/stats/daily?days=${days}`, t)
export type AuditItem = { id: string; actor: string; action: string; target_type: string; target_id: string; reason?: string | null; details?: Record<string, unknown> | null; created_at: string }
export const adminAudit = (t: string, kind: string) => authed<{ total: number; items: AuditItem[] }>(`/admin/audit?days=30&limit=100${kind ? `&action=${kind}` : ''}`, t)

// ---------- оставшиеся разделы «Панели команды» ----------
export type Alert = { kind: string; level: string; count: number; value?: string | null; listing_id?: string; user_id?: string }
export const adminAlerts = (t: string) => authed<{ items: Alert[] }>('/admin/users/alerts', t)
export type FlaggedChat = { id: string; reason?: string | null; seller_id?: string; listing?: { title?: string } | null; messages?: { from?: string; text?: string }[] }
export const flaggedChats = (t: string) => authed<{ items: FlaggedChat[] }>('/moderation/flagged-chats', t)
export const clearChatFlag = (t: string, id: string) => authed<unknown>(`/moderation/flagged-chats/${id}/clear`, t, 'POST')
export type JobRun = { name: string; at?: string | null; done: number; error?: boolean; reason?: string | null }
export const adminJobs = (t: string) => authed<{ days: number; jobs: JobRun[] }>('/admin/audit/jobs?days=7', t)
export type VolApp = { id: string; user?: { display_name?: string; email?: string } | null; role?: string; languages?: string[] | string; hours_per_week?: number; about?: string; status?: string; created_at?: string }
export const volunteerQueue = (t: string, status: string) => authed<{ items: VolApp[]; counts: Record<string, number> }>(`/volunteer/queue?status=${status}`, t)
export const volunteerDecide = (t: string, id: string, accept: boolean) => authed<unknown>(`/volunteer/${id}/decide`, t, 'POST', { accept, note: '' })
export type ShopQ = { id: string; caption?: string | null; poster_url?: string | null; author?: { name?: string } | null; name?: string; display_name?: string }
export const shopQueue = (t: string) => authed<{ shops: ShopQ[]; creators: ShopQ[] }>('/shops/admin/queue', t)
export const shopDecide = (t: string, id: string, approve: boolean) => authed<unknown>(`/shops/admin/shops/${id}`, t, 'POST', { approve })
export const creatorDecide = (t: string, id: string, approve: boolean) => authed<unknown>(`/shops/admin/creators/${id}`, t, 'POST', { approve })
export type TeamChat = { id: string; person?: { name?: string } | null; last_text?: string | null; last_at?: string | null; last_from_team?: boolean; unread?: number }
export const teamChats = (t: string) => authed<{ items: TeamChat[]; unread: number }>('/team/chats', t)
export const teamChat = (t: string, id: string) => authed<{ messages: { id?: string; text: string; from_team?: boolean }[]; person?: { name?: string } }>(`/team/chats/${id}`, t)
export const teamReply = (t: string, id: string, text: string) => authed<unknown>(`/team/chats/${id}/reply`, t, 'POST', { text })
export const adminSettings = (t: string) => authed<{ card_payments_enabled: boolean; updated_at?: string | null }>('/admin/settings', t)
export const setCardPayments = (t: string, enabled: boolean) => authed<{ card_payments_enabled: boolean }>('/admin/settings/card-payments', t, 'POST', { enabled })

// причины отказа — общие для очереди модерации и экрана объявления
export const MOD_REASONS = ['Непонятный заголовок', 'Плохие или чужие фото', 'Запрещённый товар', 'Дубль объявления', 'Не тот раздел']
export const modReturn = (t: string, id: string) => authed<unknown>(`/moderation/${id}/return`, t, 'POST')
