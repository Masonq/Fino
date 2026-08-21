import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { CardSkeletons, CategorySkeletons } from '../components/Skeletons'
import PullToRefresh from '../components/PullToRefresh'
import { CITIES, cityLabel } from '../data/cities'

const PROMO_SLIDES = [
  { key: 'safe_deal', to: '/search', icon: 'shield', top: '#0E9F6E', grad: 'linear-gradient(180deg, #0E9F6E 0%, #0E9F6E 22%, #1DB388 48%, #34D8A8 78%, #5CE8CC 100%)' },
  { key: 'free_post', to: '/post', icon: 'tag', top: '#F2860C', grad: 'linear-gradient(180deg, #F2860C 0%, #F2860C 22%, #F5A524 48%, #FFC259 78%, #FFD98A 100%)' },
  { key: 'три_языка', to: '/search', icon: 'globe', top: '#3B5BF6', grad: 'linear-gradient(180deg, #3B5BF6 0%, #3B5BF6 22%, #4F7BF7 48%, #6D9BFB 78%, #93BAFF 100%)' },
  { key: 'verified', to: '/search', icon: 'check', top: '#6D3DFC', grad: 'linear-gradient(180deg, #6D3DFC 0%, #6D3DFC 22%, #8156FD 48%, #9E7BFE 78%, #BEA4FF 100%)' },
  { key: 'local', to: '/search', icon: 'pin', top: '#E0326B', grad: 'linear-gradient(180deg, #E0326B 0%, #E0326B 22%, #F0507F 48%, #FA7A9D 78%, #FFA8BF 100%)' },
]

// Иллюстрации слайдов. Пока картинка не готова — показываем запасную SVG-иконку.
// На картинках с несколькими предметами каждый выходит мельче, поэтому
// показываем их крупнее — чтобы визуальный вес всех плиток был одинаковым.
const PHOTO_SCALE = {
  beauty: 1.42,
  pets: 1.42,
  electronics: 1.39,
  jobs: 1.3,
  auto: 1.28,
  services: 1.26,
  'real-estate': 1.13,
  fashion: 1.12,
  'home-garden': 1.06,
  'hobby-sport': 1.01,
}

// Точная подгонка положения: [вправо, вниз] в пикселях.
// Бизнес и хобби сидят ровно — их не двигаем.
const PHOTO_SHIFT = {
  // высокие и узкие — опускаем, чтобы не висели
  'real-estate': [0, 6],
  services: [-2, 2],
  'hobby-sport': [-2, 2],
  business: [-2, 0],
  jobs: [0, 4],
  // широкие — почти не двигаем
  auto: [0, 4],
  fashion: [0, 2],
  electronics: [2, 4],
  'home-garden': [2, 4],
  // эти сидели низко — приподнимаем
  kids: [0, -2],
  pets: [0, 0],
  beauty: [2, 4],
}

const PROMO_IMAGES = {
  safe_deal: '/promo/safe_deal.png',
  free_post: '/promo/free_post.png',
  'три_языка': '/promo/lang.png',
  verified: '/promo/verified.png',
  local: '/promo/nearby.png',
}

const PROMO_FALLBACK = (
  <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3 5 6v6c0 4.2 2.9 7.6 7 9 4.1-1.4 7-4.8 7-9V6l-7-3Z" /><path d="m9 12 2.2 2.2L15.5 10" />
  </svg>
)

