import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { CardSkeletons, CategorySkeletons } from '../components/Skeletons'
import PullToRefresh from '../components/PullToRefresh'
import SearchOverlay from '../components/SearchOverlay'
import OfflineNotice, { LoadError } from '../components/OfflineNotice'
import { useAuth } from '../context/AuthContext'
import { CITIES, cityLabel } from '../data/cities'
import CategoryArt from '../components/CategoryArt'

// Лента живёт в памяти между заходами на страницу. Иначе при возврате из
// объявления она загружается заново: страница успевает отрисоваться пустой,
// потом появляются карточки, потом прыгает прокрутка — это и был рывок.
// Восстановить положение после отрисовки недостаточно, нужно чтобы к первой
// же отрисовке лента была той же, что была.
let feedCache = { lang: null, items: [], total: 0, scroll: 0 }

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
// Все картинки приведены к единой высоте и общей базовой линии прямо в файлах,
// поэтому индивидуальная подгонка масштаба больше не нужна.
// Точная подгонка отдельных категорий поверх общего выравнивания.
// Точная подгонка отдельных категорий поверх общего выравнивания.
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
  // объявляем до первого обращения: ниже с него начинается состояние ленты
  const cached = feedCache.lang === i18n.language ? feedCache : null

  const [listings, setListings] = useState(() => cached?.items || [])
  const [feedLoaded, setFeedLoaded] = useState(() => Boolean(cached?.items.length))
  const [feedError, setFeedError] = useState(false)
  const [feedTotal, setFeedTotal] = useState(() => cached?.total || 0)
  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef(null)
  const [cols, setCols] = useState(2)
  const [city, setCity] = useState(CITIES[0].slug)
  // Браузер восстанавливает прокрутку не мгновенно, и шапка успевала
  // развернуться и тут же схлопнуться — при возврате это читалось как рывок.
  // Берём положение прокрутки сразу, а переход включаем только после того,
  // как оно установилось.
  const [collapsed, setCollapsed] = useState(() => (cached?.scroll || window.scrollY) > 48)
  // сколько прокрутки предстоит восстановить — до этого шапку не трогаем
  const pendingScroll = useRef(cached?.scroll || 0)
  const restored = useRef(false)
  const [settled, setSettled] = useState(false)
  // слайд выбирается один раз при загрузке страницы (как у Avito) — без автокарусели,
  // иначе цвет статус-бара не успевает за сменой и отстаёт
  const [slide] = useState(() => Math.floor(Math.random() * PROMO_SLIDES.length))
  const [searchOpen, setSearchOpen] = useState(false)
  const { user } = useAuth()

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
      // Пока положение не восстановлено, прокрутка равна нулю, и шапка
      // разворачивалась — а сразу после восстановления схлопывалась обратно.
      // Именно это и выглядело как рывок при возврате.
      if (pendingScroll.current && !restored.current) return
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
    const settle = setTimeout(() => { update(); setSettled(true) }, 250)
    return () => { clearTimeout(settle); window.removeEventListener('scroll', onScroll) }
  }, [])

  useEffect(() => {
    api.getCategories()
      .then(setCategories)
      .catch(() => setCategories([]))
      .finally(() => setCatsLoaded(true))
  }, [])

  const PAGE = 12

  const loadFeed = useCallback(() => (
    api.searchListings({ lang: i18n.language, limit: PAGE, offset: 0 })
      .then((res) => {
        setListings(res.items || [])
        setFeedTotal(res.total || 0)
        setFeedError(false)
      })
      .catch(() => { setListings([]); setFeedError(true) })
      .finally(() => setFeedLoaded(true))
  ), [i18n.language])

  // Подгружаем следующую порцию, когда человек дочитал до низа —
  // иначе лента обрывается на двенадцатом объявлении.
  const loadMore = useCallback(() => {
    if (loadingMore) return
    setLoadingMore(true)
    api.searchListings({ lang: i18n.language, limit: PAGE, offset: listings.length })
      .then((res) => setListings((prev) => [...prev, ...(res.items || [])]))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [i18n.language, listings.length, loadingMore])

  useEffect(() => {
    if (!feedLoaded || listings.length >= feedTotal) return
    const el = sentinelRef.current
    if (!el) return

    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '600px' },   // начинаем заранее, чтобы не было паузы
    )
    io.observe(el)
    return () => io.disconnect()
  }, [feedLoaded, listings.length, feedTotal, loadMore])

  useEffect(() => {
    // при возврате лента уже есть — перезагрузка сбросила бы её к двенадцати
    // объявлениям и снова уронила прокрутку
    if (cached?.items.length) return
    loadFeed()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadFeed])

  // Лента подгружается порциями, поэтому к моменту, когда браузер
  // восстанавливает прокрутку, страница ещё короткая и он прижимает её к
  // низу — человек возвращался из объявления не туда, где был. Запоминаем
  // место сами и возвращаемся, когда объявления отрисованы.
  useEffect(() => {
    const save = () => {
      feedCache = {
        lang: langRef.current,
        items: itemsRef.current,
        total: totalRef.current,
        scroll: window.scrollY,
      }
    }
    window.addEventListener('pagehide', save)
    return () => { save(); window.removeEventListener('pagehide', save) }
  }, [])

  // обработчик ухода со страницы создаётся один раз, поэтому свежие
  // значения держим в ref
  const itemsRef = useRef(listings)
  const totalRef = useRef(feedTotal)
  const langRef = useRef(i18n.language)
  useEffect(() => { itemsRef.current = listings }, [listings])
  useEffect(() => { totalRef.current = feedTotal }, [feedTotal])
  useEffect(() => { langRef.current = i18n.language }, [i18n.language])

  // Прокрутку выставляем до первой отрисовки — из useLayoutEffect. Через
  // requestAnimationFrame страница успевала показаться сверху и лишь потом
  // прыгала на место.
  useLayoutEffect(() => {
    if (restored.current || !cached?.scroll || !listings.length) return
    restored.current = true
    const target = cached.scroll
    window.scrollTo(0, target)
    // Картинки и шрифты догружаются после первой отрисовки и слегка меняют
    // высоту, а iOS вдобавок правит прокрутку под свою панель. Повторяем
    // пару раз в течение полусекунды — иначе положение уезжает уже после
    // того, как мы его выставили.
    let tries = 0
    const id = setInterval(() => {
      if (Math.abs(window.scrollY - target) > 2) window.scrollTo(0, target)
      if (++tries >= 8) clearInterval(id)
    }, 60)
    return () => clearInterval(id)
  }, [cached, listings.length])

  const handleRefresh = useCallback(async () => {
    await Promise.all([
      loadFeed(),
      api.getCategories().then(setCategories).catch(() => {}),
    ])
  }, [loadFeed])

  return (
    <PullToRefresh onRefresh={handleRefresh}>
      <OfflineNotice onRetry={loadFeed} />
    <div className="home">
      <div
        className={[
          'avito-banner',
          collapsed ? 'collapsed' : '',
          settled ? '' : 'no-anim',
        ].filter(Boolean).join(' ')}
        style={{
          backgroundColor: collapsed ? '#FFFFFF' : PROMO_SLIDES[slide].top,
          backgroundImage: collapsed ? 'none' : PROMO_SLIDES[slide].grad,
        }}
      >
        <div className="avito-toprow">
          <button type="button" className="avito-search" onClick={() => setSearchOpen(true)}>
            <img className="search-logo-mark" src="/logo-mark.png" alt="PLONK" />
            <span>{t('search.placeholder')}</span>
            <span className="avito-search-filter" aria-label={t('misc.filters')} data-label={t('misc.find')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
            </span>
          </button>
          <Link to={user ? '/profile' : '/login'} className="avito-login-pill">
            {user
              ? <div className="avatar-mini">{(user.display_name || '?').trim().charAt(0).toUpperCase()}</div>
              : t('common.login')}
          </Link>
        </div>

        {/* Иллюстрация фоном, а не в углу: так заголовку достаётся вся ширина,
            и картинка не спорит с ним за место при длинном тексте. */}
        <div className="promo-backdrop" aria-hidden="true">
          {PROMO_SLIDES.map((s, i) => (
            <div key={s.key} className={i === slide ? 'promo-glyph active' : 'promo-glyph'}>
              {PROMO_IMAGES[s.key]
                ? <img src={PROMO_IMAGES[s.key]} alt="" onError={(e) => { e.currentTarget.style.display = 'none' }} />
                : PROMO_FALLBACK}
            </div>
          ))}
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
            <div className="cat-tile-2row-glyph"><CategoryArt slug="all" /></div>
          </Link>
        ) : (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="cat-tile-2row">
            <div className="cat-tile-2row-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
            <div className="cat-tile-2row-glyph"><CategoryArt slug={cat.slug} /></div>
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
        feedError
          ? <LoadError onRetry={() => { setFeedLoaded(false); loadFeed() }} />
          : <p className="empty-hint">{t('common.no_listings')}</p>
      )}

      <div ref={sentinelRef} className="feed-sentinel">
        {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}
      </div>
    </div>

      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />
    </PullToRefresh>
  )
}
