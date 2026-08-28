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
export const FIELDS = {
  'real-estate': {
    modes: ['sale', 'rent', 'daily'],
    chips: ['rooms1', 'rooms2', 'rooms3', 'studio'],
  },
  jobs: {
    modes: ['resume', 'vacancy'],
    chips: ['partTime', 'fullTime', 'remote'],
  },
  // Слова уже были готовы в modeWords.js (cars/moto/trucks/parts) —
  // подкатегории (Легковые/Мото/Грузовые/Запчасти) делают то же самое
  // переходом по ссылке, а modes даёт уточнить это же на месте, не
  // уходя со страницы поиска, тем же приёмом, что и sale/rent/daily
  // у недвижимости.
  auto: {
    modes: ['cars', 'moto', 'trucks', 'parts'],
  },
}

// Вынесено отдельно — Search.jsx использует тот же поиск ключа, чтобы
// подписать активный фильтр («Посуточно», «2 комнаты») человеческим
// текстом в чипе над результатами, а не хранить перевод дважды.
export function fieldsKeyFor(slug) {
  return Object.keys(FIELDS).find(
    (k) => slug === k || slug?.startsWith(`${k}-`) || slug?.startsWith(`${k}/`),
  )
}

export default function CategoryFields({ slug, value, onChange }) {
  const { t } = useTranslation()

  const key = fieldsKeyFor(slug)
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

      {chips && (
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
      )}
    </div>
  )
}
