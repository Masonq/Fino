import SlidePill from '../components/SlidePill'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { cityLabel } from '../data/cities'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import CategoryArt from '../components/CategoryArt'
import ListingCard from '../components/ListingCard'
import JobsLanding from '../components/JobsLanding'
import { longestWordWidth, oneLineWidth, tileFor } from '../utils/artFit'
import TileArt from '../components/TileArt'
import { CardSkeletons } from '../components/Skeletons'
import { LANDINGS, landingFor } from '../data/landings'
import { MODE_WORDS } from '../data/modeWords'
import { CAR_MODELS, CAR_MODEL_OTHER } from '../data/carBrands'
import useStickyColumn from '../hooks/useStickyColumn'

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
// Картинка-шапка раздела. Предметы стоят по краям, середина пустая —
// туда ложатся название и поиск. Градиент остаётся запасным вариантом:
// если картинка не загрузилась, шапка не станет белым пятном.
const HERO_FALLBACK = {
  'real-estate': 'linear-gradient(135deg, #8E9BE8 0%, #A6B1F0 55%, #C9D0F8 100%)',
  auto: 'linear-gradient(135deg, #2E7CC4 0%, #4D97D8 55%, #A8D2F0 100%)',
  electronics: 'linear-gradient(135deg, #4FB8A8 0%, #6FCCBC 55%, #B8E8DF 100%)',
  'home-garden': 'linear-gradient(135deg, #C87A52 0%, #DB9A72 55%, #F0C8A8 100%)',
  fashion: 'linear-gradient(135deg, #E88A6B 0%, #F2A488 55%, #FBD0BE 100%)',
  kids: 'linear-gradient(135deg, #E092A0 0%, #EFAEB8 55%, #F8D5DB 100%)',
  'hobby-sport': 'linear-gradient(135deg, #4C9E52 0%, #68B86E 55%, #ABDCAE 100%)',
  pets: 'linear-gradient(135deg, #E0A85C 0%, #E8B878 55%, #F5DCB4 100%)',
  beauty: 'linear-gradient(135deg, #B99BC4 0%, #CBB2D4 55%, #E6D8EC 100%)',
  services: 'linear-gradient(135deg, #7E93A8 0%, #9AACBE 55%, #CAD6E0 100%)',
  jobs: 'linear-gradient(135deg, #3B4B94 0%, #5A6CB0 55%, #A8B4DA 100%)',
  business: 'linear-gradient(135deg, #7C8794 0%, #98A2AE 55%, #CCD2D8 100%)',
}

// Кэш результатов поиска внутри раздела — по одному на каждый slug,
// не единый на все разделы (иначе объявления одной категории
// подставлялись бы при возврате в другую). См. подробный комментарий
// в самом компоненте, у cached/cacheFresh.
const LANDING_CACHE_TTL = 60_000
const landingCache = {}

/** Плитки по образцу Авито: короткие названия — по три в ряд, длинные — парами; не больше 3 рядов, дальше «Все категории →». */
function gridRows(list, name, narrowText, maxRows = 3) {
  const wide = (n) => oneLineWidth(n) > narrowText
  const narrowQ = list.filter((x) => !wide(name(x))), wideQ = list.filter((x) => wide(name(x)))
  const rows = []
  while ((narrowQ.length || wideQ.length) && rows.length < maxRows) {
    const nextNarrow = narrowQ.length && (!wideQ.length || list.indexOf(narrowQ[0]) < list.indexOf(wideQ[0]))
    if (nextNarrow && narrowQ.length >= 3) rows.push(narrowQ.splice(0, 3))
    else if (!nextNarrow && wideQ.length >= 2) rows.push(wideQ.splice(0, 2))
    else rows.push([...(nextNarrow ? narrowQ : wideQ).splice(0, 1), ...(nextNarrow ? wideQ : narrowQ).splice(0, 1)])
  }
  if ((narrowQ.length || wideQ.length) && rows.length) { const last = rows[rows.length - 1]; last[last.length - 1] = null }
  return rows
}

/** «Работа» — свой экран по образцу Авито (как в приложении), остальные разделы — как раньше. */
export default function CategoryLanding() {
  const { slug } = useParams()
  return slug === 'jobs' ? <JobsLanding /> : <CategoryLandingPage />
}

