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
export default function BarsChart({ items, valueKey, secondKey, unitKey = 'stats.listings_count' }) {
  const { t, i18n } = useTranslation()
  const [selectedDay, setSelectedDay] = useState(null)
  const peak = Math.max(1, ...items.map((d) => d[valueKey] || 0))

  const active = items.find((d) => d.day === selectedDay) || items[items.length - 1]
  const activeValue = active ? (active[valueKey] || 0) : 0
  const activeSecond = active && secondKey ? (active[secondKey] || 0) : 0
  const activeDate = active
    ? new Date(`${active.day}T00:00:00`).toLocaleDateString(i18n.language, { day: 'numeric', month: 'long' })
    : ''

  return (
    <div>
      {active && (
        <div className="stats-bars-info">
          <b>{activeDate}</b> — {activeValue} {t(unitKey)}
          {!!secondKey && ` (${activeSecond} ${t('stats.own_short')})`}
        </div>
      )}
      <div className="stats-bars">
        {items.map((d) => {
          const value = d[valueKey] || 0
          const second = secondKey ? d[secondKey] || 0 : 0
          const isActive = active === d
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
            </button>
          )
        })}
      </div>
    </div>
  )
}
