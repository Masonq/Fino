import { Routes, Route, useLocation, useNavigationType } from 'react-router-dom'
import { useEffect, useLayoutEffect } from 'react'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'
import Categories from './pages/Categories'
import ListingDetail from './pages/ListingDetail'
import ChatScreen from './pages/ChatScreen'
import ComingSoon from './pages/ComingSoon'
import Favorites from './pages/Favorites'
import Chats from './pages/Chats'
import Login from './pages/Login'
import Profile from './pages/Profile'
import SellerProfile from './pages/SellerProfile'
import MyListings from './pages/MyListings'
import AdminAudit from './pages/AdminAudit'
import Enter from './pages/Enter'
import AdminSupport from './pages/AdminSupport'
import Support from './pages/Support'
import AdminStats from './pages/AdminStats'
import AdminUsers from './pages/AdminUsers'
import Moderation from './pages/Moderation'
import EditListing from './pages/EditListing'
import SavedSearches from './pages/SavedSearches'
import History from './pages/History'
import { AuthProvider } from './context/AuthContext'
import { FavoritesProvider } from './context/FavoritesContext'
import BottomNav from './components/BottomNav'
import TopNav from './components/TopNav'

export default function App() {
  const { pathname } = useLocation()
  const hideNav = pathname.startsWith('/listing/') || pathname.startsWith('/chat/') || pathname === '/login'

  const navType = useNavigationType()

  // Браузер восстанавливает прокрутку сам и делает это после нашего кода,
  // причём считает её для страницы, которая ещё не догрузилась. Он
  // перезаписывал верное положение — берём восстановление на себя.
  useLayoutEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }
  }, [])

  useLayoutEffect(() => {
    // Наверх прокручиваем только при переходе вперёд. При возврате экран
    // сам восстанавливает своё положение, и этот сброс отменял его — из-за
    // чего лента дёргалась: сначала прыгала наверх, потом на место.
    if (navType === 'POP') return
    window.scrollTo(0, 0)
  }, [pathname, navType])

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
      {!hideNav && <TopNav />}
      <main className={hideNav ? '' : 'has-bottomnav'}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/post" element={<PostAd />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/listing/:id" element={<ListingDetail />} />
          <Route path="/chat/:id" element={<ChatScreen />} />
          <Route path="/login" element={<Login />} />
          <Route path="/favorites" element={<Favorites />} />
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
          <Route path="/edit/:id" element={<EditListing />} />
          <Route path="/saved" element={<SavedSearches />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
      {!hideNav && <BottomNav />}
    </div>
    </FavoritesProvider>
    </AuthProvider>
  )
}
