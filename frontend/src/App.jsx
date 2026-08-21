import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'
import Categories from './pages/Categories'
import BottomNav from './components/BottomNav'

export default function App() {
  return (
    <div className="app-shell">
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/post" element={<PostAd />} />
          <Route path="/categories" element={<Categories />} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  )
}
