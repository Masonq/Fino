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
export function fetchFeed(opts: { tab: FeedTab; offset: number; q?: string }) {
  const p = new URLSearchParams({ lang: 'ru', limit: String(PAGE), offset: String(opts.offset) })
  if (opts.tab === 'new') p.set('sort', 'new')
  if (opts.tab === 'free') p.set('only_free', 'true')
  if (opts.q) { p.set('q', opts.q); p.set('sort', 'relevance') }
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
