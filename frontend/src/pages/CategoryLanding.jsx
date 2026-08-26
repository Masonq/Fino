import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import CategoryArt from '../components/CategoryArt'
import ListingCard from '../components/ListingCard'
import { LANDINGS } from '../data/landings'

/**
 * Вход в раздел.
 *
 * Человек, зашедший в «Недвижимость», ищет не «что-нибудь» — он хочет
 * снять двушку до тысячи евро. Спрашиваем это сразу, а не заставляем
 * листать всё подряд.
 *
 * Ниже — подразделы плитками и свежие объявления: если ответить на
 * вопросы нечем, человек всё равно видит, что тут есть.
 */
export default function CategoryLanding() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

  const [category, setCategory] = useState(null)
  const [fresh, setFresh] = useState([])
  const [deal, setDeal] = useState('')
  const [values, setValues] = useState({})
  const [text, setText] = useState('')

  const landing = LANDINGS[slug]

  useEffect(() => {
    api.getCategories()
      .then((all) => setCategory(all.find((c) => c.slug === slug) || null))
      .catch(() => setCategory(null))

    api.searchListings({ category_slug: slug, limit: 8, lang: i18n.language })
      .then((res) => setFresh(res.items || []))
      .catch(() => setFresh([]))
  }, [slug, i18n.language])

  const search = () => {
    const params = new URLSearchParams({ category: slug })
    if (text.trim()) params.set('q', text.trim())
    // Ключи должны совпадать с тем, что читает Search.jsx через
    // CategoryFields — иначе выбор «Снять» или «2 комнаты» на лендинге
    // никуда не долетает.
    if (deal) params.set('mode', deal)
    const ROOMS_TO_CHIP = { '1': 'rooms1', '2': 'rooms2', '3': 'rooms3' }
    Object.entries(values).forEach(([key, value]) => {
      if (!value) return
      if (key === 'rooms') {
        if (ROOMS_TO_CHIP[value]) params.set('chip', ROOMS_TO_CHIP[value])
        return
      }
      params.set(key, value)
    })
    navigate(`/search?${params}`)
  }

  const name = category?.name?.[i18n.language] || category?.name?.ru || ''

  return (
    <div className="landing">
      <div className="landing-head">
        <button className="landing-back" onClick={() => navigate('/categories')}
                aria-label={t('actions.back')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3"
               strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <h1 className="landing-title">{name}</h1>
        {category?.count > 0 && (
          <div className="landing-count">
            {t('landing.offers', { count: category.count })}
          </div>
        )}
      </div>

      {/* Раньше здесь были только фильтры (комнаты, цена) — можно было
          сузить раздел, но не поискать конкретную вещь словом. Теперь
          можно и то, и другое: слово уходит в q вместе с остальными
          отборами. */}
      <div className="landing-search">
        <div className="search-field">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') search() }}
            placeholder={t('search.placeholder_full')}
            autoComplete="off"
          />
          {text && (
            <button className="search-clear" onClick={() => setText('')} aria-label={t('actions.clear')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
      </div>

      {/* Первый вопрос делит раздел надвое: без ответа на него
          остальное бессмысленно. */}
      {landing?.deal && (
        <div className="cat-modes landing-deal">
          {landing.deal.options.map((opt) => (
            <button
              key={opt.value}
              className={`cat-mode${deal === opt.value ? ' on' : ''}`}
              onClick={() => setDeal(deal === opt.value ? '' : opt.value)}
            >
              {t(opt.label)}
            </button>
          ))}
        </div>
      )}

      {landing?.fields?.map((field) => (
        <div key={field.key} className="landing-field">
          <div className="landing-label">{t(field.label)}</div>

          {field.type === 'chips' && (
            <div className="cat-chips landing-chips">
              {field.options.map((opt) => (
                <button
                  key={opt}
                  className={`cat-chip${values[field.key] === opt ? ' on' : ''}`}
                  onClick={() => setValues({
                    ...values,
                    [field.key]: values[field.key] === opt ? '' : opt,
                  })}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {field.type === 'text' && (
            <input
              className="landing-input"
              placeholder={field.hint ? t(field.hint) : ''}
              value={values[field.key] || ''}
              onChange={(e) => setValues({ ...values, [field.key]: e.target.value })}
            />
          )}

          {field.type === 'range' && (
            <div className="landing-range">
              <input
                className="landing-input"
                inputMode="numeric"
                placeholder={t('landing.from')}
                value={values[`${field.key}_min`] || ''}
                onChange={(e) => setValues({
                  ...values, [`${field.key}_min`]: e.target.value,
                })}
              />
              <input
                className="landing-input"
                inputMode="numeric"
                placeholder={t('landing.to')}
                value={values[`${field.key}_max`] || ''}
                onChange={(e) => setValues({
                  ...values, [`${field.key}_max`]: e.target.value,
                })}
              />
            </div>
          )}
        </div>
      ))}

      <button className="landing-go" onClick={search}>
        {t('landing.show')}
      </button>

      {/* Подразделы: если отвечать на вопросы нечем, человек всё равно
          видит, что тут есть. */}
      {category?.children?.length > 0 && (
        <div className="landing-subs">
          {category.children.map((sub) => (
            <button
              key={sub.id}
              className="landing-sub"
              onClick={() => navigate(`/search?category=${sub.slug}`)}
            >
              <span className="landing-sub-name">
                {sub.name?.[i18n.language] || sub.name?.ru}
              </span>
              <span className="landing-sub-art"><CategoryArt slug={sub.slug} /></span>
            </button>
          ))}
        </div>
      )}

      {fresh.length > 0 && (
        <div className="landing-fresh">
          <h2>{t('landing.fresh')}</h2>
          <div className="feed-grid">
            {fresh.map((l) => <ListingCard key={l.id} listing={l} />)}
          </div>
        </div>
      )}
    </div>
  )
}
