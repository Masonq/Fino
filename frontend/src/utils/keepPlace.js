import { useEffect, useRef } from 'react'

/**
 * Возвращает страницу туда, где человек её оставил.
 *
 * В админке списки длинные: модерация, пользователи, журнал действий.
 * Модератор уходит в карточку, возвращается — и оказывается в начале
 * списка, хотя разбирал сотую запись. Браузер сам умеет это только
 * для обычных переходов, а в приложении переход между экранами для
 * него не перезагрузка страницы, и восстанавливать ему нечего.
 *
 * Храним в sessionStorage, а не в памяти: свайп «назад» на телефоне
 * иногда перезагружает страницу целиком, и всё, что жило в памяти,
 * при этом пропадает. sessionStorage переживает перезагрузку и
 * очищается сам, когда человек закрывает вкладку.
 */
export function useKeepPlace(key) {
  const restored = useRef(false)

  useEffect(() => {
    if (restored.current) return
    restored.current = true

    let saved = 0
    try { saved = Number(sessionStorage.getItem(`place:${key}`) || 0) } catch { /* не беда */ }
    if (saved <= 0) return

    // Список при возврате грузится заново: сперва скелетоны, потом
    // записи. Прокручивать в этот момент ещё некуда — страница
    // короткая, и браузер молча оставляет её наверху. Поэтому не
    // «через пару кадров», а пока не получится: пробуем каждые сто
    // миллисекунд, пока страница не дорастёт до нужной высоты.
    let tries = 0
    const timer = setInterval(() => {
      tries += 1
      const reachable = document.documentElement.scrollHeight - window.innerHeight
      if (reachable >= saved - 4) {
        window.scrollTo(0, saved)
        clearInterval(timer)
        return
      }
      // Полторы секунды — это дольше любой загрузки списка. Если за это
      // время страница не выросла, записей стало меньше: прокручивать
      // некуда, и настаивать незачем.
      if (tries >= 15) clearInterval(timer)
    }, 100)

    return () => clearInterval(timer)
  }, [key])

  useEffect(() => {
    const remember = () => {
      // Ноль не запоминаем: он приходит и в тот момент, когда страница
      // только открылась и ещё ничего не прокручено, — и затирал бы
      // настоящее место.
      if (window.scrollY > 0) {
        try { sessionStorage.setItem(`place:${key}`, String(window.scrollY)) } catch { /* не беда */ }
      }
    }
    window.addEventListener('scroll', remember, { passive: true })
    window.addEventListener('pagehide', remember)
    return () => {
      remember()
      window.removeEventListener('scroll', remember)
      window.removeEventListener('pagehide', remember)
    }
  }, [key])
}

/**
 * То же для выбранного отбора: вкладка, фильтр, строка поиска.
 * Возвращается вместе со страницей — иначе модератор каждый раз заново
 * выставляет «только жалобы».
 */
export function keepValue(key, value) {
  try { sessionStorage.setItem(`value:${key}`, JSON.stringify(value)) } catch { /* не беда */ }
}

export function readValue(key, fallback) {
  try {
    const saved = sessionStorage.getItem(`value:${key}`)
    return saved === null ? fallback : JSON.parse(saved)
  } catch {
    return fallback
  }
}
