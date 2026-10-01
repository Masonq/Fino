import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Шкала «дешевле / обычно / дороже»: где цена объявления среди похожих на PLONK.
 *
 * Средняя зона — от нижней до верхней четверти цен похожих (low_eur…high_eur), края — по 60% её ширины в каждую
 * сторону. Метка при открытии подъезжает от середины к своему месту — видно, что это измерение, а не украшение.
 * Без нужных чисел (мало похожих, старый кэш) шкала не рисуется вовсе.
 */
export default function PriceGauge({ mine, low, high, label }) {
  const { t } = useTranslation()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let second = 0
    const first = requestAnimationFrame(() => { second = requestAnimationFrame(() => setReady(true)) })
    return () => { cancelAnimationFrame(first); cancelAnimationFrame(second) }
  }, [])

  if (!(mine > 0) || !(high > low)) return null
  const span = high - low
  const min = low - span * 0.6
  const max = high + span * 0.6
  const pos = Math.min(97, Math.max(3, ((mine - min) / (max - min)) * 100))
  const edge = ((span * 0.6) / (max - min)) * 100

  return (
    <div className="pg" role="img" aria-label={label}>
      <div className="pg-track" style={{ gridTemplateColumns: `${edge}% minmax(0, 1fr) ${edge}%` }}>
        <span className="pg-zone is-cheap" />
        <span className="pg-zone is-fair" />
        <span className="pg-zone is-high" />
      </div>
      <span className="pg-marker" style={{ left: `${ready ? pos : 50}%` }} />
      <div className="pg-labels">
        <span>{t('price_check.zone_cheap')}</span>
        <span>{t('price_check.zone_fair')}</span>
        <span>{t('price_check.zone_high')}</span>
      </div>
    </div>
  )
}
