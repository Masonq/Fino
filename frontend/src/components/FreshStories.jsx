import { useEffect, useLayoutEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { formatPrice } from '../utils/money'

// Полоска «Только что» в шапке главной — свежие объявления кружками,
// как сторис. Первый кружок — «Продать»: шапка зовёт не только
// смотреть, но и выкладывать своё.
//
// Кольцо: у непросмотренного свежего — акцентное, у просмотренного
// или старше суток — тонкое белое. Подпись под кружком — цена: это
// то, ради чего открывают объявление; время видно по кольцу.
export default function FreshStories({ items, seen, onOpen }) {
  const { t, i18n } = useTranslation()

  // Полоска помнит, докуда её пролистали.
  //
  // Человек доходит до непросмотренных, открывает объявление, жмёт
  // назад -- и полоска снова в начале: приходится листать те же
  // двадцать кружков заново. Прокрутка тут своя, внутри полоски,
  // поэтому общий возврат на место страницы её не касается.
  const strip = useRef(null)
  const restored = useRef(false)

  // Возвращаем полоску на место до первого кадра, а не после.
  //
  // Было так: эффект после отрисовки заводил таймер на сто
  // миллисекунд и только потом двигал полоску. Человек успевал увидеть
  // её в начале, и она на его глазах прыгала вправо — это и читалось
  // как рывок при возврате с объявления.
  //
  // useLayoutEffect выполняется до того, как браузер покажет кадр.
  // Если кружки уже на месте, прокрутка ставится там же и рывка нет
  // вовсе. Если ещё нет — пробуем каждый следующий кадр, а не раз в
  // сотую долю секунды: попадём в первый же, где полоске есть куда
  // двигаться.
  useLayoutEffect(() => {
    const node = strip.current
    if (!node || items === null || restored.current) return
    restored.current = true

    let saved = 0
    try { saved = Number(sessionStorage.getItem('stories-scroll') || 0) } catch { /* не беда */ }
    if (saved <= 0) return

    let frame = 0
    let tries = 0
    const put = () => {
      if (node.scrollWidth - node.clientWidth >= saved - 4) {
        // На время подстановки снимаем привязку кружков к сетке:
        // с ней браузер после присвоения доводит полоску до ближайшей
        // точки — и она на глазах отъезжает и возвращается. Именно это
        // и видно как рывок. Возвращаем привязку следующим кадром,
        // когда полоска уже стоит.
        const snap = node.style.scrollSnapType
        node.style.scrollSnapType = 'none'
        node.scrollLeft = saved
        requestAnimationFrame(() => { node.style.scrollSnapType = snap })
        return
      }
      if (tries++ < 40) frame = requestAnimationFrame(put)
    }
    put()
    return () => cancelAnimationFrame(frame)
  }, [items])

  useEffect(() => {
    const node = strip.current
    if (!node) return
    const remember = () => {
      // Ноль не пишем: он приходит сразу при открытии страницы, когда
      // полоска ещё в начале, и затирал сохранённое место — из-за
      // этого возврат и не работал.
      if (node.scrollLeft > 0) {
        try { sessionStorage.setItem('stories-scroll', String(node.scrollLeft)) } catch { /* не беда */ }
      }
    }
    node.addEventListener('scroll', remember, { passive: true })
    return () => { remember(); node.removeEventListener('scroll', remember) }
  }, [items])

  const cells = items === null
    ? Array.from({ length: 6 }, (_, i) => <div key={`sk${i}`} className="story story-skeleton"><div className="story-ring"><div className="story-photo" /></div><div className="story-label" /></div>)
    : items.map((l, i) => {
      const hot = l.fresh && !seen.has(l.id)
      return (
        <Link
          key={l.id}
          to={l.path}
          className={hot ? 'story hot' : 'story'}
          onClick={() => onOpen(l.id)}
          onTouchStart={() => api.prefetchListing(l.id)}
          onMouseEnter={() => api.prefetchListing(l.id)}
          aria-label={l.title}
        >
          <div className="story-ring">
            {/* Фото целиком, а не обрезанное кругом: у вещи важен весь
                силуэт, велосипед без колёс — не велосипед. Вписываем
                целиком, а пустые края закрывает размытая копия того же
                фото — круг остаётся заполненным. */}
            <div className="story-photo">
              <img className="story-blur" src={l.cover_photo} alt="" aria-hidden="true" loading={i < 6 ? 'eager' : 'lazy'} decoding="async" />
              <img
                className="story-img"
                src={l.cover_photo}
                alt=""
                loading={i < 6 ? 'eager' : 'lazy'}
                fetchpriority={i < 6 ? 'high' : 'auto'}
                decoding="async"
                style={{ viewTransitionName: `photo-${l.id}` }}
              />
            </div>
          </div>
          <div className={l.is_free ? 'story-label free' : 'story-label'}>
            {l.is_free ? t('detail.free') : (formatPrice(l.price, l.currency, i18n.language) || '—')}
          </div>
        </Link>
      )
    })

  // Историй нет — полоску НЕ убираем, остаётся кнопка «Продать». Раньше здесь был return null: пока грузилось, полоска
  // стояла на месте, а с пустым ответом пропадала целиком, и вся главная под ней прыгала вверх на 90 точек.

  return (
    <div className="stories" role="list" ref={strip}>
      <Link to="/post" className="story story-post" role="listitem">
        <div className="story-ring">
          <div className="story-photo story-plus">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
          </div>
        </div>
        <div className="story-label">{t('fresh.post')}</div>
      </Link>
      {cells}
    </div>
  )
}
