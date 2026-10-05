import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

/**
 * PLONK 2.0: подборки на главной между плитками и лентой — чтобы у главной была иерархия, а не сплошной поток
 * (главная претензия к ленте Vinted). «Новое» и «Вы смотрели» сюда не выносим: они есть отдельно (вкладка «Новое» в ленте, история в профиле). «Витрины продавцов» —
 * открытые витрины с 3+ вещами. Пустая подборка не показывается вовсе.
 */
// Память между заходами: открыл объявление из подборки, вернулся — подборка на том же месте прокрутки,
// без повторной загрузки и мигания скелетом (данные обновляются тихо в фоне).
const memo = { key: null, stores: null, scroll: {} }

export default function HomeSections({ city }) {
  const { t, i18n } = useTranslation()
  const key = `${city || ''}|${i18n.language}`
  const [stores, setStores] = useState(() => (memo.key === key ? memo.stores : null))
  const storesRow = useRef(null)
  useEffect(() => {
    let alive = true
    if (memo.key !== key) { memo.key = key; memo.stores = null; memo.scroll = {} }
    api.sfDiscover({ city: city || undefined, limit: 10 }).then((r) => { memo.stores = r.items || []; if (alive) setStores(memo.stores) }).catch(() => alive && setStores((v) => v ?? []))
    return () => { alive = false }
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  // вернуть прокрутку рядов до первой отрисовки — без видимого прыжка
  useLayoutEffect(() => {
    if (storesRow.current && memo.scroll.stores) storesRow.current.scrollLeft = memo.scroll.stores
  }, [stores])
  const remember = (name) => (e) => { memo.scroll[name] = e.currentTarget.scrollLeft }

  return (
    <>
      {/* пока грузится — скелет того же размера, что и подборка: лента под ней не прыгает */}
      {stores === null && (
        <section className="hs" aria-hidden="true">
          <div className="hs-head"><span className="sk-block hs-sk-title" /></div>
          <div className="hs-row">{[0, 1].map((i) => (
            <span key={i} className="hs-store"><span className="sk-block hs-store-grid" /><span className="sk-block hs-sk-price" /><span className="sk-block hs-sk-name" style={{ width: '50%' }} /></span>
          ))}</div>
        </section>
      )}
      {stores?.length > 0 && (
        <section className="hs">
          <div className="hs-head">
            <h2 className="hs-title">{t('hs.stores')}</h2>
            <Link to="/vitriny" className="hs-all">{t('hs.all')}</Link>
          </div>
          <div className="hs-row" ref={storesRow} onScroll={remember('stores')}>
            {stores.map((s) => (
              <Link key={s.slug} to={`/s/${s.slug}`} className="hs-store">
                <span className="hs-store-grid">{s.previews.slice(0, 3).map((p, i) => <img key={i} src={p} alt="" loading="lazy" />)}</span>
                <span className="hs-store-name">{s.name}</span>
                <span className="hs-store-sub">{t('sf.items_n', { count: s.count })}{s.city ? ` · ${s.city}` : ''}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </>
  )
}
