import { getLang } from './i18n'
import { reportNetwork } from './net'
import { writeCache } from './cache'
import { tr } from './i18n'
import { API } from './config'

/** fetch с отметкой связи: сетевой сбой — «нет интернета», любой ответ сервера — связь есть. */
const fetch = async (input: string, init?: RequestInit): Promise<Response> => {
  try { const r = await globalThis.fetch(input, init); reportNetwork(true); return r }
  catch (e) { reportNetwork(false); throw e }
}

export type FeedItem = {
  id: string
  title: string
  price: number | null
  previous_price?: number | null
  price_mark?: string | null
  is_free?: boolean
  currency?: string | null
  city?: string | null
  cover_photo?: string | null
  photos?: string[]
  cover_is_video?: boolean
  is_reserved?: boolean
  delivery_available?: boolean
  is_xl?: boolean
  is_highlighted?: boolean
  is_company?: boolean
  published_at?: string | null
  path?: string
}

export type Photo = { id: string; url: string; thumbnail_url?: string | null; is_video?: boolean }

export type Owner = {
  id: string
  display_name?: string | null
  avatar_url?: string | null
  rating_avg?: number | null
  rating_count?: number
  document_verified?: boolean
  is_company?: boolean
  company_name?: string | null
  since?: string | null
  listings_count?: number
  has_phone?: boolean
}

export type Listing = Omit<FeedItem, 'photos'> & {
  external_author?: string | null; reserved_for_me?: boolean; status?: string
  location_lat?: number | null; location_lng?: number | null; location_approximate?: boolean; hide_exact_address?: boolean
  photos: Photo[]
  owner?: Owner
  translations?: unknown
  source_language?: string
  views_count?: number
  favorites_count?: number
  number?: number | string | null
  price_negotiable?: boolean
  category_name?: string | null
  category_slug?: string | null
  attributes?: Record<string, unknown>
  external_source?: string | null
}

export type FeedTab = 'all' | 'new' | 'free'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export const PAGE = 20

/** Лента — те же параметры, что у главной сайта: «Новое» — сортировка по дате, «Даром» — только бесплатное. */
export type Filters = { priceMin?: string; priceMax?: string; currency?: 'EUR' | 'RSD'; withPhoto?: boolean; delivery?: boolean; sort?: '' | 'new' | 'cheap' | 'expensive' }

export function fetchFeed(opts: { tab: FeedTab; offset: number; q?: string; city?: string | null; category?: string | null; filters?: Filters; extra?: Record<string, string> }) {
  const p = new URLSearchParams({ lang: getLang(), limit: String(PAGE), offset: String(opts.offset) })
  if (opts.tab === 'new') p.set('sort', 'new')
  if (opts.tab === 'free') p.set('only_free', 'true')
  if (opts.q) { p.set('q', opts.q); p.set('sort', 'relevance') }
  if (opts.city) p.set('city', opts.city)
  if (opts.category) p.set('category_slug', opts.category)
  for (const [k, v] of Object.entries(opts.extra ?? {})) if (v) p.set(k, v)
  const f = opts.filters
  if (f) {
    if (f.priceMin) p.set('price_min', f.priceMin)
    if (f.priceMax) p.set('price_max', f.priceMax)
    if ((f.priceMin || f.priceMax) && f.currency) p.set('currency', f.currency)
    if (f.withPhoto) p.set('with_photo', 'true')
    if (f.delivery) p.set('delivery', 'true')
    if (f.sort) p.set('sort', f.sort)
  }
  return get<{ total: number; items: FeedItem[] }>(`/listings?${p.toString()}`)
}

export function fetchListing(id: string) {
  return get<Listing>(`/listings/${encodeURIComponent(id)}?lang=${getLang()}`)
}

/** Заголовок и описание лежат в переводах объявления: берём русский, иначе язык оригинала, иначе любой. */
export function textOf(listing: Listing): { title: string; description: string } {
  const tr = listing.translations as unknown
  const pick = (x: unknown) => (x && typeof x === 'object' ? (x as { title?: string; description?: string }) : null)
  let chosen: { title?: string; description?: string } | null = null
  if (Array.isArray(tr)) {
    const by = (lang?: string) => tr.find((t) => (t as { language?: string; lang?: string }).language === lang || (t as { lang?: string }).lang === lang)
    chosen = pick(by(getLang())) ?? pick(by(listing.source_language)) ?? pick(tr[0])
  } else if (tr && typeof tr === 'object') {
    const map = tr as Record<string, unknown>
    chosen = pick(map[getLang()]) ?? pick(map[listing.source_language ?? '']) ?? pick(Object.values(map)[0])
  }
  return { title: chosen?.title || listing.title || '', description: chosen?.description || '' }
}

