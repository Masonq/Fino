// Откуда человек пришёл на объявление.
//
// После удаления объявления страница уходила в раздел его категории —
// а человек искал по слову («бронь»), нашёл несколько и удалял их
// подряд. Каждый раз он оказывался в категории и набирал запрос заново.
// Запоминаем последнюю страницу-список: поиск со всеми его условиями,
// главную, избранное, свои объявления, очередь модерации. Возвращаемся
// именно туда.
const LIST_PATHS = /^\/(search|favorites|my|moderation|admin\/users|categories)(\/|$|\?)/

let last = '/'

export function rememberListPage(pathname, search) {
  if (pathname === '/' || LIST_PATHS.test(pathname)) {
    last = pathname + (search || '')
    try { sessionStorage.setItem('plonk_last_list', last) } catch { /* не беда */ }
  }
}

export function lastListPage() {
  if (last !== '/') return last
  try { return sessionStorage.getItem('plonk_last_list') || '/' } catch { return '/' }
}
