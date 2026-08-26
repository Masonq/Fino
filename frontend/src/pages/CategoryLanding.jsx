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

// Цветная шапка раздела — тот же приём, что у промо-баннера на главной
// (свой градиент на категорию), а не голая белая полоса. Своей
// фотокомпозиции под каждый раздел ещё нет, поэтому вместо неё —
// крупный контурный значок раздела поверх градиента.
const BANNER_GRADIENTS = {
  'real-estate': 'linear-gradient(135deg, #0E9F6E 0%, #1DB388 55%, #5CE8CC 100%)',
  auto: 'linear-gradient(135deg, #3B5BF6 0%, #4F7BF7 55%, #93BAFF 100%)',
  electronics: 'linear-gradient(135deg, #2B6CE0 0%, #4A8AF0 55%, #8FC1FF 100%)',
  'home-garden': 'linear-gradient(135deg, #0E9F6E 0%, #34D8A8 55%, #B7F5E1 100%)',
  fashion: 'linear-gradient(135deg, #E0326B 0%, #F0507F 55%, #FFA8BF 100%)',
  kids: 'linear-gradient(135deg, #F2860C 0%, #F5A524 55%, #FFD98A 100%)',
  'hobby-sport': 'linear-gradient(135deg, #6D3DFC 0%, #8156FD 55%, #BEA4FF 100%)',
  pets: 'linear-gradient(135deg, #E0326B 0%, #F0507F 55%, #FFC2D3 100%)',
  beauty: 'linear-gradient(135deg, #C0399B 0%, #DD5DBB 55%, #FBC6EE 100%)',
  services: 'linear-gradient(135deg, #0A7A54 0%, #0E9F6E 55%, #7EE4C1 100%)',
  jobs: 'linear-gradient(135deg, #3B5BF6 0%, #6D9BFB 55%, #C6DBFF 100%)',
  business: 'linear-gradient(135deg, #1B2A4A 0%, #3B5BF6 55%, #93BAFF 100%)',
}

export default function CategoryLanding() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

  const [category, setCategory] = useState(null)
  const [fresh, setFresh] = useState([])
  const [deal, setDeal] = useState('')
  const [values, setValues] = useState({})
  const [text, setText] = useState('')
  const [showAllSubs, setShowAllSubs] = useState(false)

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
      <div className="landing-hero" style={{ background: BANNER_GRADIENTS[slug] || BANNER_GRADIENTS['real-estate'] }}>
        <div className="landing-hero-card" aria-hidden="true">
          <CategoryArt slug={slug} />
        </div>
        <div className="landing-head">
          <button className="landing-back on-hero" onClick={() => navigate('/categories')}
                  aria-label={t('actions.back')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3"
                 strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <h1 className="landing-title on-hero">{name}</h1>
          {category?.count > 0 && (
            <div className="landing-count on-hero">
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
          видит, что тут есть. Как у Авито — несколько плиток с картинкой
          и «Все категории» последней, а не весь список сразу: длинный
          список подряд читается хуже, чем несколько картинок и явный
          переход дальше. */}
      {category?.children?.length > 0 && (() => {
        const subs = category.children
        const showLimit = subs.length > 6
        const visible = showLimit ? subs.slice(0, 5) : subs
        return (
          <div className="landing-subs">
            {visible.map((sub) => (
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
            {showLimit && (
              <button
                className="landing-sub landing-sub-all"
                onClick={() => setShowAllSubs(true)}
              >
                <span className="landing-sub-name">{t('common.all_categories')}</span>
                <svg className="landing-sub-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m9 6 6 6-6 6" /></svg>
              </button>
            )}
          </div>
        )
      })()}

      {showAllSubs && (
        <div className="subs-modal">
          <div className="subs-modal-head">
            <button className="subs-modal-close" onClick={() => setShowAllSubs(false)} aria-label={t('actions.close')}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
            <div className="subs-modal-title">{t('common.all_categories')}</div>
          </div>
          <div className="subs-modal-list">
            {category.children.map((sub) => (
              <button
                key={sub.id}
                className="subs-modal-row"
                onClick={() => navigate(`/search?category=${sub.slug}`)}
              >
                {sub.name?.[i18n.language] || sub.name?.ru}
              </button>
            ))}
          </div>
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