// ---------- вход по коду из почты ----------

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

async function post<T>(path: string, body: unknown, token?: string | null): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = ''
    try { detail = (await res.json())?.detail ?? '' } catch { /* тело без JSON */ }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : '')
  }
  return res.json() as Promise<T>
}

/** «sent» — письмо ушло; «typo_suspected» — похоже на опечатку в адресе (suggestion — как, вероятно, правильно). */
export function requestCode(email: string) {
  return post<{ status: 'sent' | 'typo_suspected'; suggestion?: string }>('/auth/request-code', { destination: email, channel: 'email' })
}

export function verifyCode(email: string, code: string) {
  return post<{ token: string; user: import('./auth').User }>('/auth/verify-code', { destination: email, code, channel: 'email', lang: getLang() })
}

// ---------- избранное (нужен вход) ----------

async function authed<T>(path: string, token: string, method: 'GET' | 'POST' | 'DELETE' | 'PATCH' = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = ''
    try { const j = await res.json(); detail = typeof j?.detail === 'string' ? j.detail : '' } catch { /* тело без JSON */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const favoriteIds = (token: string) => authed<{ ids: string[] }>('/favorites/ids', token)
export const favoriteList = (token: string) => authed<{ total: number; items: FeedItem[] }>(`/favorites?lang=${getLang()}`, token)
export const addFavorite = (token: string, id: string) => authed<{ status: string }>(`/favorites/${encodeURIComponent(id)}`, token, 'POST')
export const removeFavorite = (token: string, id: string) => authed<{ status: string }>(`/favorites/${encodeURIComponent(id)}`, token, 'DELETE')

// ---------- разделы ----------

export type Category = { id: string; slug: string; name: Record<string, string> | string; count?: number; ready?: boolean; children?: Category[] }

export async function fetchCategories(): Promise<Category[]> {
  return get<Category[]>(`/categories?lang=${getLang()}`)
}

// ---------- сообщения ----------

export type Chat = {
  // как на сайте: звонок по разрешению, бронь, блокировка, состояние объявления
  buyer?: { id: string; display_name?: string | null } | null; seller?: { id: string; display_name?: string | null } | null
  call_request_pending?: boolean; phone_revealed?: boolean; other_phone?: string | null; seller_has_phone?: boolean
  listing_is_reserved?: boolean; listing_reserved_for_me?: boolean; blocked_by_them?: boolean; i_blocked_them?: boolean
  listing_sold?: boolean; listing_archived?: boolean; listing_status?: string | null; listing_price_negotiable?: boolean
  id: string; listing_id?: string | null; listing_title?: string | null; listing_photo?: string | null; listing_price?: number | null
  currency?: string | null; other_name?: string | null; last_text?: string | null; last_kind?: string | null; last_from_me?: boolean
  last_at?: string | null; unread?: number; is_seller?: boolean; is_team?: boolean
}

export type Message = {
  id: string; sender_id?: string | null; text?: string | null; kind: string; is_read?: boolean
  offer_price?: number | null; offer_status?: string | null; created_at: string
}

/** Предложение цены: сервер помечает его как price_offer (раньше — offer) */
export const isOffer = (kind?: string | null) => kind === 'price_offer' || kind === 'offer'

export const chatList = (token: string) => authed<{ total: number; items: Chat[] }>(`/chats?lang=${getLang()}`, token)
export const chatInfo = (token: string, id: string) => authed<Chat>(`/chats/${encodeURIComponent(id)}?lang=${getLang()}`, token)
export const chatMessages = (token: string, id: string) => authed<Message[]>(`/chats/${encodeURIComponent(id)}/messages`, token)
export const sendMessage = (token: string, id: string, text: string) =>
  authed<Message>(`/chats/${encodeURIComponent(id)}/messages`, token, 'POST', { text, offer_price: null })
export const markChatRead = (token: string, id: string) => authed<unknown>(`/chats/${encodeURIComponent(id)}/read`, token, 'POST')
export const startChat = (token: string, listingId: string) => authed<Chat>(`/chats/start?lang=${getLang()}`, token, 'POST', { listing_id: listingId })

// ---------- размещение, мои объявления, баланс ----------

export type Uploaded = { url: string; thumbnail_url?: string | null; is_video?: boolean }

/**
 * Загрузка видео — как на сайте (/media/upload-video): сервер проверяет формат, размер и длину (до полутора
 * минут) и делает превью. Ошибки — кодом (unsupported_format, file_too_large, video_too_long, processing_failed).
 */
export async function uploadVideo(token: string, uri: string, mime: string): Promise<Uploaded> {
  const form = new FormData()
  form.append('file', { uri, name: `video.${mime.includes('quicktime') ? 'mov' : 'mp4'}`, type: mime } as unknown as Blob)
  const res = await fetch(`${API}/media/upload-video`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form })
  if (!res.ok) {
    let detail = ''
    try { const j = await res.json(); detail = typeof j?.detail === 'string' ? j.detail : '' } catch { /* тело без JSON */ }
    throw new ApiError(res.status, detail)
  }
  const j = await res.json()
  return { url: j.video_url, thumbnail_url: j.video_thumbnail_url ?? null, is_video: true }
}

/** Загрузка одного фото (сервер сжимает до 1600 px и делает превью). */
export async function uploadPhoto(token: string, uri: string, mime = 'image/jpeg'): Promise<Uploaded> {
  const form = new FormData()
  const name = `photo.${mime.includes('png') ? 'png' : mime.includes('heic') ? 'heic' : 'jpg'}`
  if (typeof document !== 'undefined' && uri.startsWith('blob:')) {
    form.append('file', await (await fetch(uri)).blob(), name) // веб-превью
  } else {
    form.append('file', { uri, name, type: mime } as unknown as Blob)
  }
  const res = await fetch(`${API}/media/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form })
  if (!res.ok) throw new ApiError(res.status, '')
  return res.json() as Promise<Uploaded>
}

export type NewListing = {
  category_id: string; title: string; description: string; price: number | null; currency: 'EUR' | 'RSD'
  price_negotiable: boolean; city: string | null; photos: Uploaded[]; attributes?: Record<string, unknown>
  location_lat?: number | null; location_lng?: number | null; hide_exact_address?: boolean
}

export async function createListing(token: string, l: NewListing) {
  const res = await fetch(`${API}/listings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      category_id: l.category_id, source_language: getLang(), price: l.price, currency: l.currency, price_negotiable: l.price_negotiable,
      // характеристики раздела — как на сайте (раньше уходил пустой объект, и объявления из приложения не находились по фильтрам)
      location_lat: l.location_lat ?? null, location_lng: l.location_lng ?? null, hide_exact_address: !!l.hide_exact_address,
      city: l.city, attributes: l.attributes ?? {}, translations: [{ language: getLang(), title: l.title, description: l.description }],
      photos: l.photos.map((p) => ({ url: p.url, thumbnail_url: p.thumbnail_url ?? null, is_video: !!p.is_video })),
    }),
  })
  if (!res.ok) {
    let detail = ''
    try { const j = await res.json(); detail = typeof j.detail === 'string' ? j.detail : '' } catch { /* не JSON */ }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<{ id: string; status: string }>
}

