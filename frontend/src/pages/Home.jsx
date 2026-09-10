import { useCallback, useEffect, useRef, useState } from 'react'
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
import { hasLanding } from '../data/landings'

// Лента живёт в памяти между заходами на страницу. Иначе при возврате из
// объявления она загружается заново: страница успевает отрисоваться пустой,
// потом появляются карточки, потом прыгает прокрутка — это и был рывок.
// Восстановить положение после отрисовки недостаточно, нужно чтобы к первой
// же отрисовке лента была той же, что была.
//
// Но как и в Moderation.jsx (тот же класс проблемы, найден и там): кэш без
// срока жизни означает, что лента после первой загрузки не обновляется
// вообще никогда за сессию — вернулся спустя час, а видишь тот же снимок.
// FEED_CACHE_TTL — компромисс: быстрый заход в объявление и обратно не
// сбрасывает прокрутку и не мигает пустым списком, а настоящий возврат
// спустя время подтягивает свежую ленту.
//
// Пять минут. Минуты было мало: человек читает объявление, смотрит
// фотографии, пишет продавцу — и на возврате лента перезагружалась,
// хотя он никуда не уходил.
//
// За пять минут в ленте всё равно почти ничего не меняется: за сутки
// прибавляется несколько сотен объявлений на четыре тысячи. А цена
// ошибки несимметрична: показать ленту на пару минут несвежей — мелочь,
// потерять место человека — обидно.
const FEED_CACHE_TTL = 300_000
// Город в ключе кэша наравне с языком: без этого человек, выбравший
// Нови-Сад, при возврате на главную видел бы сохранённую ленту Белграда.
let feedCache = { lang: null, city: null, items: [], total: 0, scroll: 0, fetchedAt: 0 }

