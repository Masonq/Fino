/**
 * История просмотренных объявлений.
 *
 * Держим на устройстве, а не на сервере: это личное, работает без входа
 * в аккаунт и не требует лишних запросов. Хранится идентификатор и время —
 * сами объявления подтягиваем при показе, чтобы цена и статус были свежими.
 */
const KEY = 'plonk_viewed'
const LIMIT = 40

// Полный номер объявления, а не обрезок из адреса.
//
// Раньше в историю писалась последняя часть красивого адреса — восемь
// знаков вместо тридцати шести. Такие записи уже лежат у людей в
// браузере, и один негодный номер ломал запрос целиком: страница «Вы
// смотрели» оставалась пустой, даже если в списке были и правильные
// записи. Отбрасываем их при чтении.
const FULL_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function readHistory() {
  try {
    const raw = localStorage.getItem(KEY)
    const list = raw ? JSON.parse(raw) : []
    return list.filter((x) => FULL_ID.test(x?.id || ''))
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
