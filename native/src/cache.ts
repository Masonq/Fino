import { File, Paths } from 'expo-file-system'
import { Platform } from 'react-native'

/**
 * Сохранённое на телефоне — для офлайна и мгновенного показа: сначала показываем сохранённое, свежее
 * подгружаем следом. В памяти — для быстрых повторных чтений; на диске — между запусками (папка документов,
 * её система не чистит). В веб-превью — хранилище браузера.
 */
const mem = new Map<string, unknown>()
const fileFor = (key: string) => new File(Paths.document, `plonk-cache-${key.replace(/[^\w-]/g, '_').slice(0, 120)}.json`)

export async function readCache<T>(key: string): Promise<T | null> {
  if (mem.has(key)) return mem.get(key) as T
  try {
    let raw: string | null = null
    if (Platform.OS === 'web') raw = globalThis.localStorage?.getItem(`plonk-cache:${key}`) ?? null
    else { const f = fileFor(key); if (f.exists) raw = await f.text() }
    if (!raw) return null
    const value = JSON.parse(raw) as T
    mem.set(key, value)
    return value
  } catch {
    return null
  }
}

export function writeCache(key: string, value: unknown) {
  mem.set(key, value)
  try {
    const raw = JSON.stringify(value)
    if (Platform.OS === 'web') globalThis.localStorage?.setItem(`plonk-cache:${key}`, raw)
    else fileFor(key).write(raw)
  } catch { /* место кончилось или нет доступа — живём без кэша */ }
}
