import { prefs } from './prefs'

/** «Вы смотрели» — как на сайте: номера открытых объявлений на телефоне, свежие первыми, не больше 60. */
const KEY = 'plonk_viewed'
const MAX = 60

export async function rememberViewed(id: string) {
  const list = await viewedIds()
  const next = [id, ...list.filter((x) => x !== id)].slice(0, MAX)
  await prefs.set(KEY, next.join(','))
}

export async function viewedIds(): Promise<string[]> {
  const raw = await prefs.get(KEY)
  return raw ? raw.split(',').filter(Boolean) : []
}

export async function clearViewed() { await prefs.set(KEY, '') }
