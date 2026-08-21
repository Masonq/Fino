/**
 * История просмотренных объявлений.
 *
 * Держим на устройстве, а не на сервере: это личное, работает без входа
 * в аккаунт и не требует лишних запросов. Хранится идентификатор и время —
 * сами объявления подтягиваем при показе, чтобы цена и статус были свежими.
 */
const KEY = 'plonk_viewed'
const LIMIT = 40

export function readHistory() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function addToHistory(id) {
  if (!id) return
  try {
    const list = readHistory().filter((x) => x.id !== id)
    list.unshift({ id, at: Date.now() })
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, LIMIT)))
  } catch {
    // приватный режим или переполнено — история не критична
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY)
  } catch { /* нечего чистить */ }
}
