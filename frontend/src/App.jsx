import { Routes, Route, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'
import Categories from './pages/Categories'
import ListingDetail from './pages/ListingDetail'
import ChatScreen from './pages/ChatScreen'
import BottomNav from './components/BottomNav'

export default function App() {
  const { pathname } = useLocation()
  const hideNav = pathname.startsWith('/listing/') || pathname.startsWith('/chat/')

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
        </Routes>
      </main>
      {!hideNav && <BottomNav />}
    </div>
  )
}