export type MyListing = FeedItem & { status: string; views_count?: number; favorites_count?: number; expires_at?: string | null }
export const myListings = (token: string) => authed<{ total: number; counts: Record<string, number>; items: MyListing[] }>(`/listings/my/list?lang=${getLang()}`, token)
export const balance = (token: string) => authed<Record<string, unknown>>('/balance', token)

// ---------- объявление целиком, продавец, истории, свои объявления ----------

export const similarListings = (id: string) => get<{ items: FeedItem[] }>(`/listings/${encodeURIComponent(id)}/similar?lang=${getLang()}`)
export const sellerListings = (userId: string) => get<{ total: number; items: FeedItem[] }>(`/listings/by-seller/${encodeURIComponent(userId)}?lang=${getLang()}`)
export const freshListings = (city?: string | null) =>
  get<{ items: (FeedItem & { fresh?: boolean })[] }>(`/listings/fresh?lang=${getLang()}${city ? `&city=${encodeURIComponent(city)}` : ''}`)

export type Seller = {
  id: string; display_name?: string | null; company_name?: string | null; is_company?: boolean; avatar_url?: string | null
  rating_avg?: number | null; rating_count?: number; document_verified?: boolean; created_at?: string | null
  active_listings?: number; reply_speed?: string | null; company_description?: string | null; is_subscribed?: boolean
}
export const sellerProfile = (userId: string) => get<Seller>(`/users/${encodeURIComponent(userId)}/public?lang=${getLang()}`)

