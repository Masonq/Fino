import SlidePill from '../components/SlidePill'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { withoutRemoved } from '../utils/removedListings'
import TypingHint from '../components/TypingHint'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import { CardSkeletons, CategorySkeletons } from '../components/Skeletons'
import SearchOverlay from '../components/SearchOverlay'
import FilterPanel from '../components/FilterPanel'
import OfflineNotice, { LoadError } from '../components/OfflineNotice'
import { useAuth } from '../context/AuthContext'
import { CITIES, cityLabel, nearestCity } from '../data/cities'
import useFresh from '../hooks/useFresh'
import FreshStories from '../components/FreshStories'
import CategoryArt from '../components/CategoryArt'
import Avatar from '../components/Avatar'
import { hasLanding } from '../data/landings'
import { HOME_TILE, artBoxFor, artLayoutMeasured, catSrc, tileFor as tileForBase } from '../utils/artFit'

// плитки главной — свои размеры (HOME_TILE): ниже и уже, чем внутри разделов
const tileFor = (name) => tileForBase(name, HOME_TILE)
import { useAspect, useTextLines, useTileMeasure } from '../components/TileArt'

// Ширина плитки раздела — как у плиток внутри разделов: длинное слово — широкая, очень длинное — ещё шире
// картинка плитки на телефоне — по её форме (artBox); на компьютере — прежняя сетка (размеры из CSS)
// колонка надписи плитки главной — по точному замеру текста (та же, что у картинки в HomeTileArt)
const homeTileFit = (name, slug, measure) => artLayoutMeasured(name, tileFor(name), slug, measure, tileFor(name).tile - 26).fit

function HomeTileArt({ slug, name }) {
  const ref = useRef(null)
  const aspect = useAspect(catSrc(slug))
  const measure = useTileMeasure()
  const fit = homeTileFit(name, slug, measure)
  const lines = useTextLines(ref, '.cat-tile-2row-label', [name, fit.text, fit.tile])
  const box = artBoxFor(name, fit, slug, measure, lines, aspect)
  // только сама картинка, без запасного контурного значка: нет файла — в плитке ничего (картинки делаются заново)
  return (
    <div ref={ref} className="cat-tile-2row-glyph" style={{ '--art-w': `${box.width}px`, '--art-h': `${box.height}px`, '--art-r': `${box.right}px`, '--art-b': `${box.bottom}px` }}>
      <img className="cat-art" src={catSrc(slug)} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.display = 'none' }} />
    </div>
  )
}

const tileSize = (name) => { const k = tileFor(name).kind; return k ? ` ${k}` : '' }
// крупная картинка или прежняя — если вторая строка названия доходит до места картинки
const artClass = (name) => (tileFor(name).art === 'big' ? '' : ' small-art')

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
// Вкладка тоже в памяти: человек смотрел «Даром», открыл объявление,
// вернулся — и оказывался на «Все». Работа выбора пропадала.
let feedCache = { lang: null, city: null, tab: 'all', items: [], total: 0, scroll: 0, fetchedAt: 0 }

// Своя память у каждой вкладки: карточки, сколько всего и где человек
// остановился.
//
// Без неё случайное смахивание стоило дорого: вернулся на прежнюю
// вкладку, а лента с начала, и всё, что пролистал, потеряно.
let tabCache = {}

// Фон страницы (--bg в styles.css). Держим тут же числом: значение
// уходит в meta theme-color, а из CSS-переменной его пришлось бы
// вычитывать через getComputedStyle на каждый вызов.
const PAGE_BG = '#FAFAF9'


// Шапка без цвета: тот же фон, что у страницы. Цвет в шапке спорил с
// фотографиями в кружках сторис, а они и есть главное, что там есть.
// Цвет шапки берём из переменной темы, а не числом: при тёмной теме
// шапка оставалась светлой полосой над тёмной страницей.
const BRAND = { top: 'var(--bg)', grad: 'none' }

