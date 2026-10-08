import { Routes, Route, useLocation, useNavigationType, useParams } from 'react-router-dom'
import { Suspense, lazy, useEffect, useLayoutEffect, useRef } from 'react'
import Home from './pages/Home'
import Search from './pages/Search'
import CategoryLanding from './pages/CategoryLanding'

// Страница раздела — заново при каждом разделе: без ключа React переиспользовал её, и найденное, выбранный
// подраздел и кэш прошлого раздела переезжали в новый («Запчасти» сначала показывали 78 чужих объявлений).
function CategoryLandingPage() {
  const { slug } = useParams()
  return <CategoryLanding key={slug} />
}
import ListingDetail from './pages/ListingDetail'
import NotFound from './pages/NotFound'
import { CITIES } from './data/cities'

// Раздел в городе: /novi-sad/c/namestaj. Сюда приводит поиск по запросу
// «nameštaj Novi Sad» — человек должен увидеть тот же раздел, уже с этим
// городом, что поисковик видит на этом адресе. Город запоминаем так же,
// как при выборе вручную: раздел, лента и поиск берут его оттуда.
function CityCategoryPage() {
  const { city, slug } = useParams()
  if (!CITIES.some((c) => c.slug === city)) return <NotFound />
  try { localStorage.setItem('plonk_city', city) } catch { /* приватный режим — откроется без города */ }
  return <CategoryLanding key={`${city}/${slug}`} />
}

// Остальные страницы — по требованию.
//
// Раньше всё приложение уезжало в один файл на 808 КБ, и человек,
// открывший одну карточку из рекламы, ждал, пока догрузятся служебный
// раздел, чаты, подача объявления и всё прочее, чем он не собирался
// пользоваться. На мобильном интернете это разница между «открылось» и
// «крутится».
//
// Сразу грузятся только страницы первого захода: главная, объявление,
// раздел, поиск. Всё остальное подгружается, когда человек туда идёт —
// это доли секунды, и он их не замечает.
const PostAd = lazy(() => import('./pages/PostAd'))
const MapSearch = lazy(() => import('./pages/MapSearch'))
const Categories = lazy(() => import('./pages/Categories'))
const ChatScreen = lazy(() => import('./pages/ChatScreen'))
const Storefront = lazy(() => import('./pages/Storefront'))
const StorefrontDiscover = lazy(() => import('./pages/Storefront').then((m) => ({ default: m.StorefrontDiscover })))
const StorefrontManage = lazy(() => import('./pages/StorefrontManage'))
const ShopsFeed = lazy(() => import('./pages/ShopsFeed'))
const ShopEditor = lazy(() => import('./pages/ShopEditor'))
const ShopsCabinet = lazy(() => import('./pages/ShopsCabinet'))
const AdminShops = lazy(() => import('./pages/ShopsCabinet').then((m) => ({ default: m.AdminShops })))
const JobResponses = lazy(() => import('./pages/JobResponses'))
const MyJobResponses = lazy(() => import('./pages/JobResponses').then((m) => ({ default: m.MyJobResponses })))
const ComingSoon = lazy(() => import('./pages/ComingSoon'))
const Favorites = lazy(() => import('./pages/Favorites'))
const BlockedUsers = lazy(() => import('./pages/BlockedUsers'))
const InviteFriend = lazy(() => import('./pages/InviteFriend'))
const Notifications = lazy(() => import('./pages/Notifications'))
const ListingDashboard = lazy(() => import('./pages/ListingDashboard'))
const WaitingReviews = lazy(() => import('./pages/WaitingReviews'))
const TgPost = lazy(() => import('./pages/TgPost'))
const TgMy = lazy(() => import('./pages/TgMy'))
const LegalDoc = lazy(() => import('./pages/LegalDoc'))
const Chats = lazy(() => import('./pages/Chats'))
const Login = lazy(() => import('./pages/Login'))
const Profile = lazy(() => import('./pages/Profile'))
const SellerProfile = lazy(() => import('./pages/SellerProfile'))
const MyListings = lazy(() => import('./pages/MyListings'))
const AdminAudit = lazy(() => import('./pages/AdminAudit'))
const AdminJobs = lazy(() => import('./pages/AdminJobs'))
const EditProfile = lazy(() => import('./pages/EditProfile'))
const Enter = lazy(() => import('./pages/Enter'))
const AdminSupport = lazy(() => import('./pages/AdminSupport'))
const AdminFlaggedChats = lazy(() => import('./pages/AdminFlaggedChats'))
const Support = lazy(() => import('./pages/Support'))
const Volunteer = lazy(() => import('./pages/Volunteer'))
const AdminVolunteers = lazy(() => import('./pages/AdminVolunteers'))
const AdminTeamChats = lazy(() => import('./pages/AdminTeamChats'))
const AdminSettings = lazy(() => import('./pages/AdminSettings'))
const AdminStats = lazy(() => import('./pages/AdminStats'))
const AdminUsers = lazy(() => import('./pages/AdminUsers'))
const AdminUser = lazy(() => import('./pages/AdminUser'))
const AdminAlerts = lazy(() => import('./pages/AdminAlerts'))
const Moderation = lazy(() => import('./pages/Moderation'))
const EditListing = lazy(() => import('./pages/EditListing'))
const SavedSearches = lazy(() => import('./pages/SavedSearches'))
const History = lazy(() => import('./pages/History'))
import { AuthProvider } from './context/AuthContext'
import { FavoritesProvider } from './context/FavoritesContext'
import { rememberListPage } from './utils/lastList'
import Island from './components/Island'
import ConfirmHost from './components/ConfirmHost'
import BottomNav from './components/BottomNav'
import { Toaster } from 'sonner'
import Footer from './components/Footer'
import TopNav from './components/TopNav'
import { GuideArticle, GuidesList } from './pages/Guides'
import AdminHome from './pages/AdminHome'

