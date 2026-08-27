import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

/**
 * Колокольчик рядом с профилем — единственное место, где решения
 * модерации, истечение объявления и новое по подписке видны на самом
 * сайте, а не только в Telegram или почте.
 */
export default function NotificationBell() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const { user } = useAuth()
  const [unread, setUnread] = useState(0)

  // Тот же приём опроса, что и у значка непрочитанных сообщений в
  // нижнем меню: раз в 20 секунд, и сразу при возврате на вкладку —
  // необязательно ждать целый интервал, чтобы увидеть, что пришло,
  // пока телефон был свёрнут.
  useEffect(() => {
    if (!user) { setUnread(0); return }
    const tick = () => {
      if (document.hidden) return
      api.getNotificationsUnread()
        .then((res) => setUnread(res.unread || 0))
        .catch(() => {})
    }
    tick()
    const timer = setInterval(tick, 20000)
    document.addEventListener('visibilitychange', tick)
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', tick) }
  }, [user, pathname])

  if (!user) return null

  return (
    <Link to="/notifications" className="notif-bell" aria-label={t('notif.title')}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      {unread > 0 && <span className="notif-bell-badge">{unread > 9 ? '9+' : unread}</span>}
    </Link>
  )
}
