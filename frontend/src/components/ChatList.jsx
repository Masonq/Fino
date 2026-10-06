import { useAutoAnimate } from '@formkit/auto-animate/react'
import { plainTeamText } from '../utils/teamText'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
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
export default function ChatList({ activeId, onLoaded, query = '', filter = 'all' }) {
  const { t, i18n } = useTranslation()
  // Удалили или добавили — соседи плавно съезжают (AutoAnimate, ~3 КБ; сам гаснет при «уменьшить движение»)
  const [listRef] = useAutoAnimate()
  const { user } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const userId = user?.id

  useEffect(() => {
    if (!userId) { setLoaded(true); onLoaded?.(0); return }
    api.getChats(i18n.language)
      .then((res) => { const list = res.items || []; setItems(list); onLoaded?.(list.length) })
      .catch(() => { setItems([]); onLoaded?.(0) })
      .finally(() => { setLoaded(true) })
  // Намеренно: обработчик задаёт родитель заново на каждой отрисовке; добавить его в зависимости — значит перезапрашивать список без конца.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, i18n.language])

  // Отбор и поиск — на устройстве, без запроса к серверу: переписок у
  // человека десятки, а не тысячи, и ждать ответ ради фильтра «только
  // непрочитанные» незачем. Ищем по собеседнику, объявлению и тексту
  // последнего сообщения — по всему, что человек видит в строке.
  const needle = query.trim().toLowerCase()
  const visible = items.filter((c) => {
    if (filter === 'unread' && !c.unread) return false
    if (filter === 'selling' && !c.is_seller) return false
    if (filter === 'buying' && c.is_seller) return false
    if (!needle) return true
    return [c.other_name, c.listing_title, c.last_text]
      .filter(Boolean).some((v) => v.toLowerCase().includes(needle))
  })

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

  // свайп-действия (как в Telegram): закрепить, непрочитано, без звука, удалить у себя (с «Отменить»)
  const pref = (c, action) => {
    const patch = { pin: { pinned: true }, unpin: { pinned: false }, mute: { muted: true }, unmute: { muted: false }, unread: { unread: 1 }, read: { unread: 0 } }[action]
    setItems((list) => {
      const next = list.map((x) => (x.id === c.id ? { ...x, ...patch } : x))
      return action === 'pin' || action === 'unpin' ? [...next.filter((x) => x.pinned), ...next.filter((x) => !x.pinned)] : next
    })
    api.chatPref(c.id, action).catch(() => toast.error(t('common.error')))
  }
  const remove = (c) => {
    setItems((list) => list.filter((x) => x.id !== c.id))
    api.chatPref(c.id, 'hide').catch(() => {})
    toast(t('chats.deleted'), { action: { label: t('chats.undo'), onClick: () => { api.chatPref(c.id, 'unhide').then(() => setItems((list) => [c, ...list])).catch(() => {}) } } })
  }
  return (
    <div className="chat-list" ref={listRef}>
      {visible.length === 0 && (
        <p className="empty-hint">{t('chats.nothing_found')}</p>
      )}
      {visible.map((c) => (
        <SwipeRow key={c.id}
          actions={{
            left: [{ key: 'pin', label: c.pinned ? t('chats.unpin') : t('chats.pin'), cls: 'sw-pin', run: () => pref(c, c.pinned ? 'unpin' : 'pin') },
                   { key: 'unread', label: c.unread ? t('chats.mark_read') : t('chats.mark_unread'), cls: 'sw-unread', run: () => pref(c, c.unread ? 'read' : 'unread') }],
            right: [{ key: 'mute', label: c.muted ? t('chats.unmute') : t('chats.mute'), cls: 'sw-mute', run: () => pref(c, c.muted ? 'unmute' : 'mute') },
                    { key: 'del', label: t('chats.delete'), cls: 'sw-del', run: () => remove(c) }],
          }}>
        <Link
          to={`/chat/${c.id}`}
          className={[c.unread ? 'chat-row unread' : 'chat-row', c.id === activeId ? 'active' : '', c.pinned ? 'pinned' : ''].filter(Boolean).join(' ')}
        >
          <div className={c.is_team ? 'chat-thumb is-team' : 'chat-thumb'}>
            {c.is_team
              ? <img src="/logo-mark.png" alt="" />
              : c.listing_photo
                ? <img src={c.listing_photo} alt="" />
                : <div className="photo-placeholder" />}
          </div>
          <div className="chat-row-body">
            <div className="chat-row-top">
              <span className="chat-name">{c.other_name || '—'}
                {c.muted && <svg className="chat-flag" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-label={t('chats.muted')}><path d="M11 5 6 9H2v6h4l5 4V5z" /><path d="m23 9-6 6M17 9l6 6" /></svg>}
              </span>
              <span className="chat-time">{timeAgo(c.last_at, t, i18n.language)}</span>
            </div>
            <div className="chat-listing">{c.listing_title}</div>
            <div className="chat-row-bottom">
              <span className="chat-last">
                {c.last_from_me && <span className="chat-you">{t('chats.you')}: </span>}
                {c.last_kind === 'team' ? plainTeamText(c.last_text) : (c.last_text || t('chats.no_messages'))}
              </span>
              {c.unread > 0 && <span className="chat-badge">{c.unread}</span>}
              {c.pinned && !c.unread && <svg className="chat-flag pin" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-label={t('chats.pinned')}><path d="M16 3a1 1 0 0 1 .7 1.7L15 6.4V10l2.6 2.6a1 1 0 0 1-.7 1.7H13v6l-1 1-1-1v-6H7.1a1 1 0 0 1-.7-1.7L9 10V6.4L7.3 4.7A1 1 0 0 1 8 3h8z" /></svg>}
            </div>
          </div>
        </Link>
        </SwipeRow>
      ))}
    </div>
  )
}

/**
 * Строка переписки со свайпом, как в Telegram: влево — «Без звука» и «Удалить» (длинный свайп — сразу удалить),
 * вправо — «Закрепить» и «Непрочитано». Касание без сдвига — обычный переход в переписку.
 */
function SwipeRow({ actions, children }) {
  const ref = useRef(null)
  const st = useRef({ x0: 0, y0: 0, dx: 0, open: 0, lock: null, moved: false })
  const [dx, setDx] = useState(0)
  const [anim, setAnim] = useState(false)
  const W = 152 // ширина двух кнопок
  const snap = (to) => { setAnim(true); setDx(to); st.current.open = to }
  useEffect(() => {
    // закрыть, если коснулись другой строки
    const close = (e) => { if (st.current.open && ref.current && !ref.current.contains(e.target)) snap(0) }
    document.addEventListener('touchstart', close, { passive: true })
    return () => document.removeEventListener('touchstart', close)
  }, [])
  const onStart = (e) => { const p = e.touches[0]; Object.assign(st.current, { x0: p.clientX, y0: p.clientY, dx: st.current.open, lock: null, moved: false }); setAnim(false) }
  const onMove = (e) => {
    const p = e.touches[0]; const s = st.current
    const mx = p.clientX - s.x0, my = p.clientY - s.y0
    if (s.lock === null && (Math.abs(mx) > 8 || Math.abs(my) > 8)) s.lock = Math.abs(mx) > Math.abs(my) ? 'x' : 'y'
    if (s.lock !== 'x') return
    s.moved = true
    let v = s.open + mx
    if (v > W) v = W + (v - W) * 0.25
    setDx(v)
  }
  const onEnd = () => {
    const s = st.current
    if (s.lock !== 'x') return
    const v = dx
    if (v < -W - 70) { snap(0); actions.right[1].run(); return } // длинный свайп влево — удалить сразу
    if (v < -W / 2) snap(-W)
    else if (v > W / 2) snap(W)
    else snap(0)
  }
  const fire = (a) => { snap(0); a.run() }
  return (
    <div className="sw-row" ref={ref}>
      <div className="sw-actions left" style={{ width: Math.max(0, dx) }}>
        {actions.left.map((a) => <button key={a.key} type="button" className={`sw-btn ${a.cls}`} onClick={() => fire(a)}>{a.label}</button>)}
      </div>
      <div className="sw-actions right" style={{ width: Math.max(0, -dx) }}>
        {actions.right.map((a) => <button key={a.key} type="button" className={`sw-btn ${a.cls}`} onClick={() => fire(a)}>{a.label}</button>)}
      </div>
      <div className={`sw-front${anim ? ' anim' : ''}`} style={{ transform: `translate3d(${dx}px,0,0)` }}
        onTouchStart={onStart} onTouchMove={onMove} onTouchEnd={onEnd}
        onClickCapture={(e) => { if (st.current.moved || st.current.open) { e.preventDefault(); e.stopPropagation(); if (st.current.open) snap(0); st.current.moved = false } }}>
        {children}
      </div>
    </div>
  )
}
