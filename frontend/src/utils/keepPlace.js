import { useEffect, useRef } from 'react'
import { scrollPos, scrollTo, onScroll as onScrollEvent, observerRoot } from './scroller'

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
  // Пока возвращаем страницу на место, запись выключена: иначе наш же
  // scrollTo поднимает событие прокрутки, оно записывает новое
  // значение, а восстановление ставит старое — и страница дёргается
  // между двумя позициями, что и было видно.
  const restoring = useRef(false)

  useEffect(() => {
    if (restored.current) return
    restored.current = true

    // Браузер умеет возвращать страницу на место сам — но по своему
    // разумению и в свой момент. Вдвоём с нашим восстановлением они
    // тянут страницу каждый к своей позиции; просим браузер не
    // вмешиваться.
    try { window.history.scrollRestoration = 'manual' } catch { /* не беда */ }

    let saved = 0
    try { saved = Number(sessionStorage.getItem(`place:${key}`) || 0) } catch { /* не беда */ }
    if (saved <= 0) return

    restoring.current = true

    // Список при возврате грузится заново: сперва скелетоны, потом
    // записи. Прокручивать в этот момент ещё некуда — страница
    // короткая, и браузер молча оставляет её наверху. Поэтому не
    // «через пару кадров», а пока не получится: пробуем каждые сто
    // миллисекунд, пока страница не дорастёт до нужной высоты.
    // Ждём не просто «страница доросла», а «страница перестала расти».
    //
    // Список возвращается в два приёма: сперва скелетоны, потом
    // настоящие строки, и высота у них разная. Если встать на место по
    // первой высоте, через мгновение приходит вторая — и страница
    // прыгает уже после того, как человек начал читать. Поэтому ждём
    // две одинаковые высоты подряд: значит, список дорисовался.
    let tries = 0
    let lastHeight = -1
    const timer = setInterval(() => {
      tries += 1
      const height = document.documentElement.scrollHeight
      const settled = height === lastHeight
      lastHeight = height
      const reachable = height - window.innerHeight
      if (settled && reachable >= saved - 4) {
        scrollTo(saved)
        clearInterval(timer)
        // Отпускаем запись через кадр: событие от нашего же scrollTo
        // придёт следующим, и до него писать нельзя.
        requestAnimationFrame(() => { restoring.current = false })
        return
      }
      // Полторы секунды — это дольше любой загрузки списка. Если за это
      // время страница не выросла, записей стало меньше: прокручивать
      // некуда, и настаивать незачем.
      if (tries >= 15) {
        clearInterval(timer)
        restoring.current = false
      }
    }, 100)

    return () => {
      clearInterval(timer)
      restoring.current = false
    }
  }, [key])

  useEffect(() => {
    const remember = () => {
      // Ноль не запоминаем: он приходит и в тот момент, когда страница
      // только открылась и ещё ничего не прокручено, — и затирал бы
      // настоящее место. И не пишем, пока идёт восстановление.
      if (restoring.current) return
      if (scrollPos() > 0) {
        try { sessionStorage.setItem(`place:${key}`, String(scrollPos())) } catch { /* не беда */ }
      }
    }
    const stop = onScrollEvent(remember)
    window.addEventListener('pagehide', remember)
    return () => {
      remember()
      stop()
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
