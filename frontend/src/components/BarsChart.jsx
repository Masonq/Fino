import { useState } from 'react'
import { useTranslation } from 'react-i18next'

// Столбики рисуем сами: ради одного графика тянуть библиотеку незачем,
// а по высоте прямоугольника провал виден не хуже.
//
// Прокрутка вбок вместо прореживания подписей: у каждого дня своя
// фиксированная ширина, хватает места на двузначное число всегда,
// сколько бы дней ни было выбрано — раньше пытались сжать все 30 в
// экран разом, из-за чего то раздувало страницу вбок, то подписи
// приходилось через одну прятать.
//
// unitKey — ключ перевода единицы измерения в строке над графиком
// («объявлений», «просмотров» и т.п.) — раньше был жёстко зашит под
// один-единственный случай использования в статистике админки.
export default function BarsChart({
  items, valueKey, secondKey,
  unitKey = 'stats.listings_count',
  // Подпись второго ряда. Раньше здесь было жёстко «своих» — годится
  // для объявлений, но у посещаемости второй ряд это люди, и выходило
  // «97 заходов (37 своих)». Увидел на снимке.
  secondLabelKey = 'stats.own_short',
  promotions = [],
}) {
  const { t, i18n } = useTranslation()
  const [selectedDay, setSelectedDay] = useState(null)
  const peak = Math.max(1, ...items.map((d) => d[valueKey] || 0))

  // Даты продвижения приходят точными метками времени (начало/конец),
  // а столбики графика — по календарным дням: день промаркирован, если
  // хоть немного пересекается с периодом хоть одного продвижения —
  // человек смотрит по дням, не по часам, «весь день чуть-чуть
  // подсвечен» понятнее, чем дробить один столбик пополам.
  const promotedDays = new Map()
  for (const p of promotions) {
    const start = new Date(p.starts_at)
    const end = new Date(p.expires_at)
    for (const d of items) {
      const dayStart = new Date(`${d.day}T00:00:00`)
      const dayEnd = new Date(`${d.day}T23:59:59.999`)
      if (start <= dayEnd && end >= dayStart && !promotedDays.has(d.day)) {
        promotedDays.set(d.day, p.type)
      }
    }
  }

  const active = items.find((d) => d.day === selectedDay) || items[items.length - 1]
  const activeValue = active ? (active[valueKey] || 0) : 0
  const activeSecond = active && secondKey ? (active[secondKey] || 0) : 0
  const activeDate = active
    ? new Date(`${active.day}T00:00:00`).toLocaleDateString(i18n.language, { day: 'numeric', month: 'long' })
    : ''
  const activePromo = active ? promotedDays.get(active.day) : null

  return (
    <div>
      {active && (
        <div className="stats-bars-info">
          <b>{activeDate}</b> — {activeValue} {t(unitKey)}
          {!!secondKey && ` (${activeSecond} ${t(secondLabelKey)})`}
          {activePromo && <span className="stats-bars-promo-tag">{t(`promo.type_${activePromo}`)}</span>}
        </div>
      )}
      <div className="stats-bars">
        {items.map((d) => {
          const value = d[valueKey] || 0
          const second = secondKey ? d[secondKey] || 0 : 0
          const isActive = active === d
          const promoted = promotedDays.has(d.day)
          return (
            <button
              type="button"
              key={d.day}
              className={isActive ? 'stats-bar selected' : 'stats-bar'}
              onClick={() => setSelectedDay(d.day)}
            >
              <div className="stats-bar-track">
                <div
                  className="stats-bar-fill"
                  style={{ height: `${(value / peak) * 100}%` }}
                >
                  {!!second && (
                    <div
                      className="stats-bar-own"
                      style={{ height: `${(second / Math.max(value, 1)) * 100}%` }}
                    />
                  )}
                </div>
              </div>
              <span className="stats-bar-day">{d.day.slice(8)}</span>
              {promoted && <span className="stats-bar-promo-dot" />}
            </button>
          )
        })}
      </div>
      {promotedDays.size > 0 && (
        <div className="stats-bars-legend">
          <span className="stats-bar-promo-dot" />
          {t('stats.promo_legend')}
        </div>
      )}
    </div>
  )
}
