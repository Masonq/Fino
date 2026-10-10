/**
 * «Цена на рынке за год» — для машин: медиана таких же (марка и модель) по месяцам, обычная вилка цен и где на ней
 * эта машина. Помогает понять, справедлива ли цена, и торговаться. Мало похожих — блока нет.
 */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

const fmt = (n) => `€${Math.round(n).toLocaleString('ru-RU').replace(/\u00a0/g, ' ')}`

export default function MarketChart({ listingId }) {
  const { t, i18n } = useTranslation()
  const [m, setM] = useState(null)
  useEffect(() => { api.listingMarket(listingId).then(setM).catch(() => setM(null)) }, [listingId])
  if (!m?.enough) return null
  // шкала — от минимума к максимуму, а не от нуля: иначе разница в 10% превращается в одинаковые столбики
  const vals = m.points.map((p) => p.median)
  const lo = Math.min(...vals), hi = Math.max(...vals)
  const h = (v) => (hi === lo ? 60 : 18 + ((v - lo) / (hi - lo)) * 82)
  const diff = m.this && m.median ? Math.round(((m.this - m.median) / m.median) * 100) : null
  const month = (s) => new Date(`${s}-01`).toLocaleDateString(i18n.language, { month: 'short' })
  return (
    <div className="market-card">
      <div className="market-head">
        <b>{t('market.title')}</b>
        <span>{t(`market.scope_${m.scope}`, { count: m.count })}</span>
      </div>
      <div className="market-range">
        {t('market.usual')} <b className="nw">{fmt(m.low)} – {fmt(m.high)}</b> · {t('market.median')} <b className="nw">{fmt(m.median)}</b>
      </div>
      {diff !== null && (
        <div className={`market-verdict ${diff <= -40 ? 'high' : diff <= -5 ? 'good' : diff >= 10 ? 'high' : ''}`}>
          {diff <= -40 ? t('market.too_cheap', { n: -diff }) : diff <= -5 ? t('market.below', { n: -diff }) : diff >= 10 ? t('market.above', { n: diff }) : t('market.fair')}
        </div>
      )}
      <div className="market-bars" role="img" aria-label={t('market.title')}>
        {m.points.map((p, i) => (
          <div key={p.month} className="market-bar">
            <i style={{ height: `${h(p.median)}%` }} title={`${fmt(p.median)} · ${p.count}`} />
            <span>{i % 2 === 0 || m.points.length <= 6 ? month(p.month) : '\u00a0'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