type Label = Record<string, string> | string
export type AttrField = { key: string; type?: string; label?: Label; unit?: string; required?: boolean; options?: { value: string | number; label: Label }[] }
export const categorySchema = (slug: string) => get<{ attribute_schema?: AttrField[] }>(`/categories/${encodeURIComponent(slug)}/schema`)
export const ru = (l?: Label | null) => (!l ? '' : typeof l === 'string' ? l : l[getLang()] || l.ru || l.en || Object.values(l)[0] || '')

/** Характеристики объявления с подписями из схемы раздела: «Комнат — 2», «Площадь, м² — 62». */
export function attrRows(attrs: Record<string, unknown> | undefined, schema: AttrField[]): { label: string; value: string }[] {
  if (!attrs) return []
  const out: { label: string; value: string }[] = []
  for (const f of schema) {
    const raw = attrs[f.key]
    if (raw === undefined || raw === null || raw === '' || (Array.isArray(raw) && raw.length === 0)) continue
    const one = (v: unknown) => {
      const opt = f.options?.find((o) => String(o.value) === String(v))
      if (opt) return ru(opt.label)
      if (typeof v === 'boolean') return v ? tr('да') : tr('нет')
      return String(v)
    }
    const value = Array.isArray(raw) ? raw.map(one).join(', ') : one(raw)
    if (value) out.push({ label: ru(f.label) || f.key, value })
  }
  return out
}

export const setListingStatus = (token: string, id: string, status: 'active' | 'sold' | 'archived') =>
  authed<unknown>(`/listings/${encodeURIComponent(id)}/status`, token, 'PATCH', { status })
export const deleteListing = (token: string, id: string) => authed<unknown>(`/listings/${encodeURIComponent(id)}`, token, 'DELETE')

export type ReportReason = 'fraud' | 'prohibited_item' | 'spam' | 'duplicate' | 'wrong_category' | 'offensive_user' | 'other'
export const sendReport = (token: string, listingId: string | null, reason: ReportReason, comment?: string, userId?: string | null) =>
  authed<unknown>('/reports', token, 'POST', { listing_id: listingId, target_user_id: userId ?? null, reason, comment: comment || null })

// ---------- уведомления, сохранённые поиски, редактирование ----------

export type Notice = { id: string; text: string; link?: string | null; is_read: boolean; created_at: string }
export const notifications = (token: string) => authed<{ total: number; unread: number; items: Notice[] }>('/notifications', token)
export const markNoticeRead = (token: string, id: string) => authed<unknown>(`/notifications/${encodeURIComponent(id)}/read`, token, 'POST')
export const markAllNoticesRead = (token: string) => authed<unknown>('/notifications/read-all', token, 'POST')

export type SearchFilters = { q?: string; category_slug?: string; city?: string; price_min?: string; price_max?: string; with_photo?: boolean }
export type SavedSearch = { id: string; name?: string | null; filters: SearchFilters; notify_enabled: boolean; new_count?: number }
export const savedSearches = (token: string) => authed<{ total: number; items: SavedSearch[] }>('/saved-searches', token)
export const saveSearch = (token: string, filters: SearchFilters, name?: string) => authed<SavedSearch>('/saved-searches', token, 'POST', { filters, name: name || null })
export const deleteSavedSearch = (token: string, id: string) => authed<unknown>(`/saved-searches/${encodeURIComponent(id)}`, token, 'DELETE')
export const toggleSavedSearch = (token: string, id: string, enabled: boolean) =>
  authed<unknown>(`/saved-searches/${encodeURIComponent(id)}`, token, 'PATCH', { notify_enabled: enabled })

