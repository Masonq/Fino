import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Горизонтальная лента со стрелками листания.
 *
 * На телефоне такую ленту листают пальцем, на ноутбуке — двумя пальцами
 * по тачпаду, а вот обычной мышью её не сдвинуть ничем: колесо крутит
 * только вертикально, и всё, что не поместилось, остаётся недоступным.
 * Поэтому стрелки — по краям, поверх ленты, и только там, где есть
 * настоящий курсор (media hover/pointer в styles.css) и только когда
 * лента действительно шире своего окна.
 *
 * Прокрутку считаем от ширины видимой части, а не на фиксированное
 * число пикселей: в узком блоке шаг в 300px перепрыгнул бы половину
 * карточек, в широком — сдвинул бы ленту почти незаметно.
 */
export default function HScroll({ className = '', children, step = 0.8 }) {
  const ref = useRef(null)
  const { t } = useTranslation()
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(false)

  const measure = useCallback(() => {
    const el = ref.current
    if (!el) return
    // 2px запаса: при дробном масштабе (например, 125% в системе)
    // scrollLeft почти никогда не совпадает с максимумом точно, и
    // правая стрелка оставалась бы включённой в самом конце ленты.
    setCanLeft(el.scrollLeft > 2)
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 2)
  }, [])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    measure()
    el.addEventListener('scroll', measure, { passive: true })
    window.addEventListener('resize', measure)
    let ro = null
    if (typeof ResizeObserver !== 'undefined') {
      // Содержимое приходит с сервера уже после первого замера —
      // без наблюдателя стрелки не появились бы вовсе.
      ro = new ResizeObserver(measure)
      ro.observe(el)
    }
    return () => {
      el.removeEventListener('scroll', measure)
      window.removeEventListener('resize', measure)
      if (ro) ro.disconnect()
    }
  }, [measure, children])

  const scrollBy = (dir) => {
    const el = ref.current
    if (!el) return
    el.scrollBy({ left: dir * el.clientWidth * step, behavior: 'smooth' })
  }

  return (
    <div className="hscroll">
      <div className={className} ref={ref}>{children}</div>
      <button
        type="button"
        className="hscroll-arrow left"
        onClick={() => scrollBy(-1)}
        disabled={!canLeft}
        aria-label={t('actions.back')}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
      </button>
      <button
        type="button"
        className="hscroll-arrow right"
        onClick={() => scrollBy(1)}
        disabled={!canRight}
        aria-label={t('actions.forward')}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
      </button>
    </div>
  )
}
