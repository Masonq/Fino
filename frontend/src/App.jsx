import { Routes, Route, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'
import Categories from './pages/Categories'
import ListingDetail from './pages/ListingDetail'
import BottomNav from './components/BottomNav'

export default function App() {
  const { pathname } = useLocation()
  const hideNav = pathname.startsWith('/listing/')

  return (
    <div className="app-shell">
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/post" element={<PostAd />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/listing/:id" element={<ListingDetail />} />
        </Routes>
      </main>
      {!hideNav && <BottomNav />}
    </div>
  )
}
