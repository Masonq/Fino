/**
 * Единая точка прокрутки приложения.
 *
 * В обычном браузере прокручивается сама страница, и всё работает так,
 * как работало годами: window.scrollY, window.scrollTo, событие scroll
 * на окне.
 *
 * В приложении, добавленном на домашний экран, так делать нельзя.
 * Собрал, как это решают другие, и все сходятся в одном: в этом режиме
 * WebKit отдаёт высоту всего экрана вместо видимой части, документ
 * получает лишнюю прокрутку, а закреплённые элементы — нижняя панель,
 * липкие шапки, кнопка «Написать продавцу» — уезжают вместе с
 * резиновым отскоком. Лечится это не подбором высоты, а тем, что
 * оболочка прибивается к краям экрана (position:fixed; inset:0), а
 * прокручивается один-единственный контейнер внутри неё.
 *
 * Чтобы не переписывать всё приложение на два режима, здесь один
 * переключатель: код спрашивает «где прокрутка?» и получает либо окно,
 * либо контейнер.
 */

const SCROLLER_ID = 'app-scroll'

/** Приложение открыто с домашнего экрана, а не во вкладке браузера. */
export function isStandalone() {
  try {
    return window.matchMedia('(display-mode: standalone)').matches
      || window.navigator.standalone === true
  } catch { return false }
}

/** Элемент, который на самом деле прокручивается. */
export function scroller() {
  if (isStandalone()) {
    const el = document.getElementById(SCROLLER_ID)
    if (el) return el
  }
  return null                 // null = прокручивается страница целиком
}

/** Текущее положение прокрутки. */
export function scrollPos() {
  const el = scroller()
  return el ? el.scrollTop : window.scrollY
}

/** Прокрутить к нужному месту. */
export function scrollTo(top, behavior) {
  const el = scroller()
  if (el) el.scrollTo({ top, behavior })
  else window.scrollTo({ top, behavior })
}

/** Мгновенно наверх — при переходе на другую страницу. */
export function scrollTop() {
  const el = scroller()
  if (el) el.scrollTop = 0
  else window.scrollTo(0, 0)
}

/** Подписка на прокрутку: возвращает функцию отписки. */
export function onScroll(handler, opts = { passive: true }) {
  const el = scroller() || window
  el.addEventListener('scroll', handler, opts)
  return () => el.removeEventListener('scroll', handler, opts)
}

/**
 * Рамка для IntersectionObserver: в приложении наблюдать надо
 * относительно контейнера, иначе наблюдатель считает видимым то, что
 * на экране давно не видно, — и лента либо не догружается, либо грузит
 * всё подряд.
 */
export function observerRoot() {
  return scroller()
}
