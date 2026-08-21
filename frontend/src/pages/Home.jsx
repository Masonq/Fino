import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { CATEGORY_ICONS, FALLBACK_ICON } from '../components/CategoryIcons'

const CITIES = ['Београд', 'Нови Сад', 'Ниш', 'Крагујевац', 'Суботица']

const PROMO_SLIDES = [
  { key: 'safe_deal', to: '/search', icon: 'shield', top: '#0E9F6E', grad: 'linear-gradient(180deg, #0E9F6E 0%, #0E9F6E 22%, #1DB388 48%, #34D8A8 78%, #5CE8CC 100%)' },
  { key: 'free_post', to: '/post', icon: 'tag', top: '#F2860C', grad: 'linear-gradient(180deg, #F2860C 0%, #F2860C 22%, #F5A524 48%, #FFC259 78%, #FFD98A 100%)' },
  { key: 'три_языка', to: '/search', icon: 'globe', top: '#3B5BF6', grad: 'linear-gradient(180deg, #3B5BF6 0%, #3B5BF6 22%, #4F7BF7 48%, #6D9BFB 78%, #93BAFF 100%)' },
  { key: 'verified', to: '/search', icon: 'check', top: '#6D3DFC', grad: 'linear-gradient(180deg, #6D3DFC 0%, #6D3DFC 22%, #8156FD 48%, #9E7BFE 78%, #BEA4FF 100%)' },
  { key: 'local', to: '/search', icon: 'pin', top: '#E0326B', grad: 'linear-gradient(180deg, #E0326B 0%, #E0326B 22%, #F0507F 48%, #FA7A9D 78%, #FFA8BF 100%)' },
]

const PROMO_ICONS = {
  shield: <img src="/promo-safe-deal.png" alt="" />,
  tag: (
    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.5 13.3 13 20.8a2 2 0 0 1-2.8 0l-7-7A2 2 0 0 1 2.6 12V4.6a2 2 0 0 1 2-2H12a2 2 0 0 1 1.4.6l7.1 7.1a2 2 0 0 1 0 2.9Z" />
      <circle cx="7.6" cy="7.6" r="1.4" />
    </svg>
  ),
  globe: (
    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><path d="M3 12h18" />
      <path d="M12 3c2.4 2.6 3.4 5.8 3.4 9s-1 6.4-3.4 9c-2.4-2.6-3.4-5.8-3.4-9s1-6.4 3.4-9Z" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3 5 6v6c0 4.2 2.9 7.6 7 9 4.1-1.4 7-4.8 7-9V6l-7-3Z" /><path d="m9 12 2.2 2.2L15.5 10" />
    </svg>
  ),
  pin: (
    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21.5s7.2-6.6 7.2-12.3A7.2 7.2 0 1 0 4.8 9.2C4.8 14.9 12 21.5 12 21.5Z" />
      <circle cx="12" cy="9" r="2.6" />
    </svg>
  ),
}