export default function Home() {
  const { t, i18n } = useTranslation()
  const tileMeasureNow = useTileMeasure() // замер надписей плиток разделов (колонка надписи — по нему)
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
  // Вкладку, на которой человек был, определяем здесь же — до ленты:
  // сохранённая лента годится, только если она от той же вкладки.
  const savedTab = (() => {
    try { return sessionStorage.getItem('plonk_feed_tab') || feedCache.tab || 'all' } catch { return feedCache.tab || 'all' }
  })()

  // Вкладка в условии наравне с языком и городом.
  //
  // Без неё случалось так: человек смотрел «Все», открыл объявление,
  // вернулся — страница перезагрузилась, вкладка восстановилась как
  // «Даром» из sessionStorage, а сохранённая лента осталась от «Все».
  // Условие её принимало, и дальше эффект загрузки видел «память
  // свежая» и не запрашивал ничего: под вкладкой «Даром» висели серые
  // заготовки, и снять их можно было только перезагрузкой. Ровно это и
  // было видно на снимке.
  const cached = (feedCache.lang === i18n.language
    && feedCache.city === savedCity
    && feedCache.tab === savedTab)
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
  // Вкладку держим в хранилище страницы, а не только в памяти.
  //
  // Память живёт, пока жива сама страница. А возврат из объявления —
  // особенно свайпом в приложении — нередко перезагружает её целиком, и
  // выбор пропадал: человек смотрел «Даром», вернулся и оказался на
  // «Все».
  const [tab, setTab] = useState(savedTab)
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

  // Предложение подобрать город по месту.
  //
  // Спрашиваем не сразу при заходе: внезапный запрос места пугает, и
  // половина отказывает не глядя. Показываем полоску, и запрос уходит
  // только когда человек сам нажал.
  //
  // Один раз: отказался — больше не пристаём.
  const [askGeo, setAskGeo] = useState(() => {
    try {
      return !localStorage.getItem('plonk_city')
        && !localStorage.getItem('plonk_geo_asked')
    } catch { return false }
  })
  const [geoBusy, setGeoBusy] = useState(false)

  const dismissGeo = useCallback(() => {
    setAskGeo(false)
    try { localStorage.setItem('plonk_geo_asked', '1') } catch { /* не беда */ }
  }, [])

  const detectCity = useCallback(() => {
    if (!navigator.geolocation) { dismissGeo(); return }
    setGeoBusy(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGeoBusy(false)
        const slug = nearestCity(pos.coords.latitude, pos.coords.longitude)
        // Не в Сербии — города не подставляем, показываем всё подряд.
        if (slug) chooseCity(slug)
        dismissGeo()
      },
      () => { setGeoBusy(false); dismissGeo() },
      { timeout: 8000, maximumAge: 600000 },
    )
  }, [chooseCity, dismissGeo])

  // Город — тоже через ref: обработчик ухода со страницы создаётся один
  // раз и иначе запомнил бы город, выбранный при первой отрисовке.
  const cityRef = useRef(city)
  cityRef.current = city

  // Вкладка — по той же причине: обработчик ухода со страницы создаётся
  // один раз и иначе запомнил бы ту, что была при первой отрисовке.
  const tabRef = useRef(tab)
  tabRef.current = tab

  // Браузер восстанавливает прокрутку не мгновенно, и шапка успевала
  // развернуться и тут же схлопнуться — при возврате это читалось как рывок.
  // Берём положение прокрутки сразу, а переход включаем только после того,
  // как оно установилось.
  const [collapsed, setCollapsed] = useState(() => (cached?.scroll || window.scrollY) > 48)
  // сколько прокрутки предстоит восстановить — до этого шапку не трогаем
  const lastScroll = useRef(cached?.scroll || 0)
  const [settled, setSettled] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const stories = useFresh(city, i18n.language)

  // Первый экран открывается одной волной: истории, разделы и лента. Раньше каждый блок появлялся, как только
  // приходил его ответ, — три волны подряд (замер: 1,6 / 2,4 / 2,7 с), страница «дёргалась». Ждём самого
  // медленного, но не дольше 1,6 с: медленный блок догрузится сам. Из кэша (возврат на главную) — сразу.
  const firstScreenReady = stories.items !== null && catsLoaded && feedLoaded
  const [revealed, setRevealed] = useState(firstScreenReady)
  useEffect(() => { if (firstScreenReady) setRevealed(true) }, [firstScreenReady])
  useEffect(() => { const timer = setTimeout(() => setRevealed(true), 1600); return () => clearTimeout(timer) }, [])
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
      meta.setAttribute('content', mq.matches ? PAGE_BG : BRAND.top)
      document.head.appendChild(meta)
    }
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

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


  // Смахивание вбок меняет вкладку.
  //
  // Порядок тот же, что у кнопок: влево — следующая, вправо —
  // предыдущая. Так листают ленты во всех приложениях, и палец сам
  // тянется к этому жесту.
  const TABS = ['all', 'new', 'free']
  const swipe = useRef(null)
  // В какую сторону сменили вкладку: лента уезжает туда же, куда ушёл
  // палец, а новая приезжает с другой стороны. Без этого смена
  // происходит рывком, и непонятно, что случилось.
  const [tabSlide, setTabSlide] = useState(null)
  // Вкладку вернули из памяти: карточки появляются вместе с лентой, и проявлять их второй раз поверх сдвига
  // ленты не нужно — выходило двойное мигание (лента почти пропадала и проступала заново).
  const [fromCache, setFromCache] = useState(false)
  // Куда вернуть прокрутку, когда карточки вкладки уже отрисованы.
  const pendingScroll = useRef(null)
  // Высота ленты на момент смены вкладки.
  //
  // Лента пересоздаётся, её высота падает до нуля, и браузер сам
  // подтягивает страницу вверх — человек видит шапку вместо карточек.
  // Держим прежнюю высоту, пока не приедут новые.
  const [holdHeight, setHoldHeight] = useState(null)
  const gridRef = useRef(null)

  const onTouchStart = (e) => {
    if (e.touches.length !== 1) return
    swipe.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
  }

  const onTouchEnd = (e) => {
    const start = swipe.current
    swipe.current = null
    if (!start) return

    const t = e.changedTouches[0]
    const dx = t.clientX - start.x
    const dy = t.clientY - start.y

    // Не путаем с прокруткой: жест считается боковым, только если по
    // горизонтали прошли заметно дальше, чем по вертикали.
    if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.8) return

    const i = TABS.indexOf(tab)
    const next = dx < 0 ? i + 1 : i - 1
    if (next < 0 || next >= TABS.length) return

    switchTab(TABS[next], dx < 0 ? 'left' : 'right')
  }

  const switchTab = (key, direction) => {
    setHoldHeight(gridRef.current?.offsetHeight || null)

    // Прежнюю вкладку запоминаем целиком: карточки, сколько всего и
    // место прокрутки.
    tabCache[tab] = {
      items: itemsRef.current,
      total: totalRef.current,
      scroll: window.scrollY,
      fetchedAt: fetchedAtRef.current,
    }

    setTabSlide(direction)
    setTab(key)
    // Выбор вкладки запоминаем всегда, а не только при первом заходе на
    // неё. Прежде запись стояла ниже, в ветке «вкладку видим впервые», и
    // возврат на уже просмотренную её не обновлял: в памяти оставалась
    // другая вкладка, а после перезагрузки страница открывалась на ней.
    try { sessionStorage.setItem('plonk_feed_tab', key) } catch { /* не беда */ }

    const saved = tabCache[key]
    if (saved?.items?.length) {
      // Уже смотрели — возвращаем как было, вместе с местом.
      setListings(saved.items)
      setFeedTotal(saved.total)
      setFeedLoaded(true)
      asked.current = saved.items.length
      fetchedAtRef.current = saved.fetchedAt
      // Место вернём после отрисовки — см. эффект ниже.
      //
      // Раньше возвращали сразу: карточки ещё не нарисованы, страница
      // короткая, и человек успевал увидеть её верх, а потом прыжок
      // вниз. Это и читалось как мелькание.
      pendingScroll.current = saved.scroll || 0
      setFromCache(true)
      return
    }

    // Первый заход на вкладку — показываем серые заготовки, пока едет
    // новая лента. Раньше старые карточки висели до последнего и потом
    // резко сменялись новыми: выходил рывок.
    asked.current = 0
    setFromCache(false)
    setListings([])
    setFeedLoaded(false)
    // Метку не снимаем.
    //
    // Раньше снимали через четверть секунды — и карточки
    // перерисовывались без неё, а движение запускалось по второму разу:
    // фотографии проявлялись заново, будто снимок перезагружается.
    //
    // Один проигрыш обеспечивает key на ленте ниже: при смене вкладки
    // браузер создаёт её заново, и движение играет ровно один раз.
  }

  // Возврат на место после отрисовки карточек.
  //
  // useLayoutEffect, а не обычный: он срабатывает до того, как браузер
  // покажет кадр, и человек не видит ни верха страницы, ни прыжка.
  useLayoutEffect(() => {
    // Снимаем удержание, как только приехали карточки.
    //
    // Раньше держали в ссылке — а ссылка не перерисовывает: высота
    // оставалась от прежней, длинной ленты, и под парой карточек зияла
    // пустота во весь экран.
    if (listings.length && holdHeight !== null) setHoldHeight(null)
    if (pendingScroll.current === null) return
    const y = pendingScroll.current
    pendingScroll.current = null
    window.scrollTo(0, y)
  }, [listings, holdHeight])

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

  // force — нажатие на «Показать ещё». setStalled(false) в обработчике
  // до этой функции не доходит: у неё своё замыкание, в котором stalled
  // ещё true, и кнопка молча ничего не делала бы.
  const loadMore = useCallback((force = false) => {
    if (loadingMore || (stalled && !force)) return
    setLoadingMore(true)
    const from = Math.max(asked.current, listings.length)
    asked.current = from + PAGE
    // Отбор тот же, что у первой порции.
    //
    // Раньше подгрузка про вкладку не знала: первая порция приходила
    // «даром», а следующие — обычной лентой. Новое в них было чужое,
    // дубли отсеивались, и лента замирала на двенадцати карточках,
    // хотя всего их сто четыре.
    api.searchListings({
      lang: i18n.language, limit: PAGE, offset: from, city: city || undefined,
      ...(tab === 'new' ? { sort: 'new' } : {}),
      ...(tab === 'free' ? { only_free: true } : {}),
    })
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
  }, [i18n.language, listings.length, loadingMore, stalled, city, tab])

  useEffect(() => {
  // Пока лента остановлена, наблюдатель отключён.
  //
  // Иначе выходил вечный качель: приходили три порции без нового,
  // показывалась кнопка «Показать ещё» — но наблюдатель висел на том
  // же месте (запас 1400 точек, метка всегда в зоне) и тут же звал
  // подгрузку снова. Кнопка сменялась на «Загружаем…», порция опять
  // приходила пустой, кнопка возвращалась — и так по кругу, раз в
  // полсекунды, с дёрганьем низа ленты.
    if (!feedLoaded || stalled || listings.length >= feedTotal) return
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
  }, [feedLoaded, stalled, listings.length, feedTotal, loadMore])

  useEffect(() => {
    // Ничего не грузим, только если на экране уже есть карточки этой
    // вкладки. Прежде условие смотрело на память, а не на экран, и
    // достаточно было памяти от другой вкладки, чтобы загрузка не
    // случилась вовсе — а на экране оставались серые заготовки.
    const showing = itemsRef.current.length > 0

    // при возврате лента уже есть — перезагрузка сбросила бы её к двенадцати
    // объявлениям и снова уронила прокрутку. Но только пока кэш не устарел —
    // иначе тот же снимок остался бы навсегда.
    if (showing && cached?.items.length && feedCache.tab === tab
      && Date.now() - cached.fetchedAt < FEED_CACHE_TTL) return

    // Вкладку восстановили из памяти — грузить нечего.
    //
    // Без этой проверки лента перезагружалась сразу после возврата:
    // карточки сбрасывались к двенадцати, место прокрутки терялось, и
    // память по вкладкам не работала вовсе.
    const saved = tabCache[tab]
    if (showing && saved?.items?.length && Date.now() - saved.fetchedAt < FEED_CACHE_TTL) return

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
        tab: tabRef.current,
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

  return (
    <>
      <OfflineNotice onRetry={loadFeed} />
    <div className="home">
      <div
        className={[
          'avito-banner',
          collapsed ? 'collapsed' : '',
          settled ? '' : 'no-anim',
        ].filter(Boolean).join(' ')}
        style={{
          backgroundColor: BRAND.top,
          backgroundImage: collapsed ? 'none' : BRAND.grad,
        }}
      >
        <div className="avito-toprow">
          {/* Город — слева в строке поиска, как у Avito: поиск и город
              меняют одно и то же, и держать город отдельной плашкой ниже
              было незачем. Это <select> поверх подписи: тап открывает
              системный выбор, а сама строка поиска — по остальной площади. */}
          <div className="avito-search">
            <label className="search-city" aria-label={t('post.city')}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" /></svg>
              <span>{city ? cityLabel(city, i18n.language) : t('search.all_cities')}</span>
              <svg className="search-city-chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8"><path d="m6 9 6 6 6-6" /></svg>
              <select value={city} onChange={(e) => chooseCity(e.target.value)}>
                <option value="">{t('search.all_cities')}</option>
                {CITIES.map((c) => <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>)}
              </select>
            </label>
            <button type="button" className="avito-search-main" onClick={() => setSearchOpen(true)}>
              <TypingHint className="avito-search-hint" />
            </button>
            {/* Фильтры — своя кнопка, не значок внутри строки поиска:
                вложенное «нажимаемое в нажимаемом» недопустимо, а тап по
                значку должен открывать панель, не поиск. */}
            <button type="button" className="avito-search-filter" aria-label={t('misc.filters')}
              data-label={t('misc.find')} onClick={() => setFiltersOpen(true)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
            </button>
          </div>
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
                  <Avatar
                    src={user.avatar_url}
                    name={user.company_name || user.display_name}
                    className={user.role === 'seller_business' ? 'avatar-mini is-company' : 'avatar-mini'}
                  />
                )
                : t('common.login')}
          </Link>
        </div>
      </div>

      {/* Свежие объявления кружками, как сторис, без заголовка: кружки
          с фото говорят сами за себя. Шапка меняется с каждым заходом,
          и в ней видно, что площадка живая. Полоска считается для
          города из строки поиска.

          Лежит ПОСЛЕ липкой шапки, а не внутри неё, и уезжает вверх вместе
          с лентой. Раньше история сидела в шапке и схлопывалась анимацией
          высоты при прокрутке дальше 48 точек: высота страницы менялась
          под пальцем, браузер сдвигал прокрутку, шапка раскрывалась
          обратно — и так по кругу (дрожание на записи экрана). Что липнет,
          не должно менять высоту страницы; что меняет высоту — не липнет. */}
      <div className="promo-collapse">
        <div className="avito-promo-row">
          <FreshStories items={revealed ? stories.items : null} seen={stories.seen} onOpen={stories.markSeen} />
        </div>
      </div>

      {(() => {
        const all = [{ id: '__all', slug: null, isAll: true }, ...categories]
        const top = all.filter((_, i) => i % 2 === 0)
        const bottom = all.filter((_, i) => i % 2 === 1)
        const renderTile = (cat) => cat.isAll ? (
          <Link key="__all" to="/categories" className="cat-tile-2row all">
            <div className="cat-tile-2row-label">{t('common.all')}</div>
            {/* Сетка из четырёх плиток вместо стеклянных кубиков:
                кубики ничего не значили, сетка читается как «все
                разделы» без подписи. */}
            <div className="cat-tile-2row-glyph all-glyph" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3.5" y="3.5" width="7" height="7" rx="2" /><rect x="13.5" y="3.5" width="7" height="7" rx="2" />
                <rect x="3.5" y="13.5" width="7" height="7" rx="2" /><rect x="13.5" y="13.5" width="7" height="7" rx="2" />
              </svg>
            </div>
          </Link>
        ) : (
          /* Раздел без выбора гасим: три объявления обещают выбор и
             не дают его. Но заходить не мешаем — вдруг человек ищет
             именно это. */
          <Link
            key={cat.id}
            to={hasLanding(cat.slug) ? `/c/${cat.slug}` : `/search?category=${cat.slug}`}
            className={`cat-tile-2row${tileSize(cat.name?.[i18n.language] || cat.name?.ru || '')}${artClass(cat.name?.[i18n.language] || cat.name?.ru || '')}${cat.ready === false ? ' soon' : ''}`}
                style={{ '--tile-text': `${homeTileFit(cat.name?.[i18n.language] || cat.name?.ru || '', cat.slug, tileMeasureNow).text}px`, '--tile-w': `${tileFor(cat.name?.[i18n.language] || cat.name?.ru || '').tile}px` }}
          >
            <div className="cat-tile-2row-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
            <HomeTileArt slug={cat.slug} name={cat.name?.[i18n.language] || cat.name?.ru || ''} />
          </Link>
        )
        if (!catsLoaded || !revealed) {
          return (
            <div className="cat-rows">
              <div className="cat-row"><CategorySkeletons count={5} /></div>
              <div className="cat-row"><CategorySkeletons count={5} /></div>
            </div>
          )
        }
        return (
          <div className="cat-rows reveal-in">
            <div className="cat-row">{top.map(renderTile)}</div>
            <div className="cat-row">{bottom.map(renderTile)}</div>
          </div>
        )
      })()}

      {/* Предложение подобрать город по месту.
          Стоит над лентой, а не всплывает окном: человек сперва видит
          объявления и только потом решает, сужать ли их до своего
          города. */}
      {askGeo && (
        <div className="geo-ask">
          <span className="geo-ask-text">{t('feed.geo_ask')}</span>
          <button className="geo-ask-yes" onClick={detectCity} disabled={geoBusy}>
            {geoBusy ? t('actions.loading') : t('feed.geo_yes')}
          </button>
          <button className="geo-ask-no" onClick={dismissGeo}>{t('feed.geo_no')}</button>
        </div>
      )}

      <div className="feed-head-row">
        {/* Три взгляда на одну ленту.
            Названия короткие нарочно: с длинными «Рекомендации» третья
            вкладка заезжала под переключатель колонок — увидел на
            наброске. */}
        <div className="feed-tabs">
          {/* Плашка под активной вкладкой переезжает с лёгкой пружиной — видно, куда переключился */}
          <span className="feed-tabs-pill" aria-hidden="true" style={{ transform: `translateX(${['all', 'new', 'free'].indexOf(tab) * 100}%)` }} />
          {[['all', t('feed.tab_all')],
            ['new', t('feed.tab_new')],
            ['free', t('feed.tab_free')]].map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? 'feed-tab active' : 'feed-tab'}
              onClick={() => {
                if (tab === key) return
                const to = ['all', 'new', 'free'].indexOf(key)
                const from = ['all', 'new', 'free'].indexOf(tab)
                switchTab(key, to > from ? 'left' : 'right')
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="col-toggle pill-row">
          <SlidePill />
          <button className={cols === 2 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(2)} aria-label={t('misc.cols_2')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /></svg>
          </button>
          <button className={cols === 1 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(1)} aria-label={t('misc.cols_1')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
          </button>
        </div>
      </div>

      {/* Жест на самой ленте, а не на всей странице: иначе смахивание
          по плиткам разделов, которые и так листаются вбок, меняло бы
          вкладку заодно. */}
      <div
        key={tab}
        ref={gridRef}
        style={holdHeight ? { minHeight: holdHeight } : undefined}
        className={[
          cols === 2 ? 'infinite-grid' : 'infinite-list',
          tabSlide ? `slide-${tabSlide}` : '',
          fromCache ? 'from-cache' : '',
        ].filter(Boolean).join(' ')}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        {!feedLoaded || !revealed
          ? <CardSkeletons count={cols === 2 ? 4 : 2} large={cols === 1} />
          : withoutRemoved(listings).map((l, i) => <ListingCard key={l.id} listing={l} large={cols === 1} priority={i < 4} />)}
      </div>
      {feedLoaded && revealed && listings.length === 0 && (
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
            onClick={() => { empty.current = 0; setStalled(false); loadMore(true) }}
          >
            {t('feed.show_more')}
          </button>
        )}
      </div>
    </div>

      <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />
      <FilterPanel open={filtersOpen} onClose={() => setFiltersOpen(false)} city={city} onCity={chooseCity} />
    </>
  )
}
