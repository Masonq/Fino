import SlidePill from '../components/SlidePill'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { withoutRemoved } from '../utils/removedListings'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import CategoryFields, { fieldsKeyFor } from '../components/CategoryFields'
import ListingCard from '../components/ListingCard'
import { CardSkeletons } from '../components/Skeletons'
import { CITIES, cityLabel } from '../data/cities'
import { ROOMS_IN } from '../data/landings'
import { MODE_WORDS } from '../data/modeWords'
import { LoadError } from '../components/OfflineNotice'
import { useAuth } from '../context/AuthContext'
import useStickyColumn from '../hooks/useStickyColumn'
import useHideOnScroll from '../hooks/useHideOnScroll'

const SORTS = [
  { key: 'relevance', labelKey: 'search.sort_relevance' },
  { key: 'new', labelKey: 'search.sort_new' },
  { key: 'cheap', labelKey: 'search.sort_cheap' },
  { key: 'expensive', labelKey: 'search.sort_expensive' },
]

const PAGE = 20

// Найденное держим между заходами, как на главной и на странице раздела.
//
// Без этого возврат из объявления перезапрашивал выдачу с первой
// страницы: человек листал результаты, открывал карточку, возвращался —
// и оказывался наверху короткого списка. Ключ — сам запрос: у разных
// запросов разные результаты, общее хранилище перепутало бы их.
let searchCache = { key: null, items: [], total: 0, fetchedAt: 0 }

const DEAL_ALIAS = {
  'flats-rent': ['flats', { mode: 'rent' }],
  'flats-sale': ['flats', { mode: 'sale' }],
  'daily-rent': ['flats', { mode: 'daily' }],
  'flats-studio': ['flats', { chip: 'studio' }],
}