function CategoryLandingPage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

  // Возврат из объявления сбрасывал всю страницу раздела к началу —
  // фильтры и уже найденные объявления терялись, прокрутка прыгала
  // наверх, хотя человек только что листал результаты внизу. У главной
  // ленты то же самое чинили раньше отдельно (feedCache в Home.jsx) —
  // тот же принцип, но с привязкой к конкретному разделу: у категорий
  // разное содержимое, один общий кэш для всех перепутал бы их.
  const cached = landingCache[slug]
  // Возраст решает, обновлять ли данные, но не показывать ли их.
  //
  // Раньше сохранённый список считался годным только минуту: человек
  // смотрел объявление дольше, возвращался — список сбрасывался, страница
  // становилась короткой, и возвращать прокрутку было уже некуда, он
  // оказывался наверху. Именно на это и пожаловались.
  //
  // Теперь список показывается всегда, если он есть, а по возрасту
  // решаем только, перечитать ли его с сервера — это происходит следом
  // и незаметно.
  const cacheFresh = Boolean(cached)
  const cacheStale = cached && Date.now() - cached.fetchedAt >= LANDING_CACHE_TTL
  const restoringFromCache = useRef(Boolean(cacheFresh && cached.searched))
  // Тот самый настоящий виновник — см. подробный комментарий у самого
  // места использования, в эффекте сброса при смене slug.
  const skipFirstReset = useRef(Boolean(cacheFresh && cached.searched))

  const [category, setCategory] = useState(null)

  // Липкость сайдбара — общий хук, тот же, что и на странице профиля
  // (src/hooks/useStickyColumn.js): там же и разбор, почему считаем
  // положение сами, а не одним CSS position:sticky, и зачем нужно
  // третье состояние у нижнего края колонки.
  //
  // Сайдбара нет в разметке, пока не загрузилась категория — поэтому
  // передаём это признаком готовности, чтобы хук переподписался и
  // замерил уже существующий блок.
  const sidebar = useStickyColumn(28, Boolean(category))

  const [fresh, setFresh] = useState([])
  const [freshLoading, setFreshLoading] = useState(true)
  // Число объявлений — из того же поиска, что откроется по кнопке (с
  // городом). Счётчик из дерева разделов города не знает: обещал «3»,
  // а в Белграде находилось одно.
  const [liveCount, setLiveCount] = useState(null)
  const [deal, setDeal] = useState(() => cacheFresh ? cached.deal : '')
  const [values, setValues] = useState(() => cacheFresh ? cached.values : {})
  const [text, setText] = useState(() => cacheFresh ? cached.text : '')
  const [showAllSubs, setShowAllSubs] = useState(false)
  // по образцу Авито: верх «Недвижимости» (шторки «Комнаты» и «Цена», кнопка фильтров) и ширина колонки плиток
  const [reSheet, setReSheet] = useState(null)
  const [moreFilters, setMoreFilters] = useState(false)
  const gridRef = useRef(null)
  const [gridW, setGridW] = useState(() => Math.min(window.innerWidth, 620) - 24)
  useLayoutEffect(() => {
    const el = gridRef.current
    if (!el || typeof ResizeObserver === 'undefined') return undefined
    // ширина содержимого — без внутренних отступов сетки (иначе плитки вылезали за край на 24 точки)
    const ro = new ResizeObserver(() => { const cs = getComputedStyle(el); const w = Math.floor(el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)); if (w > 0) setGridW(w) })
    ro.observe(el)
    return () => ro.disconnect()
  })

  // category в зависимостях — сайдбар не существует в DOM, пока
  // категория не загрузилась; без этого обработчик мог бы читать
  // getBoundingClientRect() у ещё не отрисованного элемента.
  // Результаты показываются прямо тут, под фильтрами, вместо перехода
  // на отдельную страницу поиска — раньше «Показать объявления» уводил
  // на /search с почти той же вёрсткой, и это читалось как две разные,
  // плохо связанные страницы.
  const [results, setResults] = useState(() => cacheFresh ? cached.results : [])
  const [resultsTotal, setResultsTotal] = useState(() => cacheFresh ? cached.resultsTotal : 0)
  const [searched, setSearched] = useState(() => cacheFresh ? cached.searched : false)
  const [searching, setSearching] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const PAGE = 20
  const resultsRef = useRef(null)

  // Раздел верхнего уровня и схема формы размещения — по ним подраздел
  // получает свои поля (см. landingFor). Схема привязана к слагу, чтобы
  // на миг после перехода не показать поля прошлого раздела.
  const [rootSlug, setRootSlug] = useState(null)
  const [schema, setSchema] = useState(null)
  // Пока корень не известен — только заливка, без запроса за чужой картинкой.
  const heroSlug = LANDINGS[slug] ? slug : rootSlug
  const landing = landingFor(slug, rootSlug, schema?.slug === slug ? schema.fields : null)

  // Заголовок вкладки браузера — раньше document.title вообще нигде на
  // сайте программно не менялся, все страницы показывали один и тот
  // же общий заголовок из index.html. Для страницы конкретного раздела
  // это упущенная возможность: по запросу вроде «объявления авто
  // сербия» страница с собственным «Авто — объявления в Сербии»
  // ранжируется куда лучше, чем общая главная с тем же заголовком,
  // что и у всех остальных разделов. Отдельным эффектом, не в самой
  // загрузке ниже — там category достаётся асинхронно, а name нужен
  // именно когда он уже есть.
  useEffect(() => {
    if (!category) return
    const name = category.name?.[i18n.language] || category.name?.ru
    document.title = `${name} — объявления в Сербии | PLONK`
  }, [category, i18n.language])

  useEffect(() => {
    // Раньше all.find(...) смотрел только на корневой уровень массива —
    // работало, пока на страницу категории попадали только по
    // корневым слагам. Теперь плитка подраздела тоже может вести на
    // /c/:slug (сама эта правка, для подразделов вроде gaming/trucks —
    // они не корневые, а вложены в electronics/auto), и плоский find
    // их находить не будет вовсе, category останется null. Ищем по
    // всему дереву, на любую глубину, не только по первому уровню.
    const findBySlug = (nodes, root) => {
      for (const node of nodes) {
        if (node.slug === slug) { setRootSlug((root || node).slug); return node }
        if (node.children?.length) {
          const found = findBySlug(node.children, root || node)
          if (found) return found
        }
      }
      return null
    }
    api.getCategories()
      .then((all) => setCategory(findBySlug(all)))
      .catch(() => setCategory(null))

    // Схема нужна только подразделу: у раздела поля свои. Не пришла —
    // останется одна цена, страница от этого не ломается.
    if (!LANDINGS[slug]) {
      api.getCategorySchema(slug)
        .then((res) => setSchema({ slug, fields: res?.attribute_schema || [] }))
        .catch(() => setSchema({ slug, fields: [] }))
    }

    // Проверили настоящим замером: старая карточка («Свежие
    // объявления» прошлого раздела) оставалась видна ещё 30мс+ после
    // клика на новый раздел, пропадала только когда приходил ответ
    // сервера (~300мс) — тот же класс утечки, что и с values/deal
    // выше, просто визуальный, не в самом запросе. setFresh([]) тут
    // же, синхронно с переходом — не оставляем чужую картинку висеть,
    // пока грузится настоящая. freshLoading — не просто пустота (та
    // тоже дёргано: блок разом исчезает и через мгновение появляется
    // снова, сдвигая макет) — скелетон той же формы держит место.
    setFresh([])
    setLiveCount(null)
    setFreshLoading(true)
    const savedCity = (() => {
      try { return localStorage.getItem('plonk_city') || '' } catch { return '' }
    })()
    api.searchListings({ category_slug: slug, limit: 8, lang: i18n.language,
                         city: savedCity || undefined })
      .then((res) => { setFresh(res.items || []); setLiveCount(res.total ?? null) })
      .catch(() => setFresh([]))
      .finally(() => setFreshLoading(false))

    // Переход на другой раздел (напр. по «Все категории») не должен
    // оставлять открытым режим результатов прошлого раздела.
    //
    // НО: этот же эффект срабатывает и на самом первом монтировании
    // компонента — включая возврат из объявления, когда searched/values/
    // deal/text уже восстановлены из landingCache (см. инициализацию
    // состояний выше). Без skipFirstReset этот блок тут же стирал бы
    // восстановленное состояние тем же самым циклом — то самое, что
    // не удавалось поймать несколько заходов подряд: сам кэш работал
    // верно, просто этот соседний, куда более старый и никак с ним не
    // связанный сброс перезаписывал его сразу следом. Нашли только по
    // видео, чтением кода не давалось.
    if (skipFirstReset.current) {
      skipFirstReset.current = false
    } else {
    setSearched(false)
    // То же самое для самого модального окна «Все категории» — раньше
    // не сбрасывался. Клик по подразделу С СОБСТВЕННЫМИ детьми (см.
    // .subs-modal-row ниже) теперь ведёт на /c/:slug того подраздела,
    // а не сразу в поиск — но React Router переиспользует один и тот
    // же компонент при смене параметра :slug в том же самом маршруте,
    // не пересоздаёт его заново. showAllSubs оставался true из старой
    // страницы, и то же самое модальное окно просто продолжало висеть
    // поверх новой страницы, молча подменив список на детей нового
    // раздела — с не изменившимся заголовком «Все категории», будто
    // это всё ещё прежняя категория. Человек физически не видел
    // саму новую страницу (баннер, поиск, «Показать объявления») —
    // только кнопка «назад» браузера это раскрывала. Нашли по видео.
    setShowAllSubs(false)
    // Тот же самый класс бага, только опаснее — не просто визуальный
    // сбой, а тихая порча самого поиска: значения полей фильтра
    // (values — марка/год/пробег и т.п.) и тип сделки (deal) тоже
    // жили в состоянии компонента и точно так же переживали переход
    // между /c/:slug. Прямой переход с «Авто» (выбрана марка Audi) на
    // «Запчасти» (клик по плитке подраздела, тот же компонент
    // переиспользуется) — на «Запчасти» отправлялся запрос с
    // brand=Audi, хотя там нет и не может быть такого поля в схеме,
    // и человек его на этой странице не выбирал вовсе. Проверил
    // настоящим запросом (перехватил URL) — подтверждено. text (поле
    // поиска на самой странице раздела) сбрасываю туда же для
    // единообразия — по той же причине могло бы утечь в extra_terms.
    setValues({})
    setDeal('')
    setText('')
    }
  }, [slug, i18n.language])

  // Плитка подраздела задаёт свой слаг категории вместо родительского —
  // нужен и на первом запуске поиска (buildQuery), и на догрузке
  // (loadMore), поэтому держим его в состоянии, а не только в замыкании
  // клика.
  const [activeCategorySlug, setActiveCategorySlug] = useState(() => cacheFresh ? cached.activeCategorySlug : slug)

  const buildQuery = (categorySlug = activeCategorySlug) => {
    const params = { category_slug: categorySlug, lang: i18n.language, limit: PAGE, offset: 0 }
    if (text.trim()) params.q = text.trim()

    // Город — тот же, что выбран на главной.
    //
    // Здесь фильтра по городу не было вовсе: человек выбирал Нови-Сад,
    // заходил в «Мебель» и снова видел всю Сербию. Выбор один на весь
    // сайт, и странице раздела незачем его переспрашивать.
    const city = (() => {
      try { return localStorage.getItem('plonk_city') || '' } catch { return '' }
    })()
    if (city) params.city = city

    // «Купить/Снять/Посуточно» — структурный атрибут (attributes.deal_type),
    // отбирает по полю, а не по словам в тексте: раньше «Снять» словом
    // «аренда» находило и «ищу квартиру в аренду» — чужую заявку, а не
    // те, что реально сдают.
    if (deal) params.deal_type = deal

    // «2 комнаты» и т.п. структурного поля пока не имеют — уходит как
    // extra_terms с синонимами, так же, как на обычном /search.
    const ROOMS_TO_CHIP = { '1': 'rooms1', '2': 'rooms2', '3': 'rooms3', '4+': 'rooms3' }
    const groups = []
    // Остальные поля раздела (год, пробег, коробка передач и т.п.) —
    // общий механизм attr_eq/attr_range (см. listings.py): раньше
    // такое поле либо не фильтровало вовсе (было в интерфейсе, но
    // бэкенд его не принимал — так нашёлся нерабочий «Год выпуска» у
    // авто), либо под каждое заводили свой именованный параметр.
    const attrEq = {}
    const attrRange = {}
    Object.entries(values).forEach(([key, value]) => {
      if (!value) return
      if (key === 'rooms') {
        const chip = ROOMS_TO_CHIP[value]
        if (chip && MODE_WORDS[chip]) groups.push(MODE_WORDS[chip].join('|'))
        return
      }
      // «Другая» — это «не нашлось в списке», не реальное значение
      // фильтра; отправлять его как есть значило бы искать буквальную
      // марку «Другая» и получать пустую выдачу.
      if ((key === 'brand' || key === 'model') && value === CAR_MODEL_OTHER) return
      if (key === 'brand' || key === 'model') { params[key] = value; return }

      // *_min/*_max — поле типа range. price — уже готовая пара
      // параметров на самой колонке цены (работает и без этого
      // механизма), остальные — в общий числовой диапазон.
      const rangeMatch = key.match(/^(.+)_(min|max)$/)
      if (rangeMatch) {
        const [, baseKey, bound] = rangeMatch
        if (baseKey === 'price') { params[key] = value; return }
        attrRange[baseKey] = attrRange[baseKey] || [null, null]
        attrRange[baseKey][bound === 'min' ? 0 : 1] = value
        return
      }

      attrEq[key] = value
    })
    if (groups.length) params.extra_terms = groups.join(';;')
    if (Object.keys(attrEq).length) params.attr_eq = JSON.stringify(attrEq)
    if (Object.keys(attrRange).length) params.attr_range = JSON.stringify(attrRange)
    return params
  }

  // Принимает необязательный слаг подраздела: плитка подраздела кликает
  // сюда напрямую с sub.slug, а не сначала кладёт его в state — иначе
  // из-за асинхронности setState поиск на этом же клике ушёл бы со
  // старым слагом.
  const search = (categorySlug = slug) => {
    setActiveCategorySlug(categorySlug)
    setSearching(true)
    setSearched(true)
    setShowAllSubs(false)
    requestAnimationFrame(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    api.searchListings(buildQuery(categorySlug))
      .then((res) => { setResults(res.items || []); setResultsTotal(res.total || 0) })
      .catch(() => { setResults([]); setResultsTotal(0) })
      .finally(() => setSearching(false))
  }

  // Прокрутка к результатам при самом первом переходе в режим поиска —
  // requestAnimationFrame в search() этот случай не ловит, потому что
  // блок результатов ещё не существовал в DOM в момент вызова.
  //
  // При восстановлении из кэша (возврат из объявления) searched уже
  // true на самом первом рендере — этот эффект всё равно сработает
  // (зависимость меняется относительно «не было рендера», не только
  // относительно предыдущего значения), и его плавная прокрутка к
  // НАЧАЛУ результатов боролась бы с восстановлением места, на
  // котором человек реально был, — а оно может быть куда ниже.
  // restoringFromCache — само по себе не меняется, но исключает
  // именно тот самый первый рендер после восстановления.
  useEffect(() => {
    if (restoringFromCache.current) return
    if (searched && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [searched])

  // Устаревший список обновляем тихо, уже показав его.
  //
  // Человек при возврате сразу видит то, что листал, и остаётся на своём
  // месте; свежие данные подъезжают следом и меняют разве что порядок в
  // самом низу. Обновляем только первую порцию: если человек долистал
  // далеко, перетряхивать всё под ним нельзя — страница подпрыгнет.
  const refreshed = useRef(false)
  useEffect(() => {
    if (refreshed.current || !cacheStale || !cached?.searched) return
    refreshed.current = true
    api.searchListings(buildQuery(cached.activeCategorySlug || slug))
      .then((res) => {
        if ((res.items || []).length) {
          setResults((prev) => (prev.length > (res.items || []).length ? prev : res.items))
          setResultsTotal(res.total || 0)
        }
      })
      .catch(() => { /* показываем то, что уже есть */ })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Сколько уже запрошено — отдельно от длины списка (см. Home.jsx).
  const asked = useRef(0)
  const empty = useRef(0)

  const loadMore = () => {
    if (loadingMore || results.length >= resultsTotal) return
    setLoadingMore(true)
    const from = Math.max(asked.current, results.length)
    asked.current = from + PAGE
    api.searchListings({ ...buildQuery(activeCategorySlug), offset: from })
      .then((res) => setResults((prev) => {
        // Отсеиваем уже показанное — как в ленте на главной: когда
        // подгрузка накладывается на обычную загрузку списка, одни и те
        // же карточки дописываются второй раз.
        const have = new Set(prev.map((l) => l.id))
        const fresh = (res.items || []).filter((l) => !have.has(l.id))
        // Ничего нового — дальше не просим (см. Home.jsx).
        if (!fresh.length) {
          // Три пустых порции подряд — тогда конец (см. Home.jsx).
          empty.current += 1
          if (empty.current >= 3) setResultsTotal(prev.length)
          return prev
        }
        empty.current = 0
        return [...prev, ...fresh]
      }))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }

  // Пишем в кэш сразу при каждом изменении, а не только в момент ухода
  // со страницы — раньше полагались на pagehide/размонтирование
  // (см. тот же приём в Home.jsx), но это требует точного совпадения
  // по времени между уходом со страницы и тем, что React успел
  // прогнать все эффекты синхронизации к этому моменту. Проще и
  // надёжнее — держать кэш всегда актуальным, без выжидания
  // конкретного события ухода вообще.
  const scrollRef = useRef(cacheFresh ? cached.scroll : 0)
  useEffect(() => {
    const onScroll = () => { scrollRef.current = window.scrollY }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    landingCache[slug] = {
      results, resultsTotal, searched, activeCategorySlug, deal, values, text,
      scroll: scrollRef.current,
      fetchedAt: Date.now(),
    }
  }, [slug, results, resultsTotal, searched, activeCategorySlug, deal, values, text])

  // Прокрутку на момент ухода записываем отдельно, uже поверх готовой
  // записи в кэше — сама прокрутка меняется без остановки, отдельным
  // эффектом на каждое движение её обновлять было бы дорого.
  useEffect(() => {
    const save = () => {
      if (landingCache[slug]) landingCache[slug].scroll = scrollRef.current
    }
    window.addEventListener('pagehide', save)
    return () => { save(); window.removeEventListener('pagehide', save) }
  }, [slug])

  // Прокрутку выставляем до первой отрисовки (useLayoutEffect) — иначе
  // страница на мгновение показывается сверху и лишь потом прыгает на
  // место. Повторяем несколько раз: фото ниже ещё догружаются и слегка
  // меняют высоту страницы, отчего однократно выставленная прокрутка
  // уезжает через долю секунды после того, как её выставили.
  // Своего восстановления прокрутки здесь больше нет.
  //
  // Оно спорило с общим (App.jsx): два механизма ставили прокрутку
  // наперегонки, каждый со своими повторами, и человек видел, как
  // страница дёргается при возврате. Ровно это уже случалось на главной,
  // и лечится так же — механизм должен быть один.
  //
  // Сохранённый список при этом остаётся: без него странице неоткуда
  // взять высоту, и возвращать прокрутку было бы некуда.


  const name = category?.name?.[i18n.language] || category?.name?.ru || ''

  // Раньше кнопка «назад» в шапке жёстко вела на /categories — если
  // человек пришёл сюда с главной (по плитке раздела), «назад» уводил
  // не туда, откуда он пришёл, а на «Все категории»: история браузера
  // росла (Главная → Раздел → Все категории → Раздел → Все категории…),
  // и «назад» с «Все категории» возвращал обратно в этот же раздел —
  // получался замкнутый круг. Тот же приём, что и в ListingDetail.jsx:
  // если есть настоящая история — идём по ней, а не мимо. «Все
  // категории» остаётся запасным для прямых ссылок, где истории нет.
  // Подпись в строке поиска не повторяет название раздела: оно уже
  // написано крупно на картинке под строкой. Вместо этого говорим, где
  // ищем — в выбранном городе или по всей стране. Так сделано у Avito,
  // и это единственное, чего человек по экрану не знает.
  const searchHint = (() => {
    let city = ''
    try { city = localStorage.getItem('plonk_city') || '' } catch { /* не беда */ }
    return city
      ? t('landing.search_city', { city: cityLabel(city, i18n.language) })
      : t('search.placeholder_full')
  })()

  const goBack = () => {
    if (window.history.state?.idx > 0) {
      navigate(-1)
      return
    }
    navigate('/categories', { replace: true })
  }

  // Пока поиск не ответил: без города число из дерева верное — берём
  // его, чтобы цифра не мигала. С городом оно заведомо чужое, поэтому
  // лучше полсекунды без цифры, чем «3», сменяющееся на «1».
  const hasCity = (() => {
    try { return !!localStorage.getItem('plonk_city') } catch { return false }
  })()
  const shownCount = liveCount ?? (hasCity ? 0 : category?.count ?? 0)
  // «Недвижимость» — верх по образцу Авито
  const isRE = slug === 'real-estate'
  const roomsField = landing?.fields?.find((f) => f.key === 'rooms')
  const priceText = values.price_min && values.price_max ? `${values.price_min} – ${values.price_max} €`
    : values.price_min ? `${t('landing.from')} ${values.price_min} €` : values.price_max ? `${t('landing.to')} ${values.price_max} €` : ''

  return (
    <div className="landing">
      {searched && (
        <div className="landing-head plain-head">
          <button className="landing-back" onClick={() => setSearched(false)}
                  aria-label={t('actions.back')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3"
                 strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <h1 className="landing-title">{name}</h1>
        </div>
      )}

      {!searched && (
      <>
      <div className="landing-body">
      {/* Распорка того же размера, что и сайдбар — появляется, только
          когда сайдбар вынут из потока (см. useStickyColumn
          выше), чтобы освободившееся место не схлопывалось и соседняя
          колонка не «прыгала» вбок в момент переключения. */}
      {sidebar.stuck && <div className="landing-sidebar-spacer" aria-hidden="true" />}
      <div
        ref={sidebar.ref}
        className={`landing-sidebar${sidebar.className}`}
        style={sidebar.style}
      >
      {/* Строка «назад + поиск» в одну линию и прилипает к верху,
          как у Avito: пока человек листает подразделы и фильтры,
          поиск всегда под рукой, а не остаётся где-то выше.

          Полупрозрачная с размытием: поверх картинки читается, а
          когда под ней проезжает белый список — не сливается с ним. */}
      <div className="landing-topbar">
        <button className="landing-back on-hero" onClick={goBack}
              aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3"
             strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="search-field">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') search() }}
            placeholder={searchHint}
            autoComplete="off"
          />
          {text && (
            <button className="search-clear" onClick={() => setText('')} aria-label={t('actions.clear')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
      </div>

      {/* По образцу Авито: у «Недвижимости» свой верх (заголовок по центру, сделка, категория, комнаты и цена,
          «Показать» + фильтры); у остальных — вопрос-заголовок, плитки сеткой по 3 (или 2 широких) с «Все категории →»,
          ниже цветная карточка «Найти …». Как в приложении (native/app/c/[slug].tsx). */}
      {isRE ? (
        <div className="re-head">
          <h1 className="re-title">{name}</h1>
          {shownCount > 0 && <div className="re-count">{t('landing.offers', { count: shownCount })}</div>}
          {landing?.deal && (
            <div className="cat-modes landing-deal pill-row re-deal">
              <SlidePill />
              {landing.deal.options.map((opt) => (
                <button key={opt.value} className={`cat-mode${deal === opt.value ? ' on' : ''}`} onClick={() => setDeal(deal === opt.value ? '' : opt.value)}>{t(opt.label)}</button>
              ))}
            </div>
          )}
          <button type="button" className="re-field" onClick={() => setShowAllSubs(true)}>
            <span>{t('landing.re_types')}</span>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
          </button>
          <div className="re-row">
            {roomsField && (
              <button type="button" className={`re-field${values.rooms ? '' : ' ph'}`} onClick={() => setReSheet('rooms')}>
                <span>{values.rooms ? `${t('landing.rooms')}: ${values.rooms}` : t('landing.rooms')}</span>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6" /></svg>
              </button>
            )}
            <button type="button" className={`re-field${priceText ? '' : ' ph'}`} onClick={() => setReSheet('price')}><span>{priceText || t('landing.price')}</span></button>
          </div>
          <div className="re-row">
            <button type="button" className="landing-go re-go" onClick={() => search()}>{shownCount > 0 ? t('landing.show_count', { count: shownCount }) : t('landing.show')}</button>
            <button type="button" className={`re-filter${moreFilters ? ' on' : ''}`} onClick={() => setMoreFilters((v) => !v)} aria-label={t('landing.all_filters')}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 7h10M18 7h2M4 17h4M12 17h8" /><circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /></svg>
            </button>
          </div>
        </div>
      ) : (
        <div className="jl-head lp-head">
          <h1 className="jl-h1">{category?.parent_id ? name : t(`landing_q.${slug}`, { defaultValue: name })}</h1>
          {shownCount > 0 && <div className="lp-count">{t('landing.offers', { count: shownCount })}</div>}
        </div>
      )}
      {!isRE && category?.children?.length > 0 && (() => {
        const subs = category.children
        const labelOf = (x) => x.name?.[i18n.language] || x.name?.ru
        const smallW = Math.floor((gridW - 16) / 3), wideW = Math.floor((gridW - 8) / 2)
        const rows = gridRows(subs, labelOf, smallW - 22)
        return (
          <div className="lp-grid" ref={gridRef}>
            {rows.map((row, r) => (
              <div key={r} className="lp-grid-row">
                {row.map((sub, k) => {
                  const w = row.length === 3 ? smallW : row.length === 2 ? wideW : gridW
                  if (!sub) {
                    return (
                      <button key={`all-${k}`} type="button" className="jl-tile lp-all" style={{ width: w }} onClick={() => setShowAllSubs(true)}>
                        <span className="jl-tile-text" style={{ maxWidth: w - 22 }}>{t('landing.all_categories')}</span>
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 6 6 6-6 6" /></svg>
                      </button>
                    )
                  }
                  const label = labelOf(sub)
                  const text = w < wideW ? w - 22 : Math.min(w - 22, Math.max(longestWordWidth(label) + 4, Math.round(w * 0.5)))
                  const fit = { kind: '', tile: w, text, art: 'big' }
                  return (
                    <button key={sub.id} type="button" className="jl-tile" style={{ width: w }}
                      onClick={() => (sub.children?.length > 0 ? navigate(`/c/${sub.slug}`) : navigate(`/search?category=${sub.slug}`))}>
                      <span className="jl-tile-text" style={{ maxWidth: fit.text }}>{label}</span>
                      <TileArt src={`/cat/${sub.slug}.png`} name={label} fit={fit} />
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        )
      })()}

      {/* Раньше здесь были только фильтры (комнаты, цена) — можно было
            сузить раздел, но не поискать конкретную вещь словом. Теперь
            можно и то, и другое: слово уходит в q вместе с остальными
            отборами. */}

      {/* Первый вопрос делит раздел надвое: без ответа на него
          остальное бессмысленно. */}
      {(!isRE || moreFilters) && (
      <div className="lp-filters">
        <div className="lp-filters-title">{t(`landing_card.${rootSlug || slug}`, { defaultValue: t('landing.refine') })}</div>
      {landing?.deal && !isRE && (
        <div className="cat-modes landing-deal pill-row">
          <SlidePill />
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

      {landing?.fields?.filter((field) => !(isRE && (field.key === 'rooms' || field.key === 'price'))).map((field) => {
        // Модель без выбранной марки бессмысленна — список моделей
        // зависит от того, что выбрано выше, а «Другая» модели не
        // предполагает вовсе.
        if (field.type === 'car-model' && (!values.brand || values.brand === CAR_MODEL_OTHER)) {
          return null
        }
        return (
        <div key={field.key} className="landing-field">
          <div className="landing-label">{t(field.label)}</div>

          {field.type === 'chips' && (
            <div className="cat-chips landing-chips">
              {field.options.map((opt) => {
                // Старые поля (комнаты, размер) — плоский массив строк,
                // значение и подпись совпадают. Новые (коробка передач
                // и подобное) — {value, label}: хранится по-английски
                // («automatic»), показывается переводом. Оба формата
                // рядом, чтобы не переписывать уже работающие поля.
                const value = typeof opt === 'object' ? opt.value : opt
                const label = typeof opt === 'object' ? t(opt.label) : opt
                return (
                  <button
                    key={value}
                    className={`cat-chip${values[field.key] === value ? ' on' : ''}`}
                    onClick={() => setValues({
                      ...values,
                      [field.key]: values[field.key] === value ? '' : value,
                    })}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          )}

          {field.type === 'select' && (
            <select
              className="landing-input landing-select"
              value={values[field.key] || ''}
              onChange={(e) => setValues({
                ...values,
                [field.key]: e.target.value,
                ...(field.key === 'brand' ? { model: '' } : {}),
              })}
            >
              <option value="">{field.placeholder ? t(field.placeholder) : ''}</option>
              {field.options.map((opt) => {
                const value = typeof opt === 'object' ? opt.value : opt
                const label = typeof opt === 'object' ? t(opt.label) : opt
                return <option key={value} value={value}>{label}</option>
              })}
            </select>
          )}

          {field.type === 'car-model' && (
            CAR_MODELS[values.brand] ? (
              <select
                className="landing-input landing-select"
                value={values.model || ''}
                onChange={(e) => setValues({ ...values, model: e.target.value })}
              >
                <option value="">{t('landing.model_placeholder')}</option>
                {CAR_MODELS[values.brand].map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
                <option value={CAR_MODEL_OTHER}>{t('landing.model_other')}</option>
              </select>
            ) : (
              <input
                className="landing-input"
                placeholder={t('landing.model_placeholder')}
                value={values.model || ''}
                onChange={(e) => setValues({ ...values, model: e.target.value })}
              />
            )
          )}

          {field.type === 'text' && (
            <input
              className="landing-input"
              placeholder={field.hint
                // «Например, iPhone 13» годится «Электронике» и «Телефонам»,
                // но не «Играм» и не «Ноутбукам»: у подраздела свой пример,
                // а где его нет — нейтральная подсказка.
                ? t([`${field.hint}_${slug}`, LANDINGS[slug] ? field.hint : `${field.hint}_any`])
                : ''}
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
        )
      })}

      <button className="landing-go" onClick={() => search()}>
        {shownCount > 0
          ? t('landing.show_count', { count: shownCount })
          : t('landing.show')}
      </button>
      </div>
      )}
      </div>

      <div className="landing-main">
      {/* Пока категория (а вместе с ней — список подразделов) ещё не
          пришла, на её месте ничего не было вовсе — блок появлялся
          целиком одним скачком, стоило данным дойти, и «Свежие
          объявления» ниже резко уезжали вниз (замерил — 354px за
          один кадр). Скелетон той же сетки (2 колонки, те же 104px на
          плитку) держит место заранее — придут данные раньше или
          позже, соседние блоки не двигаются. Шесть плиток — самое
          частое число подразделов; у категорий с меньшим числом
          настоящих плиток скелетон будет чуть выше финального блока,
          это меньшее зло по сравнению с прежним скачком со всей
          высоты разом. */}
      {!category && (
        <div className="landing-subs">
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="landing-sub skeleton" key={i} />
          ))}
        </div>
      )}
      {/* Подразделы: если отвечать на вопросы нечем, человек всё равно
          видит, что тут есть. Как у Авито — несколько плиток с картинкой
          и «Все категории» последней, а не весь список сразу: длинный
          список подряд читается хуже, чем несколько картинок и явный
          переход дальше. */}
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
                onClick={() => (
                  sub.children?.length > 0
                    ? navigate(`/c/${sub.slug}`)
                    : navigate(`/search?category=${sub.slug}`)
                )}
              >
                {sub.name?.[i18n.language] || sub.name?.ru}
              </button>
            ))}
          </div>
        </div>
      )}

      {reSheet && (
        <div className="re-sheet-layer" onClick={() => setReSheet(null)}>
          <div className="re-sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={reSheet === 'rooms' ? t('landing.rooms') : t('landing.price')}>
            <div className="re-sheet-handle" />
            <div className="re-sheet-head">
              <button type="button" className="re-sheet-close" onClick={() => setReSheet(null)} aria-label={t('actions.close')}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
              <div className="re-sheet-title">{reSheet === 'rooms' ? t('landing.rooms') : `${t('landing.price')}, €`}</div>
              <button type="button" className="re-sheet-clear" onClick={() => setValues(reSheet === 'rooms' ? { ...values, rooms: '' } : { ...values, price_min: '', price_max: '' })}>{t('landing.clear')}</button>
            </div>
            {reSheet === 'rooms' ? (
              <div className="re-sheet-chips">
                {(roomsField?.options || []).map((opt) => {
                  const value = typeof opt === 'object' ? opt.value : opt
                  const label = typeof opt === 'object' ? t(opt.label) : opt
                  const on = values.rooms === value
                  return <button key={value} type="button" className={`re-sheet-chip${on ? ' on' : ''}`} onClick={() => setValues({ ...values, rooms: on ? '' : value })}>{label}</button>
                })}
              </div>
            ) : (
              <div className="re-sheet-price">
                <input inputMode="numeric" placeholder={t('landing.from')} value={values.price_min || ''} onChange={(e) => setValues({ ...values, price_min: e.target.value.replace(/\D/g, '').slice(0, 9) })} />
                <input inputMode="numeric" placeholder={t('landing.to')} value={values.price_max || ''} onChange={(e) => setValues({ ...values, price_max: e.target.value.replace(/\D/g, '').slice(0, 9) })} />
              </div>
            )}
            <button type="button" className="landing-go re-sheet-apply" onClick={() => { setReSheet(null); search() }}>{t('landing.apply')}</button>
          </div>
        </div>
      )}

      {freshLoading && (
        <div className="landing-fresh">
          <h2>{t('landing.fresh')}</h2>
          <div className="feed-grid"><CardSkeletons count={4} /></div>
        </div>
      )}

      {!freshLoading && fresh.length > 0 && (
        <div className="landing-fresh">
          <h2>{t('landing.fresh')}</h2>
          <div className="feed-grid">
            {fresh.map((l, i) => <ListingCard key={l.id} listing={l} priority={i < 4} />)}
          </div>
        </div>
      )}
      </div>
      </div>
      </>
      )}

      {searched && (
        <div className="landing-results" ref={resultsRef}>
          <div className="landing-results-head">
            <span className="results-count">
              {searching && !results.length ? t('search.searching') : `${t('search.found')}: ${resultsTotal}`}
            </span>
          </div>
          {searching && !results.length ? (
            <div className="feed-grid"><CardSkeletons count={4} /></div>
          ) : results.length === 0 ? (
            <div className="empty-state">
              <p className="empty-hint">{t('search.nothing')}</p>
              <button className="empty-reset" onClick={() => setSearched(false)}>
                {t('actions.edit_filters')}
              </button>
            </div>
          ) : (
            <>
              <div className="feed-grid">
                {results.map((l, i) => <ListingCard key={l.id} listing={l} priority={i < 4} />)}
              </div>
              {results.length < resultsTotal && (
                <button className="load-more" disabled={loadingMore} onClick={loadMore}>
                  {loadingMore ? t('actions.loading') : t('actions.show_more')}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
