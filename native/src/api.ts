import { API } from './config'

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
}

export type Listing = Omit<FeedItem, 'photos'> & {
  photos: Photo[]
  owner?: Owner
  translations?: unknown
  source_language?: string
  views_count?: number
  favorites_count?: number
  number?: number | string | null
  price_negotiable?: boolean
  category_name?: string | null
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

export function fetchFeed(opts: { tab: FeedTab; offset: number; q?: string; city?: string | null; category?: string | null; filters?: Filters }) {
  const p = new URLSearchParams({ lang: 'ru', limit: String(PAGE), offset: String(opts.offset) })
  if (opts.tab === 'new') p.set('sort', 'new')
  if (opts.tab === 'free') p.set('only_free', 'true')
  if (opts.q) { p.set('q', opts.q); p.set('sort', 'relevance') }
  if (opts.city) p.set('city', opts.city)
  if (opts.category) p.set('category_slug', opts.category)
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
  return get<Listing>(`/listings/${encodeURIComponent(id)}?lang=ru`)
}

/** Заголовок и описание лежат в переводах объявления: берём русский, иначе язык оригинала, иначе любой. */
export function textOf(listing: Listing): { title: string; description: string } {
  const tr = listing.translations as unknown
  const pick = (x: unknown) => (x && typeof x === 'object' ? (x as { title?: string; description?: string }) : null)
  let chosen: { title?: string; description?: string } | null = null
  if (Array.isArray(tr)) {
    const by = (lang?: string) => tr.find((t) => (t as { language?: string; lang?: string }).language === lang || (t as { lang?: string }).lang === lang)
    chosen = pick(by('ru')) ?? pick(by(listing.source_language)) ?? pick(tr[0])
  } else if (tr && typeof tr === 'object') {
    const map = tr as Record<string, unknown>
    chosen = pick(map.ru) ?? pick(map[listing.source_language ?? '']) ?? pick(Object.values(map)[0])
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
  return post<{ token: string; user: import('./auth').User }>('/auth/verify-code', { destination: email, code, channel: 'email', lang: 'ru' })
}

// ---------- избранное (нужен вход) ----------

async function authed<T>(path: string, token: string, method: 'GET' | 'POST' | 'DELETE' = 'GET', body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new ApiError(res.status, '')
  return res.json() as Promise<T>
}

export const favoriteIds = (token: string) => authed<{ ids: string[] }>('/favorites/ids', token)
export const favoriteList = (token: string) => authed<{ total: number; items: FeedItem[] }>('/favorites?lang=ru', token)
export const addFavorite = (token: string, id: string) => authed<{ status: string }>(`/favorites/${encodeURIComponent(id)}`, token, 'POST')
export const removeFavorite = (token: string, id: string) => authed<{ status: string }>(`/favorites/${encodeURIComponent(id)}`, token, 'DELETE')

// ---------- разделы ----------

export type Category = { id: string; slug: string; name: Record<string, string> | string; count?: number; ready?: boolean }

export async function fetchCategories(): Promise<Category[]> {
  return get<Category[]>('/categories?lang=ru')
}

// ---------- сообщения ----------

export type Chat = {
  id: string; listing_id?: string | null; listing_title?: string | null; listing_photo?: string | null; listing_price?: number | null
  currency?: string | null; other_name?: string | null; last_text?: string | null; last_kind?: string | null; last_from_me?: boolean
  last_at?: string | null; unread?: number; is_seller?: boolean; is_team?: boolean
}

export type Message = {
  id: string; sender_id?: string | null; text?: string | null; kind: string; is_read?: boolean
  offer_price?: number | null; offer_status?: string | null; created_at: string
}

export const chatList = (token: string) => authed<{ total: number; items: Chat[] }>('/chats?lang=ru', token)
export const chatInfo = (token: string, id: string) => authed<Chat>(`/chats/${encodeURIComponent(id)}?lang=ru`, token)
export const chatMessages = (token: string, id: string) => authed<Message[]>(`/chats/${encodeURIComponent(id)}/messages`, token)
export const sendMessage = (token: string, id: string, text: string) =>
  authed<Message>(`/chats/${encodeURIComponent(id)}/messages`, token, 'POST', { text, offer_price: null })
export const markChatRead = (token: string, id: string) => authed<unknown>(`/chats/${encodeURIComponent(id)}/read`, token, 'POST')
export const startChat = (token: string, listingId: string) => authed<Chat>('/chats/start?lang=ru', token, 'POST', { listing_id: listingId })

