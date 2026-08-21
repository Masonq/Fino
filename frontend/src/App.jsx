import { Routes, Route } from 'react-router-dom'
import LanguageSwitcher from './components/LanguageSwitcher'
import Home from './pages/Home'
import Search from './pages/Search'
import PostAd from './pages/PostAd'

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <LanguageSwitcher />
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/post" element={<PostAd />} />
        </Routes>
      </main>
    </div>
  )
}
