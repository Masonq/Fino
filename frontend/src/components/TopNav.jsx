import { useTranslation } from 'react-i18next'
import LangOrb from './LangOrb'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import SearchOverlay from './SearchOverlay'
import Avatar from './Avatar'

/**
 * Верхняя навигация — только для широких экранов.
 * На мобильном её место занимает нижнее меню, поэтому здесь она скрыта
 * через стили, а не условием: так не бывает мигания при загрузке.
 */
export default function TopNav() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const { user, loading: authLoading } = useAuth()
  // Поиск — только на главной: на страницах объявлений, поиска и
  // категорий уже есть свой (сайдбар с фильтрами или строка сверху
  // ленты), дублировать его тут ни к чему.
  const [searchOpen, setSearchOpen] = useState(false)
  const isHome = pathname === '/'

  const items = [
    { to: '/', key: 'nav.home' },
    { to: '/shops', key: 'nav.shops' },
    { to: '/favorites', key: 'nav.favorites' },
    { to: '/chats', key: 'nav.chats' },
    { to: '/my', key: 'my.title' },
  ]

  return (
    <div className="topnav">
      <Link to="/" className="topnav-brand">
        <img src="/logo-mark.png" alt="" />
        PLONK
      </Link>

      <nav className="topnav-links">
        {items.map((it) => (
          <Link
            key={it.to}
            to={it.to}
            className={pathname === it.to ? 'topnav-link active' : 'topnav-link'}
          >
            {t(it.key)}
          </Link>
        ))}
      </nav>

      {isHome && (
        <button type="button" className="topnav-search" onClick={() => setSearchOpen(true)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <span>{t('search.placeholder')}</span>
        </button>
      )}

      <div className="topnav-right">
        <LangOrb />
        <Link to="/post" className="topnav-post">{t('nav.post')}</Link>
        {/* Тот же скачок макета, что чинил в Home.jsx: пока идёт
            проверка токена, user ещё null — без этого тут на секунду
            показывалось «Войти» текстом, а затем сжималось в кружок
            аватара. Нейтральный кружок того же размера не дёргается
            ни в одну сторону, каким бы ни был исход. */}
        {authLoading ? (
          <span className="avatar-mini skeleton" />
        ) : user ? (
          <Link to="/profile" className="topnav-user">
            {/* Через общий Avatar, а не голой картинкой: ссылка на фото
                из Telegram или Google со временем перестаёт отдаваться,
                и Safari рисовал в кружке синий значок с вопросом. Avatar
                ловит ошибку загрузки и показывает букву. */}
            <Avatar
              src={user.avatar_url}
              name={user.company_name || user.display_name}
              className={user.role === 'seller_business' ? 'avatar-mini is-company' : 'avatar-mini'}
            />
          </Link>
        ) : (
          <Link to="/login" className="topnav-login">{t('common.login')}</Link>
        )}
      </div>
      {isHome && <SearchOverlay open={searchOpen} onClose={() => setSearchOpen(false)} />}
    </div>
  )
}
