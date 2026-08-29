import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'

export default function BlockedUsers() {
  const { t } = useTranslation()
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState(null)

  useEffect(() => {
    api.listBlockedUsers()
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [])

  const unblock = async (id) => {
    setBusyId(id)
    try {
      await api.unblockUser(id)
      setItems((prev) => prev.filter((u) => u.id !== id))
    } catch { /* оставляем в списке — попробовать можно ещё раз */ }
    finally { setBusyId(null) }
  }

  return (
    <div className="fav-page">
      <PageHeader title={t('blocked.title')} />

      {!loaded ? null : items.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="9" /><path d="m5.5 5.5 13 13" />
            </svg>
          </div>
          <p>{t('blocked.empty')}</p>
        </div>
      ) : (
        <div className="blocked-list">
          {items.map((u) => (
            <div className="blocked-row" key={u.id}>
              <span className="avatar-mini">
                {u.avatar_url ? <img src={u.avatar_url} alt="" /> : (u.display_name || '?').trim().charAt(0).toUpperCase()}
              </span>
              <span className="blocked-name">{u.display_name}</span>
              <button
                className="blocked-unblock-btn"
                disabled={busyId === u.id}
                onClick={() => unblock(u.id)}
              >
                {t('chat.unblock')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
