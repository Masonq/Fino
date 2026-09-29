import { useCallback, useRef } from 'react'

/*
 * Подсказка «дальше можно листать» у горизонтальных рядов.
 *
 * Ряд чипов обрезан краем экрана — и человек не всегда понимает, что
 * там есть ещё. Хук выставляет на ряд data-fade: end (есть что листать
 * вправо), start (влево), both или none. Дальше край мягко гаснет
 * маской (см. [data-fade] в styles.css); когда листать нечего, маска
 * снимается, и последний чип не остаётся полупрозрачным.
 *
 * Возвращает ref-функцию, а не объект: ряд на странице появляется не
 * сразу (после входа, после загрузки), и обычный ref успевал бы
 * прочитаться раньше, чем элемент есть.
 */
export default function useScrollFade() {
  const cleanup = useRef(null)
  return useCallback((el) => {
    if (cleanup.current) { cleanup.current(); cleanup.current = null }
    if (!el) return

    const update = () => {
      const max = el.scrollWidth - el.clientWidth
      const start = el.scrollLeft > 4
      const end = el.scrollLeft < max - 4
      el.dataset.fade = start && end ? 'both' : end ? 'end' : start ? 'start' : 'none'
    }
    update()
    el.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null
    if (ro) ro.observe(el)

    cleanup.current = () => {
      el.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
      if (ro) ro.disconnect()
    }
  }, [])
}
