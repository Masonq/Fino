import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { timeAgo } from '../utils/time'

// Список переписок — используется и на странице «Сообщения» (мобильный
// вид, весь экран), и внутри самой переписки на десктопе (боковая
// колонка рядом с открытым чатом, см. ChatScreen.jsx). activeId
// подсвечивает открытую сейчас переписку — на мобильном он всегда
// пуст, там список и открытый чат — разные экраны.
export default function ChatList({ activeId, onLoaded }) {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const userId = user?.id

  useEffect(() => {
    if (!userId) { setLoaded(true); onLoaded?.(true); return }
    api.getChats(i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => { setLoaded(true); onLoaded?.(true) })
  }, [userId, i18n.language])

  if (!loaded) {
    return (
      <div className="chat-list">
        {Array.from({ length: 4 }).map((_, i) => (
          <div className="chat-row skeleton" key={i}>
            <div className="chat-thumb sk-block" />
            <div className="chat-row-body">
              <div className="sk-line title" />
              <div className="sk-line meta" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="fav-empty">
        <div className="fav-empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />
          </svg>
        </div>
        <p>{t('chats.empty')}</p>
        <Link className="fav-cta" to="/">{t('actions.to_listings')}</Link>
      </div>
    )
  }

  return (
    <div className="chat-list">
      {items.map((c) => (
        <Link
          key={c.id}
          to={`/chat/${c.id}`}
          className={[c.unread ? 'chat-row unread' : 'chat-row', c.id === activeId ? 'active' : ''].filter(Boolean).join(' ')}
        >
          <div className="chat-thumb">
            {c.listing_photo
              ? <img src={c.listing_photo} alt="" />
              : <div className="photo-placeholder" />}
          </div>
          <div className="chat-row-body">
            <div className="chat-row-top">
              <span className="chat-name">{c.other_name || '—'}</span>
              <span className="chat-time">{timeAgo(c.last_at, t, i18n.language)}</span>
            </div>
            <div className="chat-listing">{c.listing_title}</div>
            <div className="chat-row-bottom">
              <span className="chat-last">
                {c.last_from_me && <span className="chat-you">{t('chats.you')}: </span>}
                {c.last_text || t('chats.no_messages')}
              </span>
              {c.unread > 0 && <span className="chat-badge">{c.unread}</span>}
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
}
