import EmptyArt from '../components/EmptyArt'
import { useEffect, useState } from 'react'
import Avatar from '../components/Avatar'
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
    <div className="fav-page blocked-page">
      <PageHeader title={t('blocked.title')} />

      {!loaded ? null : items.length === 0 ? (
        <div className="fav-empty">
          <EmptyArt name="blocked" />
          <p>{t('blocked.empty')}</p>
        </div>
      ) : (
        <div className="blocked-list">
          {items.map((u) => (
            <div className="blocked-row" key={u.id}>
              <span className="avatar-mini">
                <Avatar src={u.avatar_url} name={u.display_name} className="avatar-inner" />
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
