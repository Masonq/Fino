import { Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const ITEMS = [
  {
    to: '/', key: 'nav.home',
    icon: <><path d="M3 11l9-8 9 8" /><path d="M5 10v10h14V10" /></>,
  },
  {
    to: '/favorites', key: 'nav.favorites',
    icon: <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />,
  },
  {
    to: '/post', key: 'nav.post',
    // Лист с плюсом. Прежний вылезал за нижний край поля (плюс стоял на
    // 22.5 при высоте 24) — оттого значок и выглядел кривым.
    icon: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h7" /><path d="M8 8h6M8 12h4" /><circle cx="17.5" cy="17.5" r="4.5" /><path d="M17.5 15.5v4M15.5 17.5h4" /></>,
  },
  {
    to: '/chats', key: 'nav.chats',
    icon: <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />,
  },
  {
    to: '/profile', key: 'nav.profile',
    icon: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" /></>,
  },
]

export default function BottomNav() {
  const { pathname } = useLocation()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const [unread, setUnread] = useState(0)

  // Значок непрочитанных на «Сообщениях» — иначе о новом сообщении
  // можно узнать, только зайдя в раздел.
  useEffect(() => {
    if (!user) { setUnread(0); return }
    const tick = () => {
      if (document.hidden) return
      api.getChats(i18n.language)
        .then((res) => setUnread((res.items || []).reduce((n, c) => n + (c.unread || 0), 0)))
        .catch(() => {})
    }
    tick()
    const timer = setInterval(tick, 20000)
    document.addEventListener('visibilitychange', tick)
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', tick) }
  }, [user, i18n.language, pathname])

  return (
    <div className="bottomnav">
      {ITEMS.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className={pathname === item.to ? 'nav-item active' : 'nav-item'}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            {item.icon}
          </svg>
          {t(item.key)}
          {item.key === 'nav.chats' && unread > 0 && (
            <span className="nav-badge">{unread > 9 ? '9+' : unread}</span>
          )}
        </Link>
      ))}
    </div>
  )
}
