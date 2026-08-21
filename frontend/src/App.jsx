import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect, useLayoutEffect } from 'react'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'
import Categories from './pages/Categories'
import ListingDetail from './pages/ListingDetail'
import ChatScreen from './pages/ChatScreen'
import Identify from './pages/Identify'
import BottomNav from './components/BottomNav'

export default function App() {
  const { pathname } = useLocation()
  const hideNav = pathname.startsWith('/listing/') || pathname.startsWith('/chat/') || pathname === '/identify'

  useLayoutEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  // Обходной приём для известного бага iOS 26: после закрытия клавиатуры
  // visualViewport.offsetTop иногда не сбрасывается в 0, из-за чего
  // координаты тапов расходятся с тем, что видно на экране.
  // Микро-скролл на 1px туда-обратно заставляет Safari пересчитать это состояние.
  useEffect(() => {
    const handleFocusOut = () => {
      setTimeout(() => {
        window.scrollBy(0, 1)
        window.scrollBy(0, -1)
      }, 100)
    }
    document.addEventListener('focusout', handleFocusOut, true)
    return () => document.removeEventListener('focusout', handleFocusOut, true)
  }, [])

  return (
    <div className="app-shell">
      <main className={hideNav ? '' : 'has-bottomnav'}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/post" element={<PostAd />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/listing/:id" element={<ListingDetail />} />
          <Route path="/chat/:id" element={<ChatScreen />} />
          <Route path="/identify" element={<Identify />} />
        </Routes>
      </main>
      {!hideNav && <BottomNav />}
    </div>
  )
}
