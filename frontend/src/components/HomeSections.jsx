import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { formatPrice } from '../utils/money'

/**
 * PLONK 2.0: подборки на главной между плитками и лентой — чтобы у главной была иерархия, а не сплошной поток
 * (главная претензия к ленте Vinted). «Новое сегодня» — свежие объявления города, «Витрины продавцов» —
 * открытые витрины с 3+ вещами. Пустая подборка не показывается вовсе.
 */
export default function HomeSections({ city }) {
  const { t, i18n } = useTranslation()
  const [fresh, setFresh] = useState(null)
  const [stores, setStores] = useState(null)
  useEffect(() => {
    let alive = true
    api.getFresh(city || undefined, i18n.language).then((r) => alive && setFresh(r.items || [])).catch(() => alive && setFresh([]))
    api.sfDiscover({ city: city || undefined, limit: 10 }).then((r) => alive && setStores(r.items || [])).catch(() => alive && setStores([]))
    return () => { alive = false }
  }, [city, i18n.language])

  return (
    <>
      {fresh?.length > 2 && (
        <section className="hs">
          <div className="hs-head"><h2 className="hs-title">{t('hs.fresh')}</h2></div>
          <div className="hs-row">
            {fresh.slice(0, 12).map((l) => (
              <Link key={l.id} to={l.path} className="hs-card">
                <span className="hs-photo">
                  <img src={l.cover_photo} alt="" loading="lazy" decoding="async" />
                  {l.fresh && <span className="hs-new">{t('fresh.badge')}</span>}
                </span>
                <span className="hs-price">{l.is_free ? t('detail.free') : formatPrice(l.price, l.currency, i18n.language)}</span>
                <span className="hs-name">{l.title}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
      {stores?.length > 0 && (
        <section className="hs">
          <div className="hs-head">
            <h2 className="hs-title">{t('hs.stores')}</h2>
            <Link to="/vitriny" className="hs-all">{t('hs.all')}</Link>
          </div>
          <div className="hs-row">
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
