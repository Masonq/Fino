/**
 * «Цена на рынке за год» — для машин: медиана таких же (марка и модель) по месяцам, обычная вилка цен и где на ней
 * эта машина. Помогает понять, справедлива ли цена, и торговаться. Мало похожих — блока нет.
 */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

const fmt = (n) => `€${Math.round(n).toLocaleString('ru-RU').replace(/\u00a0/g, ' ')}`

// Линейный график: медиана по месяцам (линия с точками и заливкой), полоса обычной цены (между 25% и 75%),
// пунктир «эта машина», подписи цен слева и месяцев снизу; нажатие на месяц — подсказка с ценой и числом машин
function LineChart({ m, month, t }) {
  const [sel, setSel] = useState(null)
  const W = 340, H = 190, L = 46, R = 10, T = 14, B = 26
  const pts = m.points
  const vals = [...pts.map((p) => p.median), m.low, m.high, ...(m.this ? [m.this] : [])]
  let lo = Math.min(...vals), hi = Math.max(...vals)
  const pad = (hi - lo) * 0.12 || hi * 0.1
  lo = Math.max(0, lo - pad); hi += pad
  const x = (i) => L + (pts.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (pts.length - 1))
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B)
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.median).toFixed(1)}`).join(' ')
  const area = `${line} L${x(pts.length - 1).toFixed(1)},${H - B} L${x(0).toFixed(1)},${H - B} Z`
  const ticks = [0, 1, 2, 3].map((k) => lo + ((hi - lo) * k) / 3)
  const short = (v) => (v >= 1000 ? `€${Math.round(v / 100) / 10}k` : `€${Math.round(v)}`)
  const thisOut = m.this && (m.this < lo || m.this > hi)
  return (
    <div className="market-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('market.title')}>
        <defs>
          <linearGradient id="mk-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0FA36A" stopOpacity=".28" /><stop offset="1" stopColor="#0FA36A" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className="mk-grid" />
            <text x={L - 6} y={y(v) + 4} textAnchor="end" className="mk-axis">{short(v)}</text>
          </g>
        ))}
        <rect x={L} width={W - L - R} y={y(m.high)} height={Math.max(2, y(m.low) - y(m.high))} className="mk-band" />
        <path d={area} fill="url(#mk-fill)" />
        <path d={line} className="mk-line" />
        {m.this && !thisOut && (
          <g>
            <line x1={L} x2={W - R} y1={y(m.this)} y2={y(m.this)} className="mk-this" />
            <text x={W - R} y={y(m.this) - 5} textAnchor="end" className="mk-this-t">{t('market.this_car')} {short(m.this)}</text>
          </g>
        )}
        {pts.map((p, i) => (
          <g key={p.month} onClick={() => setSel(sel === i ? null : i)} style={{ cursor: 'pointer' }}>
            <rect x={x(i) - 12} y={T} width="24" height={H - T - B} fill="transparent" />
            <circle cx={x(i)} cy={y(p.median)} r={sel === i ? 5.5 : 3.5} className="mk-dot" />
            {(i % 2 === 0 || pts.length <= 6) && <text x={x(i)} y={H - 8} textAnchor="middle" className="mk-axis">{month(p.month)}</text>}
          </g>
        ))}
        {sel !== null && (() => {
          const p = pts[sel], tx = Math.min(Math.max(x(sel), L + 44), W - R - 44), ty = Math.max(y(p.median) - 40, T)
          return (
            <g pointerEvents="none">
              <rect x={tx - 44} y={ty} width="88" height="30" rx="9" className="mk-tip" />
              <text x={tx} y={ty + 13} textAnchor="middle" className="mk-tip-a">{fmt(p.median)}</text>
              <text x={tx} y={ty + 25} textAnchor="middle" className="mk-tip-b">{month(p.month)} · {p.count}</text>
            </g>
          )
        })()}
      </svg>
      <div className="mk-legend">
        <span><i className="lg-line" />{t('market.legend_median')}</span>
        <span><i className="lg-band" />{t('market.legend_band')}</span>
        {m.this && !thisOut && <span><i className="lg-this" />{t('market.this_car')}</span>}
      </div>
    </div>
  )
}

export default function MarketChart({ listingId }) {
  const { t, i18n } = useTranslation()
  const [m, setM] = useState(null)
  useEffect(() => { api.listingMarket(listingId).then(setM).catch(() => setM(null)) }, [listingId])
  if (!m?.enough) return null
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
      <LineChart m={m} month={month} t={t} />
    </div>
  )
}
