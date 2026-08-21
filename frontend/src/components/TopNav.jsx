import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Верхняя навигация — только для широких экранов.
 * На мобильном её место занимает нижнее меню, поэтому здесь она скрыта
 * через стили, а не условием: так не бывает мигания при загрузке.
 */
export default function TopNav() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const { user } = useAuth()

  const items = [
    { to: '/', key: 'nav.home' },
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

      <div className="topnav-right">
        <Link to="/post" className="topnav-post">{t('nav.post')}</Link>
        {user ? (
          <Link to="/profile" className="topnav-user">
            <span className="avatar-mini">
              {(user.display_name || '?').trim().charAt(0).toUpperCase()}
            </span>
          </Link>
        ) : (
          <Link to="/login" className="topnav-login">{t('common.login')}</Link>
        )}
      </div>
    </div>
  )
}
