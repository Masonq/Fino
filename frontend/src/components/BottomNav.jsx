import { Link, useLocation } from 'react-router-dom'

export default function BottomNav() {
  const { pathname } = useLocation()

  return (
    <div className="bottomnav">
      <Link to="/" className={pathname === '/' ? 'nav-item active' : 'nav-item'}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 11l9-8 9 8" /><path d="M5 10v10h14V10" /></svg>
        Главная
      </Link>
      <Link to="/post" className="nav-post">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6"><path d="M12 5v14M5 12h14" /></svg>
      </Link>
      <Link to="/search" className={pathname === '/search' ? 'nav-item active' : 'nav-item'}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
        Поиск
      </Link>
    </div>
  )
}
