import { Routes, Route, useLocation, useNavigationType } from 'react-router-dom'
import { useEffect, useLayoutEffect, useRef } from 'react'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'
import Categories from './pages/Categories'
import CategoryLanding from './pages/CategoryLanding'
import ListingDetail from './pages/ListingDetail'
import ChatScreen from './pages/ChatScreen'
import ComingSoon from './pages/ComingSoon'
import Favorites from './pages/Favorites'
import BlockedUsers from './pages/BlockedUsers'
import Notifications from './pages/Notifications'
import ListingDashboard from './pages/ListingDashboard'
import LegalDoc from './pages/LegalDoc'
import Chats from './pages/Chats'
import Login from './pages/Login'
import Profile from './pages/Profile'
import SellerProfile from './pages/SellerProfile'
import MyListings from './pages/MyListings'
import AdminAudit from './pages/AdminAudit'
import EditProfile from './pages/EditProfile'
import Enter from './pages/Enter'
import AdminSupport from './pages/AdminSupport'
import Support from './pages/Support'
import AdminStats from './pages/AdminStats'
import AdminUsers from './pages/AdminUsers'
import Moderation from './pages/Moderation'
import EditListing from './pages/EditListing'
import SavedSearches from './pages/SavedSearches'
import History from './pages/History'
import NotFound from './pages/NotFound'
import { AuthProvider } from './context/AuthContext'
import { FavoritesProvider } from './context/FavoritesContext'
import BottomNav from './components/BottomNav'
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
    if (navType === 'POP') {
      // Восстанавливаем на следующий кадр — если сделать сразу, страница
      // ещё может быть короче нужного (список только начал грузиться),
      // и браузер обрежет прокрутку до своего текущего максимума.
      const saved = scrollPositions.current[location.key]
      if (saved != null) {
        requestAnimationFrame(() => window.scrollTo(0, saved))
      }
      return
    }
    window.scrollTo(0, 0)
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
      </main>
      {!hideNav && <BottomNav />}
    </div>
    </FavoritesProvider>
    </AuthProvider>
  )
}