export default function Home() {
  const { t, i18n } = useTranslation()
  const [categories, setCategories] = useState([])
  const [listings, setListings] = useState([])
  const [cols, setCols] = useState(2)
  const [city, setCity] = useState(CITIES[0])
  const [collapsed, setCollapsed] = useState(false)
  // слайд выбирается один раз при загрузке страницы (как у Avito) — без автокарусели,
  // иначе цвет статус-бара не успевает за сменой и отстаёт
  const [slide] = useState(() => Math.floor(Math.random() * PROMO_SLIDES.length))

  // Статус-бар на iOS 26 Safari больше НЕ управляется theme-color: браузер берёт цвет
  // из background-color липкого элемента у края экрана (наш баннер) в момент отрисовки.
  // Поэтому цвет задаётся через backgroundColor баннера выше, а мета-тег ниже нужен
  // только для Android и старых версий Safari.
  useEffect(() => {
    document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.remove())
    const meta = document.createElement('meta')
    meta.setAttribute('name', 'theme-color')
    meta.setAttribute('content', PROMO_SLIDES[slide].top)
    document.head.appendChild(meta)
  }, [slide])

  useEffect(() => {
    let ticking = false
    const update = () => {
      ticking = false
      const y = window.scrollY
      // мягкий гистерезис: сворачиваем после 48px, разворачиваем ниже 30px —
      // достаточно, чтобы не мигало, но без резкого «щелчка» при обратной прокрутке
      setCollapsed((prev) => (prev ? y > 30 : y > 48))
    }
    const onScroll = () => {
      if (ticking) return
      ticking = true
      requestAnimationFrame(update)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    update()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    api.searchListings({ lang: i18n.language, limit: 12 })
      .then((res) => setListings(res.items || []))
      .catch(() => setListings([]))
  }, [i18n.language])

  return (
    <div className="home">
      <div
        className={collapsed ? 'avito-banner collapsed' : 'avito-banner'}
        style={collapsed ? undefined : {
          backgroundColor: PROMO_SLIDES[slide].top,
          backgroundImage: PROMO_SLIDES[slide].grad,
        }}
      >
        <div className="avito-toprow">
          <Link to="/search" className="avito-search">
            <div className="avito-search-logo">
              <span style={{ background: 'var(--primary)' }} />
              <span style={{ background: 'var(--violet)' }} />
              <span style={{ background: 'var(--coral)' }} />
            </div>
            <span>{t('search.placeholder')}</span>
            <span className="avito-search-filter" aria-label="Фильтры">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
            </span>
          </Link>
          <Link to="/identify" className="avito-login-pill">
            {localStorage.getItem('fino_user_id') ? <div className="avatar-mini">М</div> : t('common.login')}
          </Link>
        </div>

        <div className="promo-collapse">
          <div>
            <div className="avito-promo-row">
              <div className="avito-promo-left">
                <div className="promo-slides">
                  {PROMO_SLIDES.map((s, i) => (
                    <Link
                      key={s.key}
                      to={s.to}
                      className={i === slide ? 'promo-slide active' : 'promo-slide'}
                      aria-hidden={i !== slide}
                    >
                      <span className="avito-promo-text">
                        {t(`promo.${s.key}`)}
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="m9 6 6 6-6 6" /></svg>
                      </span>
                    </Link>
                  ))}
                </div>

                <div className="banner-meta">
                  <div className="city-pill">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                      <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" />
                    </svg>
                    <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="Город">
                      {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <LanguageSwitcher />
                </div>
              </div>

              <div className="avito-promo-illustration">
                {PROMO_SLIDES.map((s, i) => (
                  <div key={s.key} className={i === slide ? 'promo-glyph active' : 'promo-glyph'}>
                    {PROMO_ICONS[s.icon]}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {(() => {
        const all = [{ id: '__all', slug: null, isAll: true }, ...categories]
        const top = all.filter((_, i) => i % 2 === 0)
        const bottom = all.filter((_, i) => i % 2 === 1)
        const renderTile = (cat) => cat.isAll ? (
          <Link key="__all" to="/categories" className="cat-tile-2row all">
            <div className="cat-tile-2row-label">{t('common.all')}</div>
            <div className="cat-tile-2row-glyph">{FALLBACK_ICON}</div>
          </Link>
        ) : (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="cat-tile-2row">
            <div className="cat-tile-2row-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
            <div className="cat-tile-2row-glyph" style={{ color: cat.color || 'var(--primary)' }}>
              {CATEGORY_ICONS[cat.slug] || FALLBACK_ICON}
            </div>
          </Link>
        )
        return (
          <div className="cat-rows">
            <div className="cat-row">{top.map(renderTile)}</div>
            <div className="cat-row">{bottom.map(renderTile)}</div>
          </div>
        )
      })()}

      <div className="feed-head-row">
        <div className="feed-heading">{t('common.recommendations')}</div>
        <div className="col-toggle">
          <button className={cols === 2 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(2)} aria-label="По 2 в ряд">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /></svg>
          </button>
          <button className={cols === 1 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(1)} aria-label="По 1 в ряд">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
          </button>
        </div>
      </div>

      <div className={cols === 2 ? 'infinite-grid' : 'infinite-list'}>
        {listings.map((l) => (
          <ListingCard key={l.id} listing={l} large={cols === 1} />
        ))}
        {listings.length === 0 && (
          <p className="empty-hint">{t('common.no_listings')}</p>
        )}
      </div>
    </div>
  )
}
