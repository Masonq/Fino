import { Link, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { showIsland } from '../utils/island'
import { plainTeamText } from '../utils/teamText'

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
    // Простой «+» — как у остальных иконок в меню: один ясный контур,
    // а не составная фигура из листа и мелкого плюса сбоку.
    icon: <><path d="M12 5v14M5 12h14" /></>,
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
  const seen = useRef(null)          // сколько непрочитанных было в прошлый опрос; null — ещё не опрашивали

  // Значок непрочитанных на «Сообщениях» — иначе о новом сообщении
  // можно узнать, только зайдя в раздел.
  useEffect(() => {
    if (!user) { setUnread(0); return }
    const tick = () => {
      if (document.hidden) return
      api.getChats(i18n.language)
        .then((res) => {
          const items = res.items || []
          const total = items.reduce((n, c) => n + (c.unread || 0), 0)
          setUnread(total)

          // Остров — только когда непрочитанных стало БОЛЬШЕ, чем при
          // прошлом опросе, и не в самих чатах: там сообщение и так
          // перед глазами. Первый опрос — точка отсчёта, а не новость:
          // иначе каждое открытие сайта начиналось бы с «нового
          // сообщения», о котором человек давно знает.
          const inChats = window.location.pathname.startsWith('/chat')
          if (seen.current !== null && total > seen.current && !inChats) {
            const c = items.find((x) => x.unread > 0)
            if (c) {
              const preview = c.last_kind === 'team' ? plainTeamText(c.last_text) : (c.last_text || '')
              showIsland({
                kind: 'msg',
                text: `${c.other_name}: ${preview}`.slice(0, 60),
                to: `/chat/${c.id}`,
              })
            }
          }
          seen.current = total
        })
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
          viewTransition
          key={item.to}
          to={item.to}
          className={[
            'nav-item',
            pathname === item.to ? 'active' : '',
            item.to === '/post' ? 'nav-item-post' : '',
          ].filter(Boolean).join(' ')}
        >
          {/* «Разместить» — главное действие площадки, и оно не должно
              выглядеть как ещё один пункт меню. Плюс в цветном круге
              читается как кнопка, а не как вкладка. */}
          <span className="nav-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={item.to === '/post' ? 2.6 : 1.9} strokeLinecap="round" strokeLinejoin="round">
              {item.icon}
            </svg>
          </span>
          {t(item.key)}
          {item.key === 'nav.chats' && unread > 0 && (
            <span className="nav-badge">{unread > 9 ? '9+' : unread}</span>
          )}
        </Link>
      ))}
    </div>
  )
}
