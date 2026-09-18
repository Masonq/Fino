// Объявления, удалённые в этом сеансе.
//
// Лента и вкладки держатся в памяти пять минут, чтобы возврат из
// объявления не перезагружал всё заново. Из-за этого удалённое
// объявление возвращалось на экран: сервер о нём уже забыл, а память
// на устройстве — ещё нет, и человек видел то, что только что стёр.
//
// Помним такие id и просто не показываем их, пока не истечёт память
// списков. Живёт в sessionStorage: перезагрузка страницы не должна
// воскрешать удалённое.
const KEY = 'plonk_removed_listings'
const CAP = 200

function load() {
  try { return new Set(JSON.parse(sessionStorage.getItem(KEY) || '[]')) } catch { return new Set() }
}

let removed = load()

export function rememberRemoved(id) {
  if (!id || removed.has(id)) return
  removed.add(id)
  try {
    sessionStorage.setItem(KEY, JSON.stringify([...removed].slice(-CAP)))
  } catch { /* приватный режим — останется только в памяти */ }
}

export function isRemoved(id) {
  return removed.has(id)
}

/** Отфильтровать список объявлений перед показом. */
export function withoutRemoved(items) {
  return removed.size ? (items || []).filter((l) => !removed.has(l.id)) : (items || [])
}
