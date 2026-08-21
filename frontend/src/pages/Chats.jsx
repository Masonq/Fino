import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

function timeAgo(iso, t) {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso + 'Z').getTime()) / 1000
  if (diff < 60) return t('chats.just_now')
  if (diff < 3600) return `${Math.floor(diff / 60)} ${t('chats.min')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${t('chats.hour')}`
  const days = Math.floor(diff / 86400)
  if (days < 7) return `${days} ${t('chats.day')}`
  return new Date(iso + 'Z').toLocaleDateString()
}

export default function Chats() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const userId = user?.id

  useEffect(() => {
    if (!userId) { setLoaded(true); return }
    api.getChats(userId, i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [userId, i18n.language])

  if (!userId) {
    return (
      <div className="fav-page">
        <PageHeader title={t('nav.chats')} back={false} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />
            </svg>
          </div>
          <p>{t('chats.need_auth')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fchats')}>
            {t('actions.continue')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page">
      <PageHeader title={t('nav.chats')} back={false} />

      {!loaded ? (
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
      ) : items.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />
            </svg>
          </div>
          <p>{t('chats.empty')}</p>
          <Link className="fav-cta" to="/">{t('actions.to_listings')}</Link>
        </div>
      ) : (
        <div className="chat-list">
          {items.map((c) => (
            <Link key={c.id} to={`/chat/${c.id}`} className={c.unread ? 'chat-row unread' : 'chat-row'}>
              <div className="chat-thumb">
                {c.listing_photo
                  ? <img src={c.listing_photo} alt="" />
                  : <div className="photo-placeholder" />}
              </div>
              <div className="chat-row-body">
                <div className="chat-row-top">
                  <span className="chat-name">{c.other_name || '—'}</span>
                  <span className="chat-time">{timeAgo(c.last_at, t)}</span>
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
      )}
    </div>
  )
}
