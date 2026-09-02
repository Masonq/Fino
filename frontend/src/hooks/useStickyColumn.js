import { useEffect, useRef, useState } from 'react'

/**
 * Липкая боковая колонка.
 *
 * Считаем положение сами, а не одним CSS position:sticky: он не
 * срабатывал в Safari (лендинг раздела, страница профиля — везде одна
 * и та же болезнь), при том что в Chromium работает. Прямое сравнение
 * координат в обработчике прокрутки ведёт себя одинаково в любом
 * браузере и не зависит от того, как движок трактует sticky.
 *
 * Три состояния, а не два — это важно:
 *   false    — верх колонки ещё на экране, блок стоит в обычном потоке;
 *   'fixed'  — блок прибит к верху окна;
 *   'bottom' — колонка кончается: блок останавливается на её нижнем
 *              крае и дальше уезжает вверх вместе со страницей.
 *
 * Без третьего состояния блок висел на экране и после конца своей
 * колонки, доезжая до подвала — со стороны это выглядит как «блок едет
 * вниз вместе со страницей».
 *
 * Ориентир — родитель блока: он остаётся в потоке, даже когда сам блок
 * из него вынут (position:fixed), поэтому его координаты можно считать
 * всегда одинаково, не зная текущего состояния.
 *
 * @param {number} topGap отступ от верха окна в прибитом состоянии
 * @param {boolean} ready блок уже в разметке (данные загрузились)
 */
export default function useStickyColumn(topGap = 20, ready = true) {
  const ref = useRef(null)
  const [stuck, setStuck] = useState(false)
  const [left, setLeft] = useState(0)
  const [bottomTop, setBottomTop] = useState(0)

  useEffect(() => {
    const measure = () => {
      const el = ref.current
      const parent = el?.parentElement
      if (!el || !parent) return
      const box = parent.getBoundingClientRect()
      const height = el.offsetHeight
      if (box.top >= topGap) {
        setStuck(false)
        return
      }
      if (box.bottom - height <= topGap) {
        setBottomTop(Math.max(0, box.height - height))
        setStuck('bottom')
        return
      }
      setLeft(box.left)
      setStuck('fixed')
    }

    measure()
    window.addEventListener('scroll', measure, { passive: true })
    // Ширина окна меняется — вместе с ней и левый край колонки, а он у
    // прибитого блока задан числом в стиле и сам по себе не пересчитается.
    window.addEventListener('resize', measure)
    // Содержимое колонки может дорасти уже после первого замера
    // (подгрузились объявления, раскрылся список) — тогда точка, где
    // блок должен остановиться, сдвигается.
    let ro = null
    if (typeof ResizeObserver !== 'undefined' && ref.current?.parentElement) {
      ro = new ResizeObserver(measure)
      ro.observe(ref.current)
      ro.observe(ref.current.parentElement)
    }
    return () => {
      window.removeEventListener('scroll', measure)
      window.removeEventListener('resize', measure)
      if (ro) ro.disconnect()
    }
  }, [topGap, ready])

  return {
    ref,
    stuck,
    // Класс дописывается к своему имени колонки: .is-fixed / .is-bottom
    className: stuck ? ` is-${stuck}` : '',
    style: stuck === 'fixed' ? { left }
      : stuck === 'bottom' ? { top: bottomTop }
        : undefined,
  }
}
