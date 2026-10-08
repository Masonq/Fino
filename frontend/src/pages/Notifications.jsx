import EmptyArt from '../components/EmptyArt'
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

// вид уведомления — по ссылке и тексту: свой значок и цвет плитки
const NOTIF_ICON = {
  chat: '<path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.7L4 20.5l1.3-3.9A8 8 0 1 1 20.5 12Z" />',
  price: '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z" /><path d="M7.5 7.5h.01" />',
  check: '<path d="M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5z" /><path d="m9 12 2 2 4-4" />',
  money: '<rect x="3" y="6" width="18" height="13" rx="3" /><path d="M16 12.5h2M3 10h18" />',
  team: '<path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.9z" />',
  other: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />',
}
function notifKind(n) {
  const l = n.link || '', x = (n.text || '').toLowerCase()
  if (l.startsWith('/chat')) return 'chat'
  if (/цен|cen|price|подешев|pojeftin/.test(x)) return 'price'
  if (/провер|документ|verif|dokument|одобр|отклон|odobr|odbij/.test(x)) return 'check'
  if (/rsd|бонус|bonus|баланс|stanje|balance/.test(x)) return 'money'
  if (/лент|feed|команд|tim|team/.test(x)) return 'team'
  return 'other'
}
function dayGroup(iso) {
  const d = new Date(iso), now = new Date()
  const days = Math.floor((new Date(now.toDateString()) - new Date(d.toDateString())) / 864e5)
  return days <= 0 ? 'today' : days === 1 ? 'yesterday' : 'earlier'
}

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
          <EmptyArt name="notifications" />
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
          <EmptyArt name="notifications" />
          <p>{t('notif.empty')}</p>
        </div>
      ) : (
        <>
          <div className="notif-list" ref={listRef}>
            {items.map((n, i) => (
              <div key={n.id}>
              {/* группы по дням, как в iOS: «Сегодня», «Вчера», «Ранее» */}
              {dayGroup(n.created_at) !== (i ? dayGroup(items[i - 1].created_at) : '') && <div className="notif-day">{t(`notif.day_${dayGroup(n.created_at)}`)}</div>}
              <SwipeableNotification
                key={n.id}
                notification={n}
                isOpen={openId === n.id}
                onOpenChange={setOpenId}
                onOpen={open}
                onDelete={remove}
              >
                <span className={`notif-ico k-${notifKind(n)}`} aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" dangerouslySetInnerHTML={{ __html: NOTIF_ICON[notifKind(n)] }} /></span>
                <div className="notif-body">
                  <div className="notif-text">{n.text}</div>
                  <div className="notif-time">{timeAgo(n.created_at, t, i18n.language)}</div>
                </div>
              </SwipeableNotification>
              </div>
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