// Фон страницы (--bg в styles.css). Держим тут же числом: значение
// уходит в meta theme-color, а из CSS-переменной его пришлось бы
// вычитывать через getComputedStyle на каждый вызов.
const PAGE_BG = '#FAFAF9'

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
  // Возвращает заголовок вкладки к общему, если он остался от
  // страницы категории (там он меняется на конкретный раздел —
  // см. CategoryLanding.jsx) — иначе после захода в «Авто» и
  // возврата на главную вкладка так и осталась бы «Авто — ...».
  useEffect(() => {
    document.title = 'PLONK — объявления в Белграде и Сербии'
  }, [])
  const [categories, setCategories] = useState([])
  const [catsLoaded, setCatsLoaded] = useState(false)
  // объявляем до первого обращения: ниже с него начинается состояние ленты
  const savedCity = (() => {
    try { return localStorage.getItem('plonk_city') || '' } catch { return '' }
  })()
  // Возраст здесь намеренно не проверяем.
  //
  // Сохранённая лента — это то, ради чего человек возвращается на своё
  // место, а не в начало. Смотрел объявление три минуты — при возврате
  // должен увидеть тот же экран, а не ленту с нуля.
  //
  // Свежесть при этом не страдает: ниже, если память старше минуты,
  // лента перезагружается в фоне — человек видит своё место сразу, а
  // данные обновляются через мгновение.
  const cached = (feedCache.lang === i18n.language && feedCache.city === savedCity)
    ? feedCache
    : null

  const [listings, setListings] = useState(() => cached?.items || [])
  const [feedLoaded, setFeedLoaded] = useState(() => Boolean(cached?.items.length))
  const [feedError, setFeedError] = useState(false)
  // Ноль из памяти — не повод считать ленту законченной.
  //
  // Подгрузка включается, только если показано меньше, чем всего. Если
  // в памяти total почему-либо оказался нулём, а карточки есть, условие
  // сразу ложно: сторож прокрутки не ставится, и лента замирает
  // навсегда. Обновление страницы чинило — потому и ловилось так
  // редко.
  const [feedTotal, setFeedTotal] = useState(
    () => cached?.total || (cached?.items.length ? cached.items.length + 1 : 0))
  // Какая лента показана: «Все», «Новое», «Даром».
  //
  // Три ленты подряд для четырёх тысяч объявлений выглядели бы жидко, а
  // переключатель честнее: одна лента, три взгляда на неё.
  const [tab, setTab] = useState('all')
  const [loadingMore, setLoadingMore] = useState(false)
  // Подгрузка сама остановилась — показываем кнопку «Показать ещё».
  const [stalled, setStalled] = useState(false)
  const sentinelRef = useRef(null)
  const [cols, setCols] = useState(2)
  // Город по умолчанию — вся Сербия, а не Белград.
  //
  // Раньше в списке стоял Белград, но лента показывала объявления
  // отовсюду: человек видел выбранный город и объявления из Нови-Сада
  // рядом. Пустое значение честно означает «везде».
  //
  // Выбор запоминаем: человек живёт в одном городе, и заставлять его
  // выбирать заново при каждом заходе незачем.
  const [city, setCity] = useState(() => {
    try { return localStorage.getItem('plonk_city') || '' } catch { return '' }
  })

  const chooseCity = useCallback((value) => {
    setCity(value)
    try { localStorage.setItem('plonk_city', value) } catch { /* не беда */ }
  }, [])

  // Город — тоже через ref: обработчик ухода со страницы создаётся один
  // раз и иначе запомнил бы город, выбранный при первой отрисовке.
  const cityRef = useRef(city)
  cityRef.current = city

  // Браузер восстанавливает прокрутку не мгновенно, и шапка успевала
  // развернуться и тут же схлопнуться — при возврате это читалось как рывок.
  // Берём положение прокрутки сразу, а переход включаем только после того,
  // как оно установилось.
  const [collapsed, setCollapsed] = useState(() => (cached?.scroll || window.scrollY) > 48)
  // сколько прокрутки предстоит восстановить — до этого шапку не трогаем
  const lastScroll = useRef(cached?.scroll || 0)
  const [settled, setSettled] = useState(false)
  // слайд выбирается один раз при загрузке страницы (как у Avito) — без автокарусели,
  // иначе цвет статус-бара не успевает за сменой и отстаёт
  const [slide] = useState(() => Math.floor(Math.random() * PROMO_SLIDES.length))
  const [searchOpen, setSearchOpen] = useState(false)
  const { user, loading: authLoading } = useAuth()

  // Статус-бар на iOS 26 Safari больше НЕ управляется theme-color: браузер берёт цвет
  // из background-color липкого элемента у края экрана (наш баннер) в момент отрисовки.
  // Поэтому цвет задаётся через backgroundColor баннера выше, а мета-тег ниже нужен
  // только для Android и старых версий Safari.
  //
  // На десктопе цвет слайда сюда ставить нельзя. Баннера там нет вовсе
  // (.avito-banner{display:none} в медиазапросе), а Safari на macOS
  // красит в theme-color область за краем страницы — ту самую, что
  // видна при резиновой прокрутке. При быстром пролистывании ленты
  // снизу выезжала цветная полоса, а на резком рывке — почти весь
  // экран: синий или фиолетовый, смотря какой слайд выпал при
  // загрузке. Поймал по видео: цвет совпадал с градиентом слайда.
  // На широком экране отдаём фон самой страницы — тогда за краем
  // ровно тот же цвет, что и под лентой, и никакого блока не видно.
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 900px)')
    const apply = () => {
      document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.remove())
      const meta = document.createElement('meta')
      meta.setAttribute('name', 'theme-color')
      meta.setAttribute('content', mq.matches ? PAGE_BG : PROMO_SLIDES[slide].top)
      // Тот же цвет — области потягивания, чтобы при обновлении над
      // шапкой не открывалась белая пустота.
      document.documentElement.style.setProperty('--pull-bg', PROMO_SLIDES[slide].top)
      document.head.appendChild(meta)
    }
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [slide])

  useEffect(() => {
    let ticking = false
    const update = () => {
      ticking = false
      const y = window.scrollY
      // Запоминаем на ходу: к моменту ухода со страницы прокрутка успевает
      // обнулиться, и в память попадал ноль — возврат открывал ленту сверху.
      lastScroll.current = y
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
    api.searchListings({
      lang: i18n.language, limit: PAGE, offset: 0, city: city || undefined,
      ...(tab === 'new' ? { sort: 'new' } : {}),
      ...(tab === 'free' ? { only_free: true } : {}),
    })
      .then((res) => {
        setListings(res.items || [])
        setFeedTotal(res.total || 0)
        setFeedError(false)
        fetchedAtRef.current = Date.now()
      })
      .catch(() => { setListings([]); setFeedError(true) })
      .finally(() => setFeedLoaded(true))
  ), [i18n.language, city, tab])

  // Подгружаем следующую порцию, когда человек дочитал до низа —
  // иначе лента обрывается на двенадцатом объявлении.
  // Сколько уже запрошено. Ведём отдельно от длины списка.
  //
  // Раньше следующая порция запрашивалась по длине списка, а показанное
  // повторно мы отсеиваем. Стоило порядку в ленте измениться — скажем,
  // объявления перенесли в другие разделы, — сервер начинал отдавать
  // уже показанное, после отсева список не рос, и подгрузка просила ту
  // же порцию снова и снова. На экране это «Загружаем», которое дёргается
  // и никогда не кончается. Так и сломалось.
  const asked = useRef(0)
  // Сколько порций подряд пришло без единой новой карточки.
  const empty = useRef(0)

  const loadMore = useCallback(() => {
    if (loadingMore) return
    setLoadingMore(true)
    const from = Math.max(asked.current, listings.length)
    asked.current = from + PAGE
    api.searchListings({ lang: i18n.language, limit: PAGE, offset: from, city: city || undefined })
      .then((res) => {
        // Пусто — дальше просить нечего: помечаем, что лента кончилась,
        // иначе наблюдатель будет дёргать подгрузку до бесконечности.
        if (!(res.items || []).length) setFeedTotal(listings.length)
        setListings((prev) => {
          const have = new Set(prev.map((l) => l.id))
          const fresh = (res.items || []).filter((l) => !have.has(l.id))
          // Ничего нового не пришло — значит дальше и не появится.
          //
          // Сервер может отдавать уже показанное: порядок в ленте
          // сместился, объявления перенесли в другие разделы. Тогда
          // после отсева список не растёт, а подгрузка просит порцию за
          // порцией без конца — на экране «Загружаем», которое дёргается
          // и никогда не кончается. Ровно так лента и сломалась.
          if (!fresh.length) {
            // Пустая порция сама по себе не конец ленты.
            //
            // Так я сначала и сделал — и лента обрывалась на второй
            // сотне вместо четырёх тысяч: после переноса объявлений
            // порядок смещается, и порция целиком из уже показанного
            // вполне попадается в середине. Смещение при этом растёт,
            // так что следующая порция принесёт новое.
            //
            // Концом считаем три пустых порции подряд: случайный
            // повтор так переживём, а настоящий конец поймаем.
            empty.current += 1
            if (empty.current >= 3) {
              // Останавливаемся, но не насмерть.
              //
              // Раньше здесь ставился feedTotal = показанному, и
              // подгрузка отключалась до перезагрузки страницы. Если
              // три пустых порции попались посреди ленты — а после
              // ночных чисток порядок смещается, и это возможно —
              // человек оставался с обрывком и без всякого способа
              // это исправить, кроме F5.
              //
              // Теперь показываем кнопку: он нажмёт и продолжит.
              setStalled(true)
            }
            return prev
          }
          empty.current = 0
          setStalled(false)
          return [...prev, ...fresh]
        })
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [i18n.language, listings.length, loadingMore, city])

  useEffect(() => {
    if (!feedLoaded || listings.length >= feedTotal) return
    const el = sentinelRef.current
    if (!el) return

    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '1400px' },   // см. ниже
      // Подгружаем сильно заранее — примерно за два экрана до конца.
      //
      // 600px это меньше одного экрана телефона: человек долистывал до
      // низа и упирался в пустоту, пока летел запрос. На неспешной сети
      // это заметная пауза, а прокрутка при этом ещё и останавливается.
      // Полтора экрана запаса хватает, чтобы следующая порция успела
      // приехать незаметно.
    )
    io.observe(el)
    return () => io.disconnect()
  }, [feedLoaded, listings.length, feedTotal, loadMore])

  useEffect(() => {
    // при возврате лента уже есть — перезагрузка сбросила бы её к двенадцати
    // объявлениям и снова уронила прокрутку. Но только пока кэш не устарел —
    // иначе тот же снимок остался бы навсегда.
    if (cached?.items.length && Date.now() - cached.fetchedAt < FEED_CACHE_TTL) return
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
        city: cityRef.current,
        items: itemsRef.current,
        total: totalRef.current,
        scroll: lastScroll.current || window.scrollY,
        fetchedAt: fetchedAtRef.current,
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
  const fetchedAtRef = useRef(cached?.fetchedAt || 0)
  useEffect(() => { itemsRef.current = listings }, [listings])
  useEffect(() => { totalRef.current = feedTotal }, [feedTotal])
  useEffect(() => { langRef.current = i18n.language }, [i18n.language])

  // Прокрутку тут не трогаем: этим занимается App.jsx, один на всё
  // приложение. Здесь когда-то было своё восстановление со своим
  // сохранённым местом — два механизма спорили за прокрутку, перебивали
  // друг друга разными значениями, и при возврате свайпом человека
  // кидало то не туда, то в самое начало. Сохранённая лента (items,
  // total) остаётся: без неё список сбросился бы к первой странице, и
  // возвращаться было бы некуда.

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
            {/* Пока идёт проверка токена, user ещё null — раньше тут
                на секунду показывалось «Войти» текстом, а затем резко
                сжималось в кружок аватара: заметный скачок макета при
                каждом обновлении у любого вошедшего человека. Нейтральный
                кружок того же размера, что и у итогового аватара, не
                дёргается ни в одну сторону, каким бы ни был исход. */}
            {authLoading
              ? <div className="avatar-mini skeleton" />
              : user
                ? (
                  <div className={user.role === 'seller_business' ? 'avatar-mini is-company' : 'avatar-mini'}>
                    {user.avatar_url
                      ? <img src={user.avatar_url} alt="" />
                      : (user.company_name || user.display_name || '?').trim().charAt(0).toUpperCase()}
                  </div>
                )
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
                    <select value={city} onChange={(e) => chooseCity(e.target.value)} aria-label={t('post.city')}>
                      <option value="">{t('search.all_cities')}</option>
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
          /* Раздел без выбора гасим: три объявления обещают выбор и
             не дают его. Но заходить не мешаем — вдруг человек ищет
             именно это. */
          <Link
            key={cat.id}
            to={hasLanding(cat.slug) ? `/c/${cat.slug}` : `/search?category=${cat.slug}`}
            className={`cat-tile-2row${cat.ready === false ? ' soon' : ''}`}
          >
            <div className="cat-tile-2row-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
            <div className="cat-tile-2row-glyph"><CategoryArt slug={cat.slug} /></div>
          </Link>
        )
        if (!catsLoaded) {
          return (
            <div className="cat-rows">
              <div className="cat-row"><CategorySkeletons count={5} /></div>
              <div className="cat-row"><CategorySkeletons count={5} /></div>
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
        {/* Три взгляда на одну ленту.
            Названия короткие нарочно: с длинными «Рекомендации» третья
            вкладка заезжала под переключатель колонок — увидел на
            наброске. */}
        <div className="feed-tabs">
          {[['all', t('feed.tab_all')],
            ['new', t('feed.tab_new')],
            ['free', t('feed.tab_free')]].map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? 'feed-tab active' : 'feed-tab'}
              onClick={() => { if (tab !== key) { setTab(key); asked.current = 0 } }}
            >
              {label}
            </button>
          ))}
        </div>
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
          ? <CardSkeletons count={cols === 2 ? 4 : 2} large={cols === 1} />
          : listings.map((l, i) => (
              <ListingCard key={l.id} listing={l} large={cols === 1} priority={i < 4} />
            ))}
      </div>
      {feedLoaded && listings.length === 0 && (
        feedError
          ? <LoadError onRetry={() => { setFeedLoaded(false); loadFeed() }} />
          : <p className="empty-hint">{t('common.no_listings')}</p>
      )}

      <div ref={sentinelRef} className="feed-sentinel">
        {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}

        {/* Подгрузка встала — даём человеку кнопку.
            Раньше в этом случае лента просто заканчивалась, и починить
            это можно было только обновлением страницы. Человек при этом
            не знает, что объявления есть: для него лента кончилась. */}
        {stalled && !loadingMore && (
          <button
            className="feed-more"
            onClick={() => { empty.current = 0; setStalled(false); loadMore() }}
          >
            {t('feed.show_more')}
          </button>
        )}
      </div>
    </div>

      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />
    </PullToRefresh>
  )
}