export type ListingPatch = { title?: string; description?: string; price?: number | null; currency?: 'EUR' | 'RSD'; price_negotiable?: boolean; city?: string | null; location_lat?: number | null; location_lng?: number | null; hide_exact_address?: boolean }
export const updateListing = (token: string, id: string, patch: ListingPatch) => authed<unknown>(`/listings/${encodeURIComponent(id)}`, token, 'PATCH', patch)
export const addListingPhoto = (token: string, id: string, p: Uploaded) =>
  authed<unknown>(`/listings/${encodeURIComponent(id)}/photos`, token, 'POST', { url: p.url, thumbnail_url: p.thumbnail_url ?? null, is_video: !!p.is_video })
export const deleteListingPhoto = (token: string, id: string, photoId: string) =>
  authed<unknown>(`/listings/${encodeURIComponent(id)}/photos/${encodeURIComponent(photoId)}`, token, 'DELETE')

// ---------- профиль, история просмотров ----------

export const updateMe = (token: string, patch: { display_name?: string; phone?: string | null }) =>
  authed<import('./auth').User>('/auth/me', token, 'PATCH', patch)
export const listingsByIds = (ids: string[]) =>
  get<FeedItem[] | { items: FeedItem[] }>(`/listings/by-ids?ids=${ids.map(encodeURIComponent).join(',')}&lang=${getLang()}`)

// ---------- отзывы, подписка, поддержка, приглашения, чат ----------

export type Review = { id: string; author_name?: string | null; rating: number; comment?: string | null; created_at: string }
export const userReviews = (userId: string) =>
  get<{ total: number; rating_avg: number; rating_count: number; breakdown: Record<string, number>; items: Review[] }>(`/reviews/user/${encodeURIComponent(userId)}?lang=${getLang()}`)
export type Waiting = { chat_id: string; target_id: string; target_name?: string | null; listing_id?: string | null; listing_title?: string | null; listing_photo?: string | null }
export const waitingReviews = (token: string) => authed<{ items: Waiting[] }>(`/reviews/waiting?lang=${getLang()}`, token)
export const createReview = (token: string, r: { target_id: string; listing_id?: string | null; rating: number; comment?: string }) =>
  authed<unknown>('/reviews', token, 'POST', { ...r, comment: r.comment || null })
export const subscribeSeller = (token: string, userId: string, on: boolean) =>
  authed<unknown>(`/users/${encodeURIComponent(userId)}/subscribe`, token, on ? 'POST' : 'DELETE')

export type TicketMsg = { id: string; body: string; from_staff?: boolean; author_role?: string | null; is_staff?: boolean; created_at: string }
export type Ticket = { id: string; subject: string; topic: string; status: string; created_at: string; updated_at: string; messages?: TicketMsg[] }
export const supportMine = (token: string) => authed<{ items: Ticket[] }>('/support/mine', token)
// Одно обращение по номеру открывает только команда (/support/{id} — not_staff); пользователь видит свои
// обращения вместе с перепиской в /support/mine — оттуда и берём, как сайт
export async function supportTicket(token: string, id: string): Promise<Ticket | null> {
  const mine = await authed<{ items: Ticket[] }>('/support/mine', token)
  return mine.items.find((t) => t.id === id) ?? null
}
export const supportCreate = (token: string, t: { topic: string; subject: string; body: string }) => authed<{ id: string }>('/support', token, 'POST', t)
export const supportReply = (token: string, id: string, body: string) => authed<unknown>(`/support/${encodeURIComponent(id)}/reply`, token, 'POST', { body })

export const myReferrals = (token: string) =>
  authed<{ invited: number; posted: number; rewarded: number; earned: number; bonus: number }>('/users/me/referrals', token)

export const sendOffer = (token: string, chatId: string, price: number) =>
  authed<Message>(`/chats/${encodeURIComponent(chatId)}/messages`, token, 'POST', { text: null, offer_price: price })
export const respondOffer = (token: string, chatId: string, messageId: string, status: 'accepted' | 'declined') =>
  authed<unknown>(`/chats/${encodeURIComponent(chatId)}/offers/${encodeURIComponent(messageId)}/respond`, token, 'POST', { status })
export const blockChat = (token: string, chatId: string, on: boolean) =>
  authed<unknown>(`/chats/${encodeURIComponent(chatId)}/${on ? 'block' : 'unblock'}`, token, 'POST')

// ---------- аккаунт, заблокированные, волонтёрство ----------

