import { useTranslation } from 'react-i18next'

/**
 * Бейджи главных характеристик — для квартир и машин.
 *
 * У этих двух вещей решение принимают по нескольким числам: комнаты,
 * площадь, этаж — или год, пробег, коробка. Они и так есть в
 * характеристиках, но там лежат списком ниже описания, а смотрят их
 * первыми. Поэтому выносим наверх, под заголовок, значками в строку.
 *
 * Только эти два раздела: у стула или куртки такого набора нет, и
 * бейджи из «состояние: хорошее» ничего не добавили бы к заголовку.
 */
const ICONS = {
  rooms: <><rect x="3" y="4" width="8" height="7" rx="1.5" /><rect x="13" y="4" width="8" height="7" rx="1.5" /><rect x="3" y="13" width="8" height="7" rx="1.5" /><rect x="13" y="13" width="8" height="7" rx="1.5" /></>,
  area_m2: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h4M17 3v4" /></>,
  floor: <><path d="M4 20h16" /><path d="M6 20V9l6-4 6 4v11" /><path d="M6 14h12" /></>,
  renovation: <><path d="m14 6 4 4" /><path d="M3 21l3-1 11-11a2.8 2.8 0 0 0-4-4L2 16l-1 3 2 2Z" /></>,
  furnished: <><path d="M4 18v-6a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v6" /><path d="M2 18h20M6 18v2M18 18v2" /><path d="M8 9V7a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></>,
  balcony: <><path d="M4 11h16v9H4z" /><path d="M8 11v9M12 11v9M16 11v9" /><path d="M6 11V6a6 6 0 0 1 12 0v5" /></>,
  bathroom: <><path d="M4 12h16v3a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-3Z" /><path d="M7 12V6a2 2 0 0 1 4 0" /></>,
  deal_type: <><path d="M3 10h18M6 6h12a3 3 0 0 1 3 3v9H3V9a3 3 0 0 1 3-3Z" /></>,

  year: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 3v4M16 3v4M3 11h18" /></>,
  mileage_km: <><path d="M12 15a8 8 0 1 0-7-4.2" /><path d="m12 15 4-5" /><path d="M4 20h16" /></>,
  transmission: <><path d="M6 4v16M12 4v16M18 4v10" /><path d="M6 8h12" /><circle cx="6" cy="4" r="1.4" /><circle cx="12" cy="4" r="1.4" /><circle cx="18" cy="4" r="1.4" /></>,
  fuel_type: <><path d="M4 20V5a2 2 0 0 1 2-2h5a2 2 0 0 1 2 2v15" /><path d="M3 20h12" /><path d="M13 9h3a2 2 0 0 1 2 2v5a1.6 1.6 0 0 0 3 0v-7l-2.5-2.5" /></>,
  engine_volume: <><path d="M4 12h2l2-3h4l2 3h4v5h-2l-2 3H8l-2-3H4z" /><path d="M10 9V6h4v3" /></>,
  body_type: <><path d="M3 14h18v4H3z" /><path d="M5 14 7 8h10l2 6" /><circle cx="7.5" cy="18" r="1.8" /><circle cx="16.5" cy="18" r="1.8" /></>,
  color: <><circle cx="12" cy="12" r="9" /><path d="M12 3a9 9 0 0 1 0 18 4.5 4.5 0 0 1 0-9 4.5 4.5 0 0 0 0-9Z" /></>,
}

// Что показываем и в каком порядке: слева то, по чему решают в первую
// очередь. Больше шести бейджей не бывает — дальше это уже список
// характеристик, он ниже на странице.
const ORDER = {
  'real-estate': ['rooms', 'area_m2', 'floor', 'renovation', 'furnished', 'balcony'],
  auto: ['year', 'mileage_km', 'transmission', 'fuel_type', 'engine_volume', 'body_type'],
}

export default function AttrChips({ rootSlug, attributes, schema, attrLabel, attrValue }) {
  const { t } = useTranslation()
  const keys = ORDER[rootSlug]
  if (!keys || !attributes) return null
  // схема полей приходит отдельным запросом: пока её нет, держим место под ряд значков — иначе ряд появлялся
  // позже и сталкивал карточку продавца вниз на 46 px (замер сдвига вёрстки на странице объявления)
  if (!schema || !schema.length) {
    return keys.some((key) => attributes[key] !== undefined && attributes[key] !== null && attributes[key] !== '')
      ? <div className="attr-chips attr-chips-sk" aria-hidden="true"><span className="sk-block" style={{ width: 120, height: 34, borderRadius: 12 }} /></div>
      : null
  }

  const chips = keys
    .filter((key) => attributes[key] !== undefined && attributes[key] !== null && attributes[key] !== '')
    .filter((key) => schema.some((f) => f.key === key))
    .map((key) => {
      const value = String(attrValue(key, attributes[key]))
      // Для «да/нет» подпись — само название признака: «Балкон», а не
      // «Балкон: да». Отрицательные не показываем вовсе: отсутствие
      // балкона не то, чем зазывают.
      const field = schema.find((f) => f.key === key)
      if (field?.type === 'boolean') {
        return attributes[key] ? { key, text: attrLabel(key) } : null
      }
      // Этаж без подписи — просто число: «16» рядом с площадью
      // читается как что угодно. Если известна этажность дома,
      // показываем вместе: «16/16 эт.» — так пишут в объявлениях.
      if (key === 'floor') {
        const total = attributes.total_floors
        return { key, text: `${value}${total ? `/${total}` : ''} ${t('detail.unit_floor')}` }
      }
      return { key, text: `${value} ${unitFor(key, t)}`.trim() }
    })
    .filter(Boolean)

  if (!chips.length) return null

  return (
    <div className="attr-chips">
      {chips.map((chip) => (
        <span className="attr-chip" key={chip.key}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            {ICONS[chip.key]}
          </svg>
          {chip.text}
        </span>
      ))}
    </div>
  )
}

// Единица измерения рядом с числом: «86 м²», «122 300 км». В самих
// характеристиках она подписана в названии строки, а тут названия нет —
// значок вместо него, и без единицы число не прочитать.
function unitFor(key, t) {
  if (key === 'area_m2') return t('detail.unit_m2')
  if (key === 'mileage_km') return t('detail.unit_km')
  if (key === 'engine_volume') return t('detail.unit_liters')
  if (key === 'rooms') return ''
  return ''
}
