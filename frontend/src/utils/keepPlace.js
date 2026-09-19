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
export function useKeepPlace(key, ready = true) {
  const restored = useRef(false)

  useEffect(() => {
    if (!ready || restored.current) return
    restored.current = true
    let saved = 0
    try { saved = Number(sessionStorage.getItem(`place:${key}`) || 0) } catch { /* не беда */ }
    if (saved > 0) {
      // Два кадра: за первый список успевает отрисоваться, иначе
      // прокручивать ещё нечего и браузер остаётся наверху.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        window.scrollTo(0, saved)
      }))
    }
  }, [key, ready])

  useEffect(() => {
    const remember = () => {
      try { sessionStorage.setItem(`place:${key}`, String(window.scrollY)) } catch { /* не беда */ }
    }
    window.addEventListener('scroll', remember, { passive: true })
    // Уход со страницы — последний момент, когда позицию ещё можно
    // записать: событие прокрутки к тому времени уже не придёт.
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