export const deleteMe = (token: string) => authed<{ ok: boolean }>('/auth/me', token, 'DELETE')
export type BlockedUser = { id: string; display_name?: string | null; avatar_url?: string | null; blocked_at?: string | null }
export const blockedUsers = (token: string) => authed<{ items: BlockedUser[] }>('/users/blocked', token)
export const unblockUser = (token: string, userId: string) => authed<unknown>(`/users/blocked/${encodeURIComponent(userId)}/unblock`, token, 'POST')
export type VolunteerApp = { id: string; role: string; status: 'new' | 'accepted' | 'rejected'; created_at: string; note?: string | null }
export const volunteerMine = (token: string) => authed<{ application: VolunteerApp | null }>('/volunteer/mine', token)
export const volunteerApply = (token: string, a: { role: string; languages: string[]; hours_per_week: string; about: string; accept_confidentiality: boolean }) =>
  authed<{ application: VolunteerApp }>('/volunteer/apply', token, 'POST', a)

// ---------- подтверждение личности (сторонний сервис) ----------

export const startVerification = (token: string) => authed<{ url?: string; status?: string }>('/verification/start', token, 'POST')
export const verificationStatus = (token: string) =>
  authed<{ status: 'verified' | 'pending' | 'rejected' | 'none' | string; reason?: string | null }>('/verification/me', token)

// ---------- предзагрузка и кэш объявления ----------

const inflight = new Map<string, Promise<Listing>>()
/** Полная версия объявления — одна загрузка на касание и открытие, результат — в сохранённое. */
export function loadListing(id: string): Promise<Listing> {
  const running = inflight.get(id)
  if (running) return running
  const p = fetchListing(id).then((l) => { writeCache(`listing:${id}`, l); return l }).finally(() => { setTimeout(() => inflight.delete(id), 4000) })
  inflight.set(id, p)
  return p
}
export function prefetchListing(id: string) { loadListing(id).catch(() => {}) }

// ---------- показатели объявления ----------

export type ListingDashboard = {
  views_total?: number; views_week?: number; favorites_count?: number; chats_count?: number; status?: string; is_complete?: boolean
  published_at?: string | null; expires_at?: string | null; daily: { day: string; views: number }[]; tips?: { code: string; level?: string }[]
}
export const listingDashboard = (token: string, id: string, days: number) =>
  authed<ListingDashboard>(`/listings/${encodeURIComponent(id)}/dashboard?days=${days}`, token)

export const reorderListingPhotos = (token: string, id: string, photoIds: string[]) =>
  authed<unknown>(`/listings/${encodeURIComponent(id)}/photos/order`, token, 'PATCH', { photo_ids: photoIds })

// ---------- звонок по разрешению и бронь — как на сайте ----------
const chatPost = (token: string, id: string, what: string) => authed<unknown>(`/chats/${encodeURIComponent(id)}/${what}`, token, 'POST')
export const requestCall = (token: string, id: string) => chatPost(token, id, 'call-request')
export const allowCall = (token: string, id: string) => chatPost(token, id, 'call-allow')
export const declineCall = (token: string, id: string) => chatPost(token, id, 'call-decline')
export const revokeCall = (token: string, id: string) => chatPost(token, id, 'call-revoke')
export const reserveListing = (token: string, listingId: string, buyerId: string, hours = 48) =>
  authed<unknown>(`/listings/${encodeURIComponent(listingId)}/reserve`, token, 'POST', { buyer_id: buyerId, hours })
export const cancelReservation = (token: string, listingId: string) => authed<unknown>(`/listings/${encodeURIComponent(listingId)}/reserve/cancel`, token, 'POST')
/** Постоянное соединение переписки: новые сообщения сразу и «печатает…» — как на сайте. */
export const chatWsUrl = (token: string, id: string) => `${API.replace(/^http/, 'ws')}/chats/${encodeURIComponent(id)}/ws?token=${encodeURIComponent(token)}`

export const renewListing = (token: string, id: string) => authed<unknown>(`/listings/${encodeURIComponent(id)}/renew`, token, 'POST')
export const readAllNotifications = (token: string) => authed<unknown>('/notifications/read-all', token, 'POST')
export const clearAllNotifications = (token: string) => authed<unknown>('/notifications', token, 'DELETE')
