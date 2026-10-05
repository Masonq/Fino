/**
 * Отклики на вакансии, шопсы (видео с объявлениями) и витрина продавца — те же запросы, что у сайта
 * (backend: job_responses.py, shops.py, storefronts.py).
 */
import { API } from './config'
import { type FeedItem, ApiError } from './api'
import { getLang } from './i18n'

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

async function call<T>(path: string, token?: string | null, method: Method = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = ''
    try { const j = await res.json(); detail = typeof j?.detail === 'string' ? j.detail : '' } catch { /* без JSON */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}
const L = () => `lang=${getLang()}`

// ---------- отклики ----------
export type Brief = { id: string; title: string; path: string; photo?: string | null; price?: number | null; currency?: string | null; city?: string | null; status: string }
export type JobResp = {
  id: string; status: 'new' | 'viewed' | 'selected' | 'invited' | 'rejected'; created_at: string; interview_at?: string | null; interview_note?: string | null
  chat_id?: string | null; vacancy?: Brief | null; name?: string; phone?: string | null; about?: string | null; resume?: Brief | null; avatar?: string | null
}
export const jobRespond = (t: string, id: string, body: { name: string; phone?: string; about?: string; resume_listing_id?: string | null }) =>
  call<JobResp>(`/jobs/${id}/respond?${L()}`, t, 'POST', body)
export const jobMyResponse = (t: string, id: string) => call<{ response: JobResp | null }>(`/jobs/${id}/my-response?${L()}`, t)
export const jobMyResponses = (t: string) => call<{ items: JobResp[] }>(`/jobs/my-responses?${L()}`, t)
export const jobIncoming = (t: string) => call<{ items: { vacancy: Brief; counts: Record<string, number> }[] }>(`/jobs/incoming?${L()}`, t)
export const jobResponses = (t: string, id: string, folder: string) =>
  call<{ vacancy: Brief; counts: Record<string, number>; items: JobResp[] }>(`/jobs/${id}/responses?folder=${folder}&${L()}`, t)
export const jobSetStatus = (t: string, id: string, body: { status: string; interview_at?: string; note?: string }) =>
  call<JobResp>(`/jobs/responses/${id}/status?${L()}`, t, 'POST', body)

// ---------- шопсы ----------
export type ShopItem = Brief & { appear_at: number; item_id: string }
export type Shop = {
  id: string; status: string; reject_reason?: string | null; video_url?: string | null; video_low_url?: string | null; poster_url?: string | null
  duration?: number | null; caption?: string | null; is_ad: boolean; author?: { id: string; name: string; avatar?: string | null; verified?: boolean; official?: boolean } | null
  items: ShopItem[]; mine: boolean; stats?: { views: number; completes: number; taps: number; chats: number }
  kind?: 'shop' | 'listing'; likes?: number; comments?: number; liked?: boolean
}
export type ShopComment = { id: string; text: string; created_at: string; user?: { id: string; name: string; avatar?: string | null } | null; is_author: boolean; can_delete: boolean }
export const shopLike = (t: string, id: string, on: boolean) => call<{ liked: boolean; likes: number }>(`/shops/${id}/like?on=${on}`, t, 'POST')
export const shopComments = (t: string | null, id: string) => call<{ items: ShopComment[]; total: number }>(`/shops/${id}/comments`, t)
export const shopComment = (t: string, id: string, text: string) => call<ShopComment>(`/shops/${id}/comments`, t, 'POST', { text })
export const shopCommentDelete = (t: string, id: string, cid: string) => call(`/shops/${id}/comments/${cid}`, t, 'DELETE')
export const shopCommentReport = (t: string, id: string, cid: string) => call(`/shops/${id}/comments/${cid}/report`, t, 'POST')
export const shopsFeed = (params: { offset?: number; limit?: number; start?: string | null; withListings?: boolean }, t?: string | null) =>
  call<{ items: Shop[]; total: number }>(`/shops/feed?offset=${params.offset ?? 0}&limit=${params.limit ?? 8}${params.start ? `&start=${params.start}` : ''}${params.withListings ? '&with_listings=true' : ''}&${L()}`, t)
export const shopsMine = (t: string) => call<{ items: Shop[]; creator: { status: string | null } }>(`/shops/mine?${L()}`, t)
export const shopGet = (t: string | null, id: string) => call<Shop>(`/shops/${id}?${L()}`, t)
export const shopUpdate = (t: string, id: string, body: { caption: string; items: { listing_id: string; appear_at: number }[]; order_id?: string | null }) =>
  call<Shop>(`/shops/${id}?${L()}`, t, 'PUT', body)
export const shopSubmit = (t: string, id: string) => call<Shop>(`/shops/${id}/submit?${L()}`, t, 'POST')
export const shopRemove = (t: string, id: string) => call<{ ok: boolean }>(`/shops/${id}`, t, 'DELETE')
export const shopEvent = (t: string | null, id: string, type: string, listingId?: string) =>
  call(`/shops/${id}/event`, t, 'POST', { type, listing_id: listingId ?? null }).catch(() => null)
export const creatorApply = (t: string, body: { links: string; audience?: number | null; about?: string }) => call(`/shops/creator/apply`, t, 'POST', body)
export type Order = { id: string; status: string; fee?: number | null; currency: string; note?: string | null; listing?: Brief | null; creator?: { name: string } | null; mine: boolean }
export const shopOrders = (t: string, scope: string) => call<{ items: Order[]; creator: boolean }>(`/shops/orders/list?scope=${scope}&${L()}`, t)
export const shopOrderCreate = (t: string, body: { listing_id: string; fee?: number | null; currency: string; note?: string }) => call<Order>(`/shops/orders?${L()}`, t, 'POST', body)
export const shopOrderTake = (t: string, id: string) => call<Order & { chat_id: string }>(`/shops/orders/${id}/take?${L()}`, t, 'POST')
export const shopOrderCancel = (t: string, id: string) => call<Order>(`/shops/orders/${id}/cancel?${L()}`, t, 'POST')

/** Видео шопса — с ходом загрузки (XMLHttpRequest: у fetch нет прогресса отправки). */
export function shopUpload(t: string, uri: string, mime: string, onProgress: (p: number) => void): Promise<Shop> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API}/shops/upload`)
    xhr.setRequestHeader('Authorization', `Bearer ${t}`)
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total) }
    xhr.onload = () => {
      let data: { detail?: string } | null = null
      try { data = JSON.parse(xhr.responseText) } catch { /* не JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as unknown as Shop)
      else reject(new ApiError(xhr.status, data?.detail ?? ''))
    }
    xhr.onerror = () => reject(new ApiError(0, 'network'))
    const form = new FormData()
    form.append('file', { uri, name: `shop.${mime.includes('quicktime') ? 'mov' : 'mp4'}`, type: mime } as unknown as Blob)
    xhr.send(form)
  })
}

// ---------- витрина ----------
export type StorefrontPublic = {
  slug: string; moved: boolean; name: string; description?: string | null; cover_url?: string | null; status: string; pause_until?: string | null; pause_note?: string | null
  owner: { id: string; name: string; avatar?: string | null; verified?: boolean; official?: boolean }; mine: boolean; followers: number | null; following: boolean
  items: FeedItem[]; collections: { id: string; title: string; description?: string | null; listing_ids: string[]; drop_at?: string | null; count?: number }[]
  shops: { id: string; poster_url?: string | null; caption?: string | null }[]
}
export type StorefrontOwn = {
  id: string; slug: string; name: string; description?: string | null; cover_url?: string | null; status: string; pause_until?: string | null; pause_note?: string | null
  views: number; followers: number; items: FeedItem[]; not_added: FeedItem[]; cover_options: string[]
  collections: { id: string; title: string; description?: string | null; status: string; sort: string; listing_ids: string[] }[]
}
type Own = { storefront: StorefrontOwn | null; active_count?: number }
export const sfMe = (t: string) => call<Own>(`/storefronts/me?${L()}`, t)
export const sfAutobuild = (t: string) => call<Own>(`/storefronts/me/autobuild?${L()}`, t, 'POST', {})
export const sfEdit = (t: string, body: { name?: string; description?: string; slug?: string; cover_url?: string }) => call<Own>(`/storefronts/me?${L()}`, t, 'PATCH', body)
export const sfItems = (t: string, ids: string[]) => call<Own>(`/storefronts/me/items?${L()}`, t, 'PUT', { listing_ids: ids })
export const sfSaveCollection = (t: string, id: string | null, body: { title: string; description?: string; status: string; sort: string; listing_ids: string[] }) =>
  call<Own>(id ? `/storefronts/me/collections/${id}?${L()}` : `/storefronts/me/collections?${L()}`, t, id ? 'PUT' : 'POST', body)
export const sfDeleteCollection = (t: string, id: string) => call<Own>(`/storefronts/me/collections/${id}?${L()}`, t, 'DELETE')
export const sfState = (t: string, body: { action: string; until?: string | null; note?: string }) => call<Own>(`/storefronts/me/state?${L()}`, t, 'POST', body)
export const sfPublic = (slug: string, t?: string | null) => call<StorefrontPublic>(`/storefronts/${encodeURIComponent(slug)}?${L()}`, t)
export const sfByOwner = (ownerId: string) => call<{ storefront: { slug: string; name: string; cover_url?: string | null; count: number } | null }>(`/storefronts/by-owner/${ownerId}`)
export const sfDiscover = (city?: string | null) =>
  call<{ items: { slug: string; name: string; count: number; city?: string | null; previews: string[] }[] }>(`/storefronts/discover?limit=10${city ? `&city=${encodeURIComponent(city)}` : ''}`)
export const sfFollow = (t: string, slug: string, on: boolean) => call<{ following: boolean }>(`/storefronts/${encodeURIComponent(slug)}/follow`, t, on ? 'POST' : 'DELETE')
export const sfReport = (t: string, slug: string, reason: string) => call(`/storefronts/${encodeURIComponent(slug)}/report`, t, 'POST', { reason })

export const money = (price?: number | null, cur?: string | null) =>
  price == null ? '' : `${Math.round(price).toLocaleString('ru-RU')} ${cur === 'EUR' ? '€' : cur ?? ''}`
