import { Routes, Route, useLocation, useNavigationType } from 'react-router-dom'
import { Suspense, lazy, useEffect, useLayoutEffect, useRef } from 'react'
import Home from './pages/Home'
import Search from './pages/Search'
import CategoryLanding from './pages/CategoryLanding'
import ListingDetail from './pages/ListingDetail'
import NotFound from './pages/NotFound'

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
const Categories = lazy(() => import('./pages/Categories'))
const ChatScreen = lazy(() => import('./pages/ChatScreen'))
const ComingSoon = lazy(() => import('./pages/ComingSoon'))
const Favorites = lazy(() => import('./pages/Favorites'))
const BlockedUsers = lazy(() => import('./pages/BlockedUsers'))
const InviteFriend = lazy(() => import('./pages/InviteFriend'))
const Notifications = lazy(() => import('./pages/Notifications'))
const ListingDashboard = lazy(() => import('./pages/ListingDashboard'))
const LegalDoc = lazy(() => import('./pages/LegalDoc'))
const Chats = lazy(() => import('./pages/Chats'))
const Login = lazy(() => import('./pages/Login'))
const Profile = lazy(() => import('./pages/Profile'))
const SellerProfile = lazy(() => import('./pages/SellerProfile'))
const MyListings = lazy(() => import('./pages/MyListings'))
const AdminAudit = lazy(() => import('./pages/AdminAudit'))
const EditProfile = lazy(() => import('./pages/EditProfile'))
const Enter = lazy(() => import('./pages/Enter'))
const AdminSupport = lazy(() => import('./pages/AdminSupport'))
const Support = lazy(() => import('./pages/Support'))
const AdminStats = lazy(() => import('./pages/AdminStats'))
const AdminUsers = lazy(() => import('./pages/AdminUsers'))
const Moderation = lazy(() => import('./pages/Moderation'))
const EditListing = lazy(() => import('./pages/EditListing'))
const SavedSearches = lazy(() => import('./pages/SavedSearches'))
const History = lazy(() => import('./pages/History'))
import { AuthProvider } from './context/AuthContext'
import { FavoritesProvider } from './context/FavoritesContext'
import BottomNav from './components/BottomNav'
import Footer from './components/Footer'
import TopNav from './components/TopNav'

export default function App() {
  const location = useLocation()
  const { pathname } = location
  // Меню внизу прячем на объявлении, в переписке и на входе: там
  // человек занят одним делом, и лишние кнопки мешают.
  //
  // Объявление узнаём по хвосту адреса из восьми знаков — у прочих
  // страниц такого нет.
  const isListing = /\/[a-z0-9-]+-[0-9a-f]{8}\/?$/.test(pathname)
  const hideNav = isListing || pathname.startsWith('/chat/') || pathname === '/login'

  const navType = useNavigationType()

  // Браузер сам ничего не восстанавливает: scrollRestoration='manual'
  // как раз выключает автоматику, а pushState-переходы (это SPA, не
  // обычные ссылки) браузер вообще не запоминает сам по себе — это
  // всегда должно быть на приложении. Храним прокрутку по ключу
  // истории (у каждого перехода свой) в переживающем переходы ref.
  const scrollPositions = useRef({})

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
  useEffect(() => {
    const key = location.key
    const onScroll = () => { scrollPositions.current[key] = window.scrollY }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [location.key])

  useLayoutEffect(() => {
    if (navType !== 'POP') {
      window.scrollTo(0, 0)
      return
    }

    const saved = scrollPositions.current[location.key]
    if (saved == null) return

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
    const giveUp = () => { stop = true }
    window.addEventListener('touchstart', giveUp, { passive: true, once: true })
    window.addEventListener('wheel', giveUp, { passive: true, once: true })

    let tries = 0
    const put = () => {
      if (stop) return
      if (Math.abs(window.scrollY - saved) > 2) window.scrollTo(0, saved)
      if (++tries < 10) setTimeout(put, 60)
    }
    put()

    return () => {
      stop = true
      window.removeEventListener('touchstart', giveUp)
      window.removeEventListener('wheel', giveUp)
    }
  }, [pathname, navType, location.key])

  // на не-главных экранах статус-бар под цвет фона страницы;
  // на главной им управляет баннер
  useEffect(() => {
    if (pathname === '/') return
    document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.remove())
    const meta = document.createElement('meta')
    meta.setAttribute('name', 'theme-color')
    meta.setAttribute('content', '#FAFAF9')
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
      <TopNav />
      <main className={hideNav ? '' : 'has-bottomnav'}>
        {/* Пока подгружается страница по требованию — ничего не рисуем.
            Пустая заглушка лучше вертушки: подгрузка занимает доли
            секунды, а вертушка, мелькнувшая на миг, выглядит как
            дёрганье. */}
        <Suspense fallback={null}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/post" element={<PostAd />} />
          <Route path="/categories" element={<Categories />} />
          {/* Вход в раздел со своими полями: человек ищет не
              «что-нибудь», а двушку до тысячи евро. */}
          <Route path="/c/:slug" element={<CategoryLanding />} />
          {/* Короткий путь по ключу — для админки и служебных ссылок,
              где понятного адреса взять неоткуда. Приложение по хвосту
              найдёт объявление и покажет его. */}
          <Route path="/go/:slug" element={<ListingDetail />} />

          <Route path="/chat/:id" element={<ChatScreen />} />
          <Route path="/login" element={<Login />} />
          <Route path="/favorites" element={<Favorites />} />
          <Route path="/profile/blocked" element={<BlockedUsers />} />
          <Route path="/profile/invite" element={<InviteFriend />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/my/:id/stats" element={<ListingDashboard />} />
          <Route path="/terms" element={<LegalDoc doc="terms" />} />
          <Route path="/privacy" element={<LegalDoc doc="privacy" />} />
          <Route path="/rules" element={<LegalDoc doc="rules" />} />
          <Route path="/chats" element={<Chats />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/seller/:id" element={<SellerProfile />} />
          <Route path="/my" element={<MyListings />} />
          <Route path="/moderation" element={<Moderation />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/stats" element={<AdminStats />} />
          <Route path="/admin/audit" element={<AdminAudit />} />
          <Route path="/admin/support" element={<AdminSupport />} />
          <Route path="/support" element={<Support />} />
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
      {!hideNav && <BottomNav />}
    </div>
    </FavoritesProvider>
    </AuthProvider>
  )
}