export default function App() {
  const location = useLocation()
  const { pathname } = location
  // Меню внизу прячем на объявлении, в переписке и на входе: там
  // человек занят одним делом, и лишние кнопки мешают.
  //
  // Объявление узнаём по хвосту адреса из восьми знаков — у прочих
  // страниц такого нет.
  // Короткая ссылка /go/<id> открывает то же самое объявление — это
  // ровно те ссылки, что уходят в Telegram и в письма. Хвоста из
  // восьми знаков у неё нет, и меню внизу оставалось: человек видел
  // сразу и нижнюю панель, и липкую кнопку «Написать продавцу»
  // поверх неё.
  const isListing = /\/[a-z0-9-]+-[0-9a-f]{8}\/?$/.test(pathname)
    || pathname.startsWith('/go/')
  // Публикатор в боте — тоже без оболочки: человек пришёл из
  // переписки на одну минуту, и нижнее меню сайта ему только мешает,
  // уводя из формы в разделы, куда он не собирался.
  const hideNav = isListing || pathname.startsWith('/chat/')
    || pathname === '/login' || pathname.startsWith('/tg/')

  // Запоминаем последнюю страницу-список (поиск, главную, избранное,
  // очередь): после удаления объявления возвращаться надо туда, откуда
  // человек пришёл, а не в раздел удалённого объявления.
  rememberListPage(pathname, location.search)

  const navType = useNavigationType()

  // Браузер сам ничего не восстанавливает: scrollRestoration='manual'
  // как раз выключает автоматику, а pushState-переходы (это SPA, не
  // обычные ссылки) браузер вообще не запоминает сам по себе — это
  // всегда должно быть на приложении. Храним прокрутку по ключу
  // истории (у каждого перехода свой) в переживающем переходы ref.
  const scrollPositions = useRef({})
  // Тип перехода и ключ истории держим в ref: эффект восстановления
  // зависит только от адреса страницы, а свежие значения ему всё равно
  // нужны.
  const navTypeRef = useRef(navType)
  navTypeRef.current = navType
  const locationKeyRef = useRef(location.key)
  locationKeyRef.current = location.key

  // Возврат из снимка браузера.
  //
  // Safari при возврате по истории или из свёрнутой вкладки показывает
  // сохранённый снимок страницы, вообще не обращаясь к серверу: данные
  // на нём могут быть многодневной давности, а объявление — уже
  // проданным.
  //
  // Раньше с этим боролись иначе: скрипт дописывал к адресу
  // ?_v=<время> и делал переход, чтобы браузеру нечего было
  // подставить. Лечило одно, ломая три — лишняя загрузка на каждом
  // заходе, мусорный хвост в ссылках, которые люди копируют и шлют друг
  // другу, и переход на неканонический адрес на глазах у поисковика.
  //
  // Правильный способ — само событие возврата из снимка. Обновляем
  // страницу, только если снимок пролежал заметное время: вернулся
  // человек через минуту — пусть видит то же, что и оставил, вместе с
  // местом прокрутки; пролежало полчаса — данные точно стоит
  // перечитать.
  useEffect(() => {
    const STALE_AFTER = 15 * 60 * 1000
    const onShow = (event) => {
      if (!event.persisted) return
      const shownAt = Number(sessionStorage.getItem('plonk_left_at') || 0)
      if (shownAt && Date.now() - shownAt > STALE_AFTER) window.location.reload()
    }
    const remember = () => {
      try { sessionStorage.setItem('plonk_left_at', String(Date.now())) } catch { /* не беда */ }
    }
    window.addEventListener('pageshow', onShow)
    window.addEventListener('pagehide', remember)
    return () => {
      window.removeEventListener('pageshow', onShow)
      window.removeEventListener('pagehide', remember)
    }
  }, [])

  useLayoutEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }
  }, [])

  // Пишем прокрутку по каждому скроллу, а не «перед уходом»: cleanup
  // эффекта срабатывает уже ПОСЛЕ того, как экран сменился на новый —
  // к этому моменту window.scrollY уже относится к новой странице, а
  // не к той, что покидали, и в кэш попадало не то число.
  // Во время перехода место не переписываем.
  //
  // При открытии объявления страница мотается наверх, и это движение
  // прилетало обработчиком прокрутки ещё живой прежней страницы — её
  // сохранённое место затиралось. Человек возвращался не туда, где
  // был: на разделе промахивались на 354 пикселя, измерил.
  const navigating = useRef(false)
  // Таймер восстановления живёт вне эффекта — см. уборку ниже.
  const restoring = useRef(null)
  // Прежний адрес: по нему отличаем замену адреса той же страницы от
  // замены одного объявления другим.
  const lastPath = useRef(pathname)

  useEffect(() => {
    const key = location.key
    const onScroll = () => {
      if (navigating.current) return
      scrollPositions.current[key] = window.scrollY
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [location.key])

  useLayoutEffect(() => {
    // Замена адреса — не переход.
    //
    // Поиск дописывает в адрес фильтры, чтобы результатом можно было
    // поделиться ссылкой. Мы принимали это за новую страницу: мотали
    // наверх, а главное — обрывали восстановление прокрутки на
    // полудороге. Оно как раз повторяет попытки, пока страница
    // дорастает, и обрыв означал, что человек остаётся наверху.
    //
    // Поэтому эффект больше не перезапускается на замене адреса
    // (см. зависимости ниже: только pathname), а сама замена ничего не
    // делает.
    // Замена адреса той же страницы (поиск дописывает фильтры) — не
    // переход, ничего не трогаем. А вот замена одного объявления другим
    // — самый настоящий переход: соседнее объявление из блоков
    // «Похожие» и «Ещё у продавца» открывается взамен текущего, и
    // открыться оно должно сверху, а не там, где человек листал
    // предыдущее.
    if (navTypeRef.current === 'REPLACE') {
      if (pathname !== lastPath.current) {
        window.scrollTo(0, 0)
        navigating.current = false
      }
      lastPath.current = pathname
      return
    }
    lastPath.current = pathname

    // Страницы разделов (/c/...) всегда открываются сверху.
    //
    // Там не список объявлений, а плитки подразделов и фильтры: человек
    // приходит туда выбирать, куда идти дальше, и возвращать его в
    // середину плиток незачем — он теряет вход в раздел из виду.
    // Запоминать место нужно там, где список: в поиске и в ленте.
    if (pathname.startsWith('/c/')) {
      window.scrollTo(0, 0)
      navigating.current = false
      return
    }

    // Пока идём на новую страницу — и пока возвращаем прокрутку —
    // сохранённое место не переписываем.
    //
    // Наш собственный вызов прокрутки порождает событие, и обработчик
    // записывал в память обрезанное значение: страница ещё короткая,
    // браузер вместо 628 ставит 274, и это 274 затирало настоящее
    // место. Дальше восстановление читало уже испорченное число и
    // считало, что попало куда надо. Человек оставался на 354 пикселя
    // выше — ровно та жалоба, с которой всё началось.
    navigating.current = true
    if (navTypeRef.current !== 'POP') {
      window.scrollTo(0, 0)
      // Наверх ушли — дальше пишем прокрутку как обычно.
      setTimeout(() => { navigating.current = false }, 100)
      return
    }

    const saved = scrollPositions.current[locationKeyRef.current]
    if (saved == null) {
      // Возвращать нечего — снимаем запрет на запись, иначе прокрутка
      // перестанет запоминаться вовсе. Так и вышло при первом заходе на
      // сайт: сохранённого места ещё нет, флаг оставался поднятым
      // навсегда, и дальше не запоминалось ничего.
      navigating.current = false
      return
    }

    // Возвращаемся не одним движением, а несколькими попытками за
    // полсекунды.
    //
    // Списки грузятся порциями, картинки и шрифты догружаются уже после
    // первой отрисовки, и высота страницы всё это время растёт. Поставить
    // прокрутку один раз мало: в этот момент страница ещё короткая,
    // браузер обрезает её до своего максимума — и человек оказывается
    // выше, чем был, а иногда в самом начале.
    //
    // Раньше такие поправки жили ещё и отдельно в ленте на главной, со
    // своим сохранённым местом. Два механизма спорили за прокрутку и
    // перебивали друг друга разными значениями — это и кидало к началу
    // при возврате свайпом. Восстановление теперь одно, здесь.
    let stop = false
    // Человек мог начать листать сам, не дожидаясь нас. Тогда поправки
    // дёргают страницу под пальцем — первое же касание их отменяет.
    const giveUp = () => { stop = true; navigating.current = false; show(); clearTimeout(restoring.current) }
    window.addEventListener('touchstart', giveUp, { passive: true, once: true })
    window.addEventListener('wheel', giveUp, { passive: true, once: true })

    // Поправляем не по таймеру, а когда страница выросла.
    //
    // Раньше прокрутка выставлялась десять раз подряд с интервалом, и
    // каждая поправка была видна: при возврате страница заметно
    // дёргалась. Теперь ставим один раз, а дальше слушаем изменения
    // высоты: подъехали фото или следующая порция — поправили, и только
    // если человек ещё не там, где нужно.
    window.scrollTo(0, saved)

    // Пробуем, пока не попадём — и сразу перестаём.
    //
    // Страница в момент возврата ещё короткая: список рисуется, фото
    // догружаются, и браузер обрезает прокрутку до своего максимума.
    // Поэтому одной попытки мало.
    //
    // Но и десять подряд, как было раньше, — плохо: каждая поправка
    // видна, и при возврате страница заметно дёргалась. Разница в том,
    // что теперь мы останавливаемся, едва попали в нужное место, и
    // больше его не трогаем. Дёргать нечего.
    // Отменяем предыдущее восстановление, если оно ещё идёт.
    clearTimeout(restoring.current)

    // Пока возвращаемся — страницу не показываем.
    //
    // Иначе человек успевает увидеть её верх, и только потом она
    // прыгает на нужное место: это и есть то мелькание при возврате.
    // Спрятать на пару кадров честнее, чем показать заведомо не то
    // место и дёрнуть.
    //
    // Прячем только если возвращаться есть куда: на самый верх страница
    // и так открывается мгновенно, прятать нечего.
    const hide = saved > 40
    if (hide) document.documentElement.classList.add('restoring-scroll')
    const show = () => document.documentElement.classList.remove('restoring-scroll')
    // Страховка: что бы ни случилось, дольше полусекунды страница
    // невидимой не останется.
    const failsafe = setTimeout(show, 500)

    // Попадание засчитываем, только если оно удержалось.
    //
    // Иначе выходило так: страница на миг дорастала, мы попадали в
    // нужное место и переставали следить, а через мгновение высота
    // менялась снова и прокрутку сбивало — человек оказывался на 354
    // пикселя выше. Теперь ждём, чтобы место продержалось три проверки
    // подряд, и только тогда отпускаем.
    let tries = 0
    let held = 0
    const put = () => {
      if (stop) return
      if (Math.abs(window.scrollY - saved) <= 2) {
        if (++held >= 3) {                                // держится — всё
          navigating.current = false
          show()
          clearTimeout(failsafe)
          return
        }
        // Первое же попадание — можно показывать: место верное, дальше
        // только убеждаемся, что оно удержалось.
        show()
        restoring.current = setTimeout(put, 80)
        return
      }
      held = 0
      window.scrollTo(0, saved)
      // Пробуем до двух с половиной секунд: на странице раздела сверху
      // ещё рисуются плитки подразделов и фильтры, и высота набирается
      // не сразу. Раньше сдавались через секунду, и человек оказывался
      // выше своего места — на 354 пикселя, измерил.
      //
      // Долгое ожидание безопасно ровно потому, что мы прекращаем при
      // первом попадании и при первом касании: дёргать под человеком
      // нечего.
      if (++tries < 30) restoring.current = setTimeout(put, 80)
      else { navigating.current = false; show() }   // дальше не пробуем
    }
    put()

    return () => {
      show()
      clearTimeout(failsafe)
      // Восстановление намеренно не отменяем.
      //
      // Уборка эффекта срабатывает не только при уходе со страницы, но
      // и когда страница обновляет свой адрес — а раздел это делает.
      // Раньше цикл обрывался на четвёртой попытке, страница ещё не
      // дорастала до нужной высоты, и человек оказывался выше своего
      // места на 354 пикселя. Останавливают восстановление только два
      // события: попали куда нужно или человек тронул экран.
      window.removeEventListener('touchstart', giveUp)
      window.removeEventListener('wheel', giveUp)
    }
    // Только pathname: замена адреса не должна перезапускать
    // восстановление — см. выше.
     
  }, [pathname])

  // «Шторка» сверху (статус-бар) — в цвет шапки на всех страницах: мятно-лаймовое свечение шапки, на тёмной теме —
  // тёмный фон, на шопсах и объявлении (видео / фото у верхнего края) — чёрный. iOS 26 Safari берёт цвет из
  // фона элемента у верхнего края (.top-tint), остальные браузеры — из meta theme-color.
  useEffect(() => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark'
    const black = pathname.startsWith('/shops') && !pathname.startsWith('/shops/') || /\/[a-z0-9-]+-[0-9a-f]{8}\/?$/.test(pathname) || pathname.startsWith('/go/')
    const color = black ? '#000000' : dark ? '#1E2421' : '#EBF1E7'
    document.documentElement.style.setProperty('--top-tint', color)
    document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.remove())
    const meta = document.createElement('meta')
    meta.setAttribute('name', 'theme-color')
    meta.setAttribute('content', color)
    document.head.appendChild(meta)
  }, [pathname])

  // Обходной приём для известного бага iOS 26: после закрытия клавиатуры
  // visualViewport.offsetTop иногда не сбрасывается в 0, из-за чего
  // координаты тапов расходятся с тем, что видно на экране.
  // Срабатываем только когда уходил фокус с реального поля ввода И клавиатура
  // действительно была открыта — иначе рывок прилетал прямо во время прокрутки.
  useEffect(() => {
    const isField = (el) =>
      el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT')

    const handleFocusOut = (e) => {
      if (!isField(e.target)) return
      const vv = window.visualViewport
      const keyboardWasOpen = vv && window.innerHeight - vv.height > 80
      if (!keyboardWasOpen) return

      setTimeout(() => {
        if (window.visualViewport && window.visualViewport.offsetTop > 0) {
          window.scrollBy(0, 1)
          window.scrollBy(0, -1)
        }
      }, 120)
    }
    document.addEventListener('focusout', handleFocusOut, true)
    return () => document.removeEventListener('focusout', handleFocusOut, true)
  }, [])

  return (
    <AuthProvider>
    <FavoritesProvider>
    <div className="app-shell">
      {/* TopNav сам прячется на мобильном через CSS (.topnav{display:none},
          комментарий в самом компоненте) — специально, чтобы не мигала при
          загрузке. Раньше !hideNav && тут дублировал то же самое решение
          вторым, JS-уровня условием — на мобильном это ничего не меняло
          (CSS и так прятал), а вот на десктопе, где .topnav показывается
          сама, это условие просто не давало ей появиться вовсе: на
          объявлении, в переписке и на входе не было никакой навигации —
          ни кнопки назад, ни ссылки на главную. BottomNav — другая
          история, там обратная логика (виден по умолчанию, прячется на
          десктопе через CSS), и на мобильном его действительно не должно
          быть на этих трёх страницах — там условие оставляем как было. */}
      <div className="top-tint" aria-hidden="true" />
      <TopNav />
      <main className={hideNav ? '' : 'has-bottomnav'}>
        {/* Пока подгружается страница по требованию — ничего не рисуем.
            Пустая заглушка лучше вертушки: подгрузка занимает доли
            секунды, а вертушка, мелькнувшая на миг, выглядит как
            дёрганье. */}
        <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/map" element={<MapSearch />} />
          <Route path="/post" element={<PostAd />} />
          <Route path="/categories" element={<Categories />} />
          {/* Вход в раздел со своими полями: человек ищет не
              «что-нибудь», а двушку до тысячи евро. */}
          <Route path="/c/:slug" element={<CategoryLandingPage />} />
          <Route path="/:city/c/:slug" element={<CityCategoryPage />} />
          {/* Короткий путь по ключу — для админки и служебных ссылок,
              где понятного адреса взять неоткуда. Приложение по хвосту
              найдёт объявление и покажет его. */}
          <Route path="/go/:slug" element={<ListingDetail />} />

          <Route path="/chat/:id" element={<ChatScreen />} />
          <Route path="/s/:slug" element={<Storefront />} />
          <Route path="/s/:slug/c/:cid" element={<Storefront />} />
          <Route path="/vitrina" element={<StorefrontManage />} />
          <Route path="/vitriny" element={<StorefrontDiscover />} />
          <Route path="/shops" element={<ShopsFeed />} />
          <Route path="/shops/new" element={<ShopEditor />} />
          <Route path="/shops/mine" element={<ShopsCabinet />} />
          <Route path="/shops/:id/edit" element={<ShopEditor />} />
          <Route path="/admin/shops" element={<AdminShops />} />
          <Route path="/jobs/responses" element={<JobResponses />} />
          <Route path="/jobs/responses/:id" element={<JobResponses />} />
          <Route path="/jobs/my" element={<MyJobResponses />} />
          <Route path="/login" element={<Login />} />
          <Route path="/favorites" element={<Favorites />} />
          <Route path="/profile/blocked" element={<BlockedUsers />} />
          <Route path="/profile/invite" element={<InviteFriend />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/my/:id/stats" element={<ListingDashboard />} />
          <Route path="/reviews/waiting" element={<WaitingReviews />} />
          {/* Публикатор внутри Telegram — без общей оболочки сайта:
              нижнего меню и шапки там быть не должно. */}
          <Route path="/tg/post" element={<TgPost />} />
          <Route path="/tg/my" element={<TgMy />} />
          <Route path="/terms" element={<LegalDoc doc="terms" />} />
          <Route path="/privacy" element={<LegalDoc doc="privacy" />} />
          <Route path="/vodic" element={<GuidesList />} />
          <Route path="/vodic/:slug" element={<GuideArticle />} />
          <Route path="/rules" element={<LegalDoc doc="rules" />} />
          <Route path="/chats" element={<Chats />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/seller/:id" element={<SellerProfile />} />
          <Route path="/my" element={<MyListings />} />
          <Route path="/admin" element={<AdminHome />} />
          <Route path="/moderation" element={<Moderation />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/users/:id" element={<AdminUser />} />
          <Route path="/admin/alerts" element={<AdminAlerts />} />
          <Route path="/admin/stats" element={<AdminStats />} />
          <Route path="/admin/audit" element={<AdminAudit />} />
          <Route path="/admin/jobs" element={<AdminJobs />} />
          <Route path="/admin/support" element={<AdminSupport />} />
          <Route path="/admin/flagged" element={<AdminFlaggedChats />} />
          <Route path="/support" element={<Support />} />
          <Route path="/volunteer" element={<Volunteer />} />
          <Route path="/admin/volunteers" element={<AdminVolunteers />} />
          <Route path="/admin/team-chats" element={<AdminTeamChats />} />
          <Route path="/admin/settings" element={<AdminSettings />} />
          <Route path="/enter" element={<Enter />} />
          <Route path="/profile/edit" element={<EditProfile />} />
          <Route path="/edit/:id" element={<EditListing />} />
          <Route path="/saved" element={<SavedSearches />} />
          <Route path="/history" element={<History />} />

          {/* Понятный адрес объявления: /beograd/mebel/stol-ikea-45e17e58.
              Стоит последним намеренно — он подходит под любые три
              части, и выше служебных страниц перехватывал бы
              /admin/users и всё остальное. */}
          <Route path="/:city/:category/:slug" element={<ListingDetail />} />
          {/* Ловит всё, что не подошло ни под одно правило выше — без
              этого несуществующий адрес открывал пустой экран без
              единого объяснения или выхода. */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
      </main>
      <Footer />
      <Island />
      <ConfirmHost />
      {!hideNav && <BottomNav />}
      {/* PLONK 2.0: короткие уведомления (Sonner) — над парящим меню, в цветах темы */}
      <Toaster position="bottom-center" offset={110} mobileOffset={{ bottom: 110 }} visibleToasts={2} duration={2200}
        toastOptions={{ classNames: { toast: 'pk-toast', success: 'pk-toast-ok' } }} />
    </div>
    </FavoritesProvider>
    </AuthProvider>
  )
}

/**
 * Пока подгружается код страницы (страницы грузятся частями), вместо пустоты — заготовка в форме обычной страницы:
 * шапка и несколько строк. Раньше на медленной связи на долю секунды был пустой экран, потом появлялся скелет,
 * потом содержимое — тройная смена картинки.
 */
function PageFallback() {
  return (
    <div className="page page-fallback" aria-hidden="true">
      <div className="page-fallback-head"><span className="sk-block" style={{ width: 40, height: 40, borderRadius: '50%' }} /><span className="sk-block" style={{ width: 180, height: 28, borderRadius: 9 }} /></div>
      {[0, 1, 2, 3].map((i) => <div key={i} className="sk-block" style={{ height: 84, borderRadius: 22, marginBottom: 10 }} />)}
    </div>
  )
}