export default function Home() {
  const { t, i18n } = useTranslation()
  const [categories, setCategories] = useState([])
  const [catsLoaded, setCatsLoaded] = useState(false)
  const [listings, setListings] = useState([])
  const [feedLoaded, setFeedLoaded] = useState(false)
  const [cols, setCols] = useState(2)
  const [city, setCity] = useState(CITIES[0].slug)
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
      // сворачиваем после 48px, а разворачиваем уже на 6px — Safari начинает
      // перекрашивать статус-бар сразу при движении вверх, и при большом пороге
      // шапка догоняла его с заметным опозданием
      setCollapsed((prev) => (prev ? y > 6 : y > 48))
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
    api.getCategories()
      .then(setCategories)
      .catch(() => setCategories([]))
      .finally(() => setCatsLoaded(true))
  }, [])

  const loadFeed = useCallback(() => (
    api.searchListings({ lang: i18n.language, limit: 12 })
      .then((res) => setListings(res.items || []))
      .catch(() => setListings([]))
      .finally(() => setFeedLoaded(true))
  ), [i18n.language])

  useEffect(() => { loadFeed() }, [loadFeed])

  const handleRefresh = useCallback(async () => {
    await Promise.all([
      loadFeed(),
      api.getCategories().then(setCategories).catch(() => {}),
    ])
  }, [loadFeed])

  return (
    <PullToRefresh onRefresh={handleRefresh}>
    <div className="home">
      <div
        className={collapsed ? 'avito-banner collapsed' : 'avito-banner'}
        style={{
          backgroundColor: collapsed ? '#FFFFFF' : PROMO_SLIDES[slide].top,
          backgroundImage: collapsed ? 'none' : PROMO_SLIDES[slide].grad,
        }}
      >
        <div className="avito-toprow">
          <Link to="/search" className="avito-search">
            <img className="search-logo-mark" src="/logo-mark.png" alt="PLONK" />
            <span>{t('search.placeholder')}</span>
            <span className="avito-search-filter" aria-label={t('misc.filters')}>
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
                        <span className="promo-text-label">{t(`promo.${s.key}`)}</span>
                        <svg className="promo-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="m9 6 6 6-6 6" /></svg>
                      </span>
                    </Link>
                  ))}
                </div>

                <div className="banner-meta">
                  <div className="city-pill">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                      <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" />
                    </svg>
                    <select value={city} onChange={(e) => setCity(e.target.value)} aria-label={t('post.city')}>
                      {CITIES.map((c) => <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>)}
                    </select>
                  </div>
                  <LanguageSwitcher />
                </div>
              </div>

              <div className="avito-promo-illustration">
                {PROMO_SLIDES.map((s, i) => (
                  <div key={s.key} className={i === slide ? 'promo-glyph active' : 'promo-glyph'}>
                    {PROMO_IMAGES[s.key]
                      ? <img src={PROMO_IMAGES[s.key]} alt="" onError={(e) => { e.currentTarget.style.display = 'none' }} />
                      : PROMO_FALLBACK}
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
            <div className="cat-tile-2row-glyph">
              <img className="cat-photo all-anim" src="/cat/all.gif" alt="" />
            </div>
          </Link>
        ) : (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="cat-tile-2row">
            <div className="cat-tile-2row-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
            <div className="cat-tile-2row-glyph">
              <img
                className="cat-photo"
                src={`/cat/${cat.slug}.png`}
                alt=""
                style={(() => {
                  const scale = PHOTO_SCALE[cat.slug]
                  const [dx, dy] = PHOTO_SHIFT[cat.slug] || [0, 0]
                  if (!scale && !dx && !dy) return undefined
                  const parts = []
                  if (dx || dy) parts.push(`translate(${dx}px, ${dy}px)`)
                  if (scale) parts.push(`scale(${scale})`)
                  return { transform: parts.join(' ') }
                })()}
              />
            </div>
          </Link>
        )
        if (!catsLoaded) {
          return (
            <div className="cat-rows">
              <div className="cat-row"><CategorySkeletons count={5} /></div>
              <div className="cat-row"><CategorySkeletons count={5} offset={5} /></div>
            </div>
          )
        }
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
          <button className={cols === 2 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(2)} aria-label={t('misc.cols_2')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /></svg>
          </button>
          <button className={cols === 1 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(1)} aria-label={t('misc.cols_1')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
          </button>
        </div>
      </div>

      <div className={cols === 2 ? 'infinite-grid' : 'infinite-list'}>
        {!feedLoaded
          ? <CardSkeletons count={cols === 2 ? 4 : 2} />
          : listings.map((l) => (
              <ListingCard key={l.id} listing={l} large={cols === 1} />
            ))}
      </div>
      {feedLoaded && listings.length === 0 && (
        <p className="empty-hint">{t('common.no_listings')}</p>
      )}
    </div>
    </PullToRefresh>
  )
}
