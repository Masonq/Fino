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
    if (deal) params.set('sub', deal)
    Object.entries(values).forEach(([key, value]) => {
      if (value) params.set(key, value)
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

      {/* Первый вопрос делит раздел надвое: без ответа на него
          остальное бессмысленно. */}
      {landing?.deal && (
        <div className="landing-deal">
          {landing.deal.options.map((opt) => (
            <button
              key={opt.value}
              className={`landing-deal-btn${deal === opt.value ? ' on' : ''}`}
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
            <div className="landing-chips">
              {field.options.map((opt) => (
                <button
                  key={opt}
                  className={`landing-chip${values[field.key] === opt ? ' on' : ''}`}
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
