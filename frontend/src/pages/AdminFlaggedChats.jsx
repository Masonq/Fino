import { intlLocale } from '../utils/time'
import { useCallback, useEffect, useState } from 'react'
import { useKeepPlace } from '../utils/keepPlace'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'

/**
 * Разговоры, где прозвучали известные приёмы обмана.
 *
 * Показываем переписку целиком, а не одну помеченную строку: решить,
 * обман это или нет, можно только прочитав разговор. «Переведите
 * предоплату» от людей, договорившихся о доставке в другой город, —
 * обычное дело, а то же самое в первом сообщении незнакомцу — уже нет.
 */
export default function AdminFlaggedChats() {
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('admin-chats')
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(null)

  const load = useCallback(() => {
    api.flaggedChats()
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [])

  useEffect(() => {
    if (authLoading) return
    if (!user || (user.role !== 'admin' && user.role !== 'moderator')) {
      navigate('/', { replace: true })
      return
    }
    load()
  }, [user, authLoading, navigate, load])

  const clear = async (id) => {
    setBusy(id)
    try {
      await api.clearChatFlag(id)
      setItems((prev) => prev.filter((c) => c.id !== id))
    } catch {
      /* не вышло — оставляем в списке, разберёмся позже */
    } finally {
      setBusy(null)
    }
  }

  const when = (iso) => new Date(iso).toLocaleString(intlLocale(i18n.language), {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })

  return (
    <div className="page">
      <PageHeader title={t('flagged.title')} />

      {!loaded && <AdminRowSkeletons count={3} />}

      {loaded && items.length === 0 && (
        <div className="admin-empty">
          <span className="admin-empty-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4v16" /><path d="M4 5h11l-1.5 3.5L15 12H4" /></svg>
          </span>
          <span className="admin-empty-title">{t('flagged.empty')}</span>
          <span className="admin-empty-text">{t('flagged.empty_hint')}</span>
        </div>
      )}

      {items.map((chat) => (
        <div key={chat.id} className="flagged-card">
          <div className="flagged-head">
            <div className="flagged-reason">{chat.reason}</div>
            <div className="flagged-when">{when(chat.flagged_at)}</div>
          </div>

          {chat.listing?.title && (
            <button
              className="flagged-listing"
              onClick={() => navigate(`/go/${chat.listing.id}`)}
            >
              {chat.listing.title}
            </button>
          )}

          {/* Переписка целиком: без неё пометка бесполезна. */}
          <div className="flagged-messages">
            {chat.messages.map((m, i) => (
              <div key={i} className={`flagged-msg ${m.from}`}>
                <span className="flagged-who">
                  {t(m.from === 'buyer' ? 'flagged.buyer' : 'flagged.seller')}
                </span>
                {m.text}
              </div>
            ))}
          </div>

          <div className="flagged-actions">
            <button
              className="flagged-clear"
              disabled={busy === chat.id}
              onClick={() => clear(chat.id)}
            >
              {t('flagged.clear')}
            </button>
            <button
              className="flagged-open"
              onClick={() => navigate(`/admin/users?q=${chat.seller_id}`)}
            >
              {t('flagged.seller_profile')}
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