export default function Search() {
  const topHidden = useHideOnScroll()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  // Липкая колонка фильтров — тот же хук, что на лендинге и в профиле
  // (CSS sticky не срабатывает в Safari). Отступ 92px — высота липкой
  // строки поиска сверху плюс воздух, иначе два прибитых блока
  // слипаются.
  const sidebar = useStickyColumn(92)
  const [subscribed, setSubscribed] = useState(false)
  const [subscribedId, setSubscribedId] = useState(null)
  // показали результаты по исправленному запросу (опечатка) — говорим об этом прямо над выдачей
  const [corrected, setCorrected] = useState(null)
  // подписка на этот поиск: из шапки результатов и из пустого результата («Сообщить, когда появится»)
  const toggleSubscribe = async () => {
                if (!user) { navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname + window.location.search)}`); return }
                // Повторное нажатие — снять слежение, не завести
                // ещё одну (бэкенд её всё равно не завёл бы второй
                // раз, но раньше и снять было нельзя не уходя в
                // профиль).
                if (subscribed && subscribedId) {
                  try {
                    await api.deleteSavedSearch(subscribedId)
                    setSubscribed(false)
                    setSubscribedId(null)
                  } catch { /* оставляем как было */ }
                  return
                }
                try {
                  const res = await api.saveSearch({
                    q: text.trim() || undefined,
                    category_slug: category || undefined,
                    price_min: priceMin || undefined,
                    price_max: priceMax || undefined,
                    city: city || undefined,
                    // Раньше терялись при сохранении — подписка на «Снять»
                    // присылала уведомления и про «Купить» тоже, а «только
                    // с фото» вообще не учитывалась (хотя бэкенд её умеет
                    // проверять).
                    deal_type: fields.mode || undefined,
                    with_photo: withPhoto || undefined,
                  })
                  setSubscribed(true)
                  setSubscribedId(res.id)
                } catch { /* уже сохранён или лимит */ }
  }
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  const [text, setText] = useState(params.get('q') || '')
  const [categories, setCategories] = useState([])
  // Пустой массив неотличим от «ещё не пришло» — нужен свой явный
  // флаг, иначе не на что опереться, решая, показывать ли скелетон
  // строки подкатегорий или уже настоящую (пустую) строку.
  const [catsLoaded, setCatsLoaded] = useState(false)
  // Начальное значение — из хранилища.
  //
  // Ключ (сам запрос) здесь ещё не собран: он считается ниже, и сверять
  // с ним нельзя — четвёртый раз за сегодня спотыкаюсь об этот порядок.
  // Поэтому берём как есть, а если запрос окажется другим, загрузка
  // ниже сразу перезапишет список.
  const [items, setItems] = useState(() => searchCache.items || [])
  const [total, setTotal] = useState(0)
  // Подгрузка сама остановилась — показываем кнопку «Показать ещё».
  const [stalled, setStalled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  const [retry, setRetry] = useState(0)
  const [showFilters, setShowFilters] = useState(false)
  const [cols, setCols] = useState(2)
  const [sortOpen, setSortOpen] = useState(false)

  // фильтры
  const [category, setCategory] = useState(params.get('category') || '')
  const [priceMin, setPriceMin] = useState(params.get('price_min') || '')
  const [priceMax, setPriceMax] = useState(params.get('price_max') || '')
  const [city, setCity] = useState(params.get('city') || '')
  const [withPhoto, setWithPhoto] = useState(params.get('with_photo') === '1')
  const [sort, setSort] = useState(params.get('sort') || 'relevance')

  // Ответы на вопросы раздела: «снять или купить», «легковые или мото».
  const [fields, setFields] = useState({
    mode: params.get('mode') || '',
    chip: params.get('chip') || '',
  })
  // «Аренда квартир», «Продажа квартир», «Студии», «Посуточная аренда» — это не отдельные разделы, а тип сделки
  // у квартир: открываем «Квартиры» с нужной вкладкой («Снять надолго» и т. д.). Раньше вкладка не горела, а
  // подразделы дублировали вкладки отдельным рядом чипов.
  useEffect(() => {
    const a = DEAL_ALIAS[category]
    if (a) { setCategory(a[0]); setFields((f) => ({ ...f, ...a[1] })) }
  }, [category])

  const inputRef = useRef(null)



  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([])).finally(() => setCatsLoaded(true))
  }, [])

  const query = useMemo(() => {
    const p = { lang: i18n.language, limit: PAGE, offset: 0, sort }
    if (text.trim()) p.q = text.trim()
    if (category) p.category_slug = category
    // «Купить/Снять/Посуточно», «Ищу работу/Ищу сотрудника» — структурный
    // атрибут (attributes.deal_type), не текстовый поиск: раньше словом
    // «аренда» находило и «ищу квартиру в аренду», не только тех, кто
    // реально сдаёт.
    if (fields.mode) p.deal_type = fields.mode
    // У «2 комнаты» и подобных структурного поля пока нет — идёт как
    // extra_terms с синонимами, а не приклеенное к тексту поиска.
    // Комнаты — по полю объявления «Комнат», а не по словам в тексте (словами «3+» находились и однушки)
    const ROOM_CHIPS = { rooms1: ROOMS_IN[1], rooms2: ROOMS_IN[2], rooms3: [...ROOMS_IN[3], ...ROOMS_IN['4+']], studio: ROOMS_IN.studio }
    const groups = []
    if (fields.chip && ROOM_CHIPS[fields.chip]) p.attr_eq = JSON.stringify({ rooms: ROOM_CHIPS[fields.chip] })
    else if (fields.chip && MODE_WORDS[fields.chip]) groups.push(MODE_WORDS[fields.chip].join('|'))
    if (groups.length) p.extra_terms = groups.join(';;')
    if (priceMin) p.price_min = priceMin
    if (priceMax) p.price_max = priceMax
    if (city.trim()) p.city = city.trim()
    if (withPhoto) p.with_photo = true
    return p
  }, [text, category, priceMin, priceMax, city, withPhoto, sort, fields, i18n.language])

  // поиск с задержкой, чтобы не дёргать сервер на каждую букву;
  // при первом открытии экрана ждать незачем — запрашиваем сразу
  const firstRun = useRef(true)
  useEffect(() => {
    // Тот же класс утечки, что уже нашли и починили на странице
    // категории и на странице объявления — просто самое частое место
    // для него: любая смена фильтра или категории — один и тот же
    // маршрут /search, тот же компонент. loaded раньше выставлялся
    // только в true (при получении ответа) — сбросить в false в
    // начале нового запроса, до самого fetch, забыли. Проверил
    // настоящим переходом: карточка «iPhone 13 Pro» (категория
    // «Телефоны») оставалась видна ещё 50мс+ после выбора «Ноутбуки»
    // в фильтре, хотя это уже совсем другая категория. Сбрасываем
    // сразу, а не внутри setTimeout — иначе те же 350мс задержки
    // ощущались бы как повисшая старая выдача, а не как загрузка.
    // Вернулись к тому же запросу — показываем найденное сразу и
    // перезапрашиваем, только если оно уже несвежее. Иначе человек
    // видел бы пустой экран на месте выдачи, которую только что листал.
    // Пять минут, как на главной.
    //
    // Минуты было мало: человек ищет коляску, открывает объявление,
    // читает, возвращается — и поиск начинается заново, хотя он никуда
    // не уходил. Здесь это обиднее, чем в ленте: запрос он набирал
    // руками.
    const FRESH = 300_000
    if (searchCache.key === JSON.stringify(query)
        && searchCache.items.length
        && Date.now() - searchCache.fetchedAt < FRESH) {
      setItems(searchCache.items)
      setTotal(searchCache.total)
      setLoaded(true)
      return
    }

    setLoaded(false)
    const wait = firstRun.current ? 0 : 350
    firstRun.current = false
    const id = setTimeout(() => {
      setLoading(true)
      api.searchListings(query)
        .then((res) => {
          setItems(res.items || [])
          setTotal(res.total || 0)
          setCorrected(res.corrected || null)
          setError(false)
          searchCache = {
            key: JSON.stringify(query),
            items: res.items || [],
            total: res.total || 0,
            fetchedAt: Date.now(),
          }
        })
        .catch(() => { setItems([]); setTotal(0); setError(true) })
        .finally(() => { setLoading(false); setLoaded(true) })
    }, wait)
    return () => clearTimeout(id)
  }, [query, retry])

  // синхронизируем адрес страницы, чтобы результат можно было переслать ссылкой
  useEffect(() => {
    const next = {}
    if (text.trim()) next.q = text.trim()
    if (category) next.category = category
    if (priceMin) next.price_min = priceMin
    if (priceMax) next.price_max = priceMax
    if (city.trim()) next.city = city.trim()
    if (withPhoto) next.with_photo = '1'
    if (sort !== 'new') next.sort = sort
    // «Купить/Снять/Посуточно» и подобные — тоже влияют на выдачу, но
    // раньше в адрес не попадали: ссылкой на такой поиск нельзя было
    // поделиться и он не переживал обновление страницы.
    if (fields.mode) next.mode = fields.mode
    if (fields.chip) next.chip = fields.chip
    setParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, category, priceMin, priceMax, city, withPhoto, sort, fields])

  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef(null)

  // Сколько уже запрошено — отдельно от длины списка: показанное
  // повторно мы отсеиваем, и при сместившемся порядке подгрузка иначе
  // просит одну и ту же порцию без конца (см. Home.jsx).
  const asked = useRef(0)
  const empty = useRef(0)

  // force — нажатие на «Показать ещё»: setStalled(false) в обработчике
  // до этой функции не доходит, у неё своё замыкание со stalled = true.
  const loadMore = useCallback((force = false) => {
    if (loadingMore || (stalled && !force)) return
    setLoadingMore(true)
    const from = Math.max(asked.current, items.length)
    asked.current = from + PAGE
    api.searchListings({ ...query, offset: from })
      .then((res) => setItems((prev) => {
        // Подгруженное тоже кладём в хранилище: иначе при возврате
        // список схлопнется к первой порции, и место потеряется.
        // Отсеиваем уже показанное — как в ленте на главной: когда
        // подгрузка накладывается на обычную загрузку списка, одни и те
        // же карточки дописываются второй раз.
        const have = new Set(prev.map((l) => l.id))
        const fresh = (res.items || []).filter((l) => !have.has(l.id))
        // Ничего нового — дальше не просим (см. Home.jsx): иначе
        // подгрузка идёт без конца, а список стоит на месте.
        if (!fresh.length) {
          // Три пустых порции подряд — тогда конец (см. Home.jsx).
          empty.current += 1
          if (empty.current >= 3) {
            // Останавливаемся, но не насмерть — как на главной.
            //
            // Раньше здесь ставился total = показанному, и подгрузка
            // отключалась до перезагрузки страницы. Человек оставался с
            // обрывком выдачи и без всякого способа это исправить,
            // притом что запрос он набирал руками.
            setStalled(true)
          }
          return prev
        }
        empty.current = 0
        setStalled(false)
        const grown = [...prev, ...fresh]
        searchCache = {
          key: JSON.stringify(query),
          items: grown,
          total: searchCache.total,
          fetchedAt: searchCache.fetchedAt || Date.now(),
        }
        return grown
      }))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [query, items.length, loadingMore, stalled])

  // подгрузка при прокрутке вместо кнопки
  useEffect(() => {
  // Пока лента остановлена, наблюдатель отключён.
  //
  // Иначе выходил вечный качель: приходили три порции без нового,
  // показывалась кнопка «Показать ещё» — но наблюдатель висел на том
  // же месте (запас 1400 точек, метка всегда в зоне) и тут же звал
  // подгрузку снова. Кнопка сменялась на «Загружаем…», порция опять
  // приходила пустой, кнопка возвращалась — и так по кругу, раз в
  // полсекунды, с дёрганьем низа ленты.
    if (!loaded || stalled || items.length === 0 || items.length >= total) return
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
  }, [loaded, stalled, items.length, total, loadMore])

  const resetFilters = () => {
    setCategory(''); setPriceMin(''); setPriceMax(''); setCity(''); setWithPhoto(false); setSort('new')
  }

  // Полоса подкатегорий над лентой. Отдельной страницы под категорию не
  // заводим: так подкатегории работают одинаково и с главной, и из списка
  // категорий, и не добавляют лишнего шага тем, кому нужна вся категория.
  //
  // Ищем на любой глубине: с третьим уровнем («Телефоны» → «Apple»)
  // поиск «сам или прямой ребёнок» не находил ничего — пропадали и ряд
  // подразделов, и фильтры раздела, и выбранный пункт в списке.
  const trail = (() => {
    const walk = (nodes, path) => {
      for (const n of nodes || []) {
        const next = [...path, n]
        if (n.slug === category) return next
        const deeper = walk(n.children, next)
        if (deeper) return deeper
      }
      return null
    }
    return (category && walk(categories, [])) || []
  })()
  // Корень — для фильтров раздела. Ряд плиток — соседи выбранного, как
  // и было: у «Телефонов» это подразделы «Электроники», у «Apple» —
  // остальные марки, а «Все» возвращает на уровень выше.
  const current = trail[0]
  const rowParent = trail.length >= 2 ? trail[trail.length - 2] : current
  const subs = rowParent?.children || []
  const label = (c) => c.name?.[i18n.language] || c.name?.ru

  const activeCount = [category, priceMin, priceMax, city, withPhoto ? '1' : ''].filter(Boolean).length

  // Чипы применённых фильтров над результатами — можно снять один
  // конкретный, не открывая панель фильтров. Категорию сюда не кладём:
  // она и так видна активной плиткой в sub-row чуть выше.
  const fieldsKey = fieldsKeyFor(current?.slug || category)
  const activeChips = []
  if (fields.mode && fieldsKey) {
    activeChips.push({ id: 'mode', text: t(`fields.${fieldsKey}.${fields.mode}`), onRemove: () => setFields((f) => ({ ...f, mode: '' })) })
  }
  if (fields.chip && fieldsKey) {
    activeChips.push({ id: 'chip', text: t(`fields.${fieldsKey}.${fields.chip}`), onRemove: () => setFields((f) => ({ ...f, chip: '' })) })
  }
  if (priceMin || priceMax) {
    const text = priceMin && priceMax ? `${priceMin}–${priceMax}`
      : priceMin ? `${t('search.price_from')} ${priceMin}`
      : `${t('search.price_to')} ${priceMax}`
    activeChips.push({ id: 'price', text, onRemove: () => { setPriceMin(''); setPriceMax('') } })
  }
  if (city) {
    activeChips.push({ id: 'city', text: cityLabel(city, i18n.language), onRemove: () => setCity('') })
  }
  if (withPhoto) {
    activeChips.push({ id: 'photo', text: t('search.only_photo'), onRemove: () => setWithPhoto(false) })
  }

  return (
    <div className="search-page-full">
      <div className={`search-topbar${topHidden ? ' is-hidden' : ''}`}>
        <button className="search-back" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="search-field">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            ref={inputRef}
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t('search.placeholder_full')}
            autoComplete="off"
          />
          {text && (
            <button className="search-clear" onClick={() => { setText(''); inputRef.current?.focus() }} aria-label={t('actions.clear')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
        <button
          className={activeCount ? 'search-filter-btn on' : 'search-filter-btn'}
          onClick={() => setShowFilters((v) => !v)}
          aria-label={t('misc.filters')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
          {activeCount > 0 && <span className="filter-badge">{activeCount}</span>}
        </button>
      </div>

      <div className="search-body">
        {/* Распорка на месте прибитой колонки: .search-body — flex, и
            когда сайдбар уходит в position:fixed, результаты
            расползаются на его место, а при возврате прыгают обратно. */}
        {sidebar.stuck && <div className="search-sidebar-spacer" aria-hidden="true" />}
        <aside
          ref={sidebar.ref}
          className={`search-sidebar${sidebar.className}`}
          style={sidebar.style}
        >
          <div className={showFilters ? 'filters-panel open' : 'filters-panel'}>
            <div className="post-field">
              <label>{t('search.category')}</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="">{t('search.all_categories')}</option>
                {/* Подкатегории отбиты отступом: в выпадающем списке вложенность
                    иначе не видна, и «Телефоны» читались бы как ещё одна
                    категория вровень с «Электроникой». */}
                {categories.map((c) => [
                  <option key={c.id} value={c.slug}>{c.name?.[i18n.language] || c.name?.ru}</option>,
                  ...(c.children || []).flatMap((sub) => [
                    <option key={sub.id} value={sub.slug}>
                      {'\u00A0\u00A0\u00A0'}{sub.name?.[i18n.language] || sub.name?.ru}
                    </option>,
                    ...(sub.children || []).map((deep) => (
                      <option key={deep.id} value={deep.slug}>
                        {'\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0'}{deep.name?.[i18n.language] || deep.name?.ru}
                      </option>
                    )),
                  ]),
                ])}
              </select>
            </div>

            <div className="post-field-row">
              <div className="post-field">
                <label>{t('search.price_from')}</label>
                <input type="number" inputMode="decimal" pattern="[0-9]*" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} placeholder="0" />
              </div>
              <div className="post-field">
                <label>{t('search.price_to')}</label>
                <input type="number" inputMode="decimal" pattern="[0-9]*" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} placeholder="—" />
              </div>
            </div>

            <div className="post-field">
              <label>{t('search.city')}</label>
              <select value={city} onChange={(e) => setCity(e.target.value)}>
                <option value="">{t('search.all_cities')}</option>
                {CITIES.map((c) => <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>)}
              </select>
            </div>

            <label className="filter-check">
              <input type="checkbox" checked={withPhoto} onChange={(e) => setWithPhoto(e.target.checked)} />
              {t('search.only_photo')}
            </label>

            {activeCount > 0 && (
              <button className="filters-reset" onClick={resetFilters}>{t('actions.reset_filters')}</button>
            )}
          </div>

          {/* Поля именно этого раздела: у квартиры «снять или купить», у
              машины — вид техники. Общая форма с ценой на эти вопросы не
              отвечает, и человек уходит листать всё подряд. */}
          <CategoryFields
            slug={current?.slug || category}
            value={fields}
            onChange={setFields}
          />

          {/* Категория ещё не выбрана — подкатегорий точно не будет,
              категории тут ни при чём (subs всегда пустой без current).
              Раньше скелетон рисовался при любом !catsLoaded, даже для
              обычного текстового поиска без категории — три вымышленные
              «таблетки» появлялись и тут же пропадали в пустоту, ведь
              настоящие чипы для такого поиска никогда не должны были
              возникнуть. */}
          {category && !catsLoaded && (
            <div className="sub-row">
              <div className="sub-chip skeleton" style={{ width: 90 }} />
              <div className="sub-chip skeleton" style={{ width: 70 }} />
              <div className="sub-chip skeleton" style={{ width: 100 }} />
            </div>
          )}
          {subs.filter((x) => !DEAL_ALIAS[x.slug]).length > 0 && (
            <div className="sub-row">
              <button
                className={category === rowParent.slug ? 'sub-chip active' : 'sub-chip'}
                onClick={() => setCategory(rowParent.slug)}
              >
                {t('search.all_in_category')}
              </button>
              {subs.filter((x) => !DEAL_ALIAS[x.slug]).map((sub) => (
                <button
                  key={sub.id}
                  className={category === sub.slug ? 'sub-chip active' : 'sub-chip'}
                  onClick={() => setCategory(sub.slug)}
                >
                  {label(sub)}
                </button>
              ))}
            </div>
          )}
        </aside>

        <div className="search-results">
          {activeChips.length > 0 && (
            <div className="active-filters-row">
              {activeChips.map((c) => (
                <button key={c.id} className="active-filter-chip" onClick={c.onRemove}>
                  {c.text}
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
              ))}
              {(activeChips.length > 1 || activeCount > 0) && (
                <button className="active-filter-chip clear-all" onClick={() => { resetFilters(); setFields({ mode: '', chip: '' }) }}>
                  {t('actions.reset_filters')}
                </button>
              )}
            </div>
          )}

          {corrected && items.length > 0 && (
            <div className="search-corrected">
              {t('search.corrected_pre')} «{text.trim()}» {t('search.corrected_mid')} <button type="button" onClick={() => setText(corrected)}>«{corrected}»</button>
            </div>
          )}

          {/* итог поиска крупно, как приветствие на главной: что искали и сколько нашлось */}
          {loaded && text.trim() && items.length > 0 && (
            <div className="ph-text search-hero">
              <span className="ph-kicker">{t('search.hero_for', { q: text.trim() })}</span>
              <h1 className="ph-title">{t('search.hero_n', { count: total })}</h1>
            </div>
          )}

          <div className="results-head">
        <div className="results-head-left">
          {/* Раньше тут же был счётчик «Найдено: N» — при добавлении
              «По релевантности» ряд стал слишком тесным дважды подряд.
              Убрали, не подбирая очередной хрупкий компромисс по
              ширине: число найденного видно и так — по самой длине
              ленты под этой строкой. */}
          <div className="sort-dd">
            <button className="sort-dd-btn" onClick={() => setSortOpen((v) => !v)}>
              {t(SORTS.find((s) => s.key === sort)?.labelKey)}
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="m6 9 6 6 6-6" /></svg>
            </button>
            {sortOpen && (
              <>
                <div className="sort-dd-backdrop" onClick={() => setSortOpen(false)} />
                <div className="sort-dd-menu">
                  {SORTS.map((s) => (
                    <button
                      key={s.key}
                      className={sort === s.key ? 'sort-dd-item active' : 'sort-dd-item'}
                      onClick={() => { setSort(s.key); setSortOpen(false) }}
                    >
                      {t(s.labelKey)}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
        <div className="results-head-right">
          {(text.trim() || category || priceMin || priceMax || city) && (
            <button
              className={subscribed ? 'save-search done' : 'save-search'}
              onClick={toggleSubscribe}
            >
              {subscribed ? t('saved.done') : t('saved.subscribe')}
            </button>
          )}
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
      </div>

      <div className={cols === 2 ? 'infinite-grid' : 'infinite-list'}>
        {!loaded
          ? <CardSkeletons count={cols === 2 ? 4 : 2} large={cols === 1} />
          : withoutRemoved(items).map((l, i) => (
              <ListingCard key={l.id} listing={l} large={cols === 1} priority={i < 4} />
            ))}
      </div>

      {loaded && !loading && items.length === 0 && (
        error
          ? <LoadError onRetry={() => { setLoaded(false); setRetry((n) => n + 1) }} />
          : (
            <div className="empty-state search-empty">
              <div className="search-empty-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round">
                  <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /><path d="M8.5 11h5" />
                </svg>
              </div>
              <p className="search-empty-title">{t('search.empty_title')}</p>
              <p className="empty-hint">{t('search.empty_hint')}</p>
              {/* ничего не нашлось — не тупик: подписка на поиск, пришлём уведомление, как только такое появится */}
              {(text.trim() || category || priceMin || priceMax || city) && (
                <button type="button" className={`empty-notify${subscribed ? ' done' : ''}`} onClick={toggleSubscribe}>
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{subscribed ? <path d="M20 6 9 17l-5-5" /> : <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></>}</svg>
                  {subscribed ? t('search.notify_done') : t('search.notify_me')}
                </button>
              )}
              {(activeChips.length > 0 || text.trim()) && (
                <button
                  className="empty-reset"
                  onClick={() => { resetFilters(); setFields({ mode: '', chip: '' }); setText('') }}
                >
                  {t('actions.reset_filters')}
                </button>
              )}
              {/* Тупик хуже всего: человек ничего не нашёл и уходит.
                  Разделы под рукой — можно продолжить оттуда. */}
              {categories.length > 0 && (
                <div className="search-empty-cats">
                  <span className="search-empty-label">{t('search.empty_browse')}</span>
                  <div className="search-empty-chips">
                    {categories.slice(0, 8).map((c) => (
                      <Link key={c.id} className="search-empty-chip" to={`/c/${c.slug}`}>
                        {c.name?.[i18n.language] || c.name?.ru}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
      )}

      <div ref={sentinelRef} className="feed-sentinel">
        {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}

        {/* Подгрузка встала — даём кнопку, как на главной. */}
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
      </div>
    </div>
  )
}
