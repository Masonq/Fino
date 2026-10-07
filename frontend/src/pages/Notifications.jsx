import { useAutoAnimate } from '@formkit/auto-animate/react'
import { confirmSheet } from '../utils/confirm'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import SwipeableNotification from '../components/SwipeableNotification'
import { timeAgo } from '../utils/time'

export default function Notifications() {
  const { t, i18n } = useTranslation()
  // Удалили или добавили — соседи плавно съезжают (AutoAnimate, ~3 КБ; сам гаснет при «уменьшить движение»)
  const [listRef] = useAutoAnimate()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [openId, setOpenId] = useState(null)   // id строки, у которой сейчас видна красная кнопка
  const sentinelRef = useRef(null)

  const userId = user?.id

  useEffect(() => {
    if (!userId) { setLoaded(true); return }
    api.getNotifications()
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0) })
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [userId])

  const loadMore = useCallback(() => {
    if (loadingMore || items.length >= total) return
    setLoadingMore(true)
    api.getNotifications(items.length)
      .then((res) => setItems((prev) => [...prev, ...(res.items || [])]))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [items.length, total, loadingMore])

  useEffect(() => {
    if (!loaded || items.length === 0 || items.length >= total) return
    const el = sentinelRef.current
    if (!el) return
    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '600px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [loaded, items.length, total, loadMore])

  const open = (n) => {
    if (!n.is_read) {
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)))
      api.markNotificationRead(n.id).catch(() => {})
    }
    if (n.link) navigate(n.link)
  }

  const readAll = () => {
    setItems((prev) => prev.map((x) => ({ ...x, is_read: true })))
    api.markAllNotificationsRead().catch(() => {})
  }

  const remove = (n) => {
    setOpenId(null)
    setItems((prev) => prev.filter((x) => x.id !== n.id))
    setTotal((prev) => Math.max(0, prev - 1))
    api.deleteNotification(n.id).catch(() => {})
  }

  const clearAll = async () => {
    if (!(await confirmSheet({ title: t('notif.clear_all_confirm'), confirm: t('confirm.clear'), danger: true }))) return
    setOpenId(null)
    setItems([])
    setTotal(0)
    api.deleteAllNotifications().catch(() => {})
  }

  const hasUnread = items.some((n) => !n.is_read)

  if (!userId) {
    return (
      <div className="fav-page notif-page">
        <PageHeader title={t('notif.title')} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
          </div>
          <p>{t('notif.need_auth')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fnotifications')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page notif-page">
      <PageHeader title={t('notif.title')} kicker={!loaded ? '\u00a0' : hasUnread ? t('notif.kicker_new') : t('notif.kicker_all')}>
        {hasUnread && (
          <button className="notif-read-all" onClick={readAll}>{t('notif.read_all')}</button>
        )}
        {items.length > 0 && (
          <button className="notif-clear-all" onClick={clearAll}>{t('notif.clear_all')}</button>
        )}
      </PageHeader>

      {!loaded ? (
        <div className="notif-list">
          {Array.from({ length: 5 }).map((_, i) => (
            <div className="notif-row skeleton" key={i}>
              <div className="sk-block sk-line" style={{ height: 13, width: '85%' }} />
              <div className="sk-block sk-line" style={{ height: 11, width: 60, marginTop: 6 }} />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
          </div>
          <p>{t('notif.empty')}</p>
        </div>
      ) : (
        <>
          <div className="notif-list" ref={listRef}>
            {items.map((n) => (
              <SwipeableNotification
                key={n.id}
                notification={n}
                isOpen={openId === n.id}
                onOpenChange={setOpenId}
                onOpen={open}
                onDelete={remove}
              >
                <div className="notif-text">{n.text}</div>
                <div className="notif-time">{timeAgo(n.created_at, t, i18n.language)}</div>
              </SwipeableNotification>
            ))}
          </div>
          {items.length < total && (
            <div ref={sentinelRef} className="feed-sentinel">
              {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}
            </div>
          )}
        </>
      )}
    </div>
  )
}
