import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

// лента шопсов один раз за открытие сайта: главная перерисовывается часто, а список меняется редко
let cache = null

/**
 * Шопсы на главной вместо историй: превью роликов 9:16, первой — «Снять шопс».
 * Нет ни одного опубликованного — одна плитка-приглашение, без пустой полосы скелетонов.
 */
export default function ShopsStrip() {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState(cache)

  useEffect(() => {
    if (cache) return
    api.shopsFeed({ limit: 12, lang: i18n.language })
      .then((r) => { cache = r.items || []; setItems(cache) })
      .catch(() => setItems([]))
  }, [i18n.language])

  if (items === null) {
    return <div className="shs" aria-hidden="true">{Array.from({ length: 5 }, (_, i) => <div key={i} className="shs-tile shs-skel" />)}</div>
  }
  return (
    <div className="shs" role="list" aria-label={t('shops.title')}>
      <Link to="/shops/new" className="shs-tile shs-new" role="listitem">
        <span className="shs-plus">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
        </span>
        <span className="shs-new-text">{items.length ? t('shops.create_short') : t('shops.create_first')}</span>
      </Link>
      {items.map((s) => (
        <Link key={s.id} to={`/shops?start=${s.id}`} className="shs-tile" role="listitem" aria-label={s.caption || s.author?.name}>
          {s.poster_url && <img src={s.poster_url} alt="" loading="lazy" decoding="async" />}
          <span className="shs-shade" />
          {s.items?.[0]?.price != null && (
            <span className="shs-price">{Math.round(s.items[0].price).toLocaleString('ru-RU')} {s.items[0].currency === 'EUR' ? '€' : s.items[0].currency}</span>
          )}
          <span className="shs-author">{s.author?.name}</span>
        </Link>
      ))}
    </div>
  )
}
