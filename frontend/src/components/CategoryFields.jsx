import { useTranslation } from 'react-i18next'

/**
 * Поля, важные именно для этого раздела.
 *
 * У квартиры спрашивают «снять или купить» и число комнат, у машины —
 * марку и год, у работы — ищет человек место или сотрудника. Общая
 * форма с ценой и городом ни на один из этих вопросов не отвечает, и
 * человек уходит листать всё подряд.
 *
 * Показываем только там, где поля правда разные. В одежде и мебели
 * достаточно обычного поиска, и лишний блок там только отодвинет
 * объявления вниз.
 */

// Что спрашивать в каком разделе. Ключ — начало пути раздела, чтобы
// «real-estate» покрывал и «real-estate/flats».
const FIELDS = {
  'real-estate': {
    modes: ['buy', 'rent', 'daily'],
    chips: ['rooms1', 'rooms2', 'rooms3', 'studio'],
  },
  auto: {
    modes: null,
    chips: ['cars', 'moto', 'trucks', 'parts'],
  },
  jobs: {
    modes: ['looking', 'hiring'],
    chips: ['partTime', 'fullTime', 'remote'],
  },
}

export default function CategoryFields({ slug, value, onChange }) {
  const { t } = useTranslation()

  const key = Object.keys(FIELDS).find(
    (k) => slug === k || slug?.startsWith(`${k}-`) || slug?.startsWith(`${k}/`),
  )
  if (!key) return null

  const { modes, chips } = FIELDS[key]

  return (
    <div className="cat-fields">
      {/* Первый вопрос — самый крупный: он делит раздел надвое, и без
          ответа на него всё остальное не имеет смысла. */}
      {modes && (
        <div className="cat-modes">
          {modes.map((mode) => (
            <button
              key={mode}
              className={`cat-mode${value.mode === mode ? ' on' : ''}`}
              onClick={() => onChange({ ...value, mode: value.mode === mode ? '' : mode })}
            >
              {t(`fields.${key}.${mode}`)}
            </button>
          ))}
        </div>
      )}

      <div className="cat-chips">
        {chips.map((chip) => (
          <button
            key={chip}
            className={`cat-chip${value.chip === chip ? ' on' : ''}`}
            onClick={() => onChange({ ...value, chip: value.chip === chip ? '' : chip })}
          >
            {t(`fields.${key}.${chip}`)}
          </button>
        ))}
      </div>
    </div>
  )
}
