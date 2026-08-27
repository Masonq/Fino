import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import ReviewRequest from '../components/ReviewRequest'

export default function ChatScreen() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const { id } = useParams()
  const navigate = useNavigate()
  const myId = user?.id

  const [chat, setChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState(null)
  const bottomRef = useRef(null)

  const otherName = () => {
    if (!chat) return ''
    return chat.buyer?.id === myId ? chat.seller?.display_name : chat.buyer?.display_name
  }

  const load = () => {
    api.getChat(id, i18n.language).then(setChat).catch(() => setChat(null))
    api.getChatMessages(id).then(setMessages).catch(() => setMessages([]))
  }

  // помечаем сообщения собеседника прочитанными при открытии переписки
  useEffect(() => {
    if (!id || !myId) return
    api.markChatRead(id).catch(() => {})
  }, [id, myId])

  useEffect(() => {
    // Сбрасываем — иначе переход из одного чата сразу в другой (без
    // перезагрузки страницы) нёс за собой состояние прошлого: если там
    // долистали до конца истории (hasOlder=false), подгрузка старых
    // сообщений в новом чате просто переставала работать.
    setHasOlder(true)
    setLoadingOlder(false)
    load()
  }, [id])

  // Новые сообщения подтягиваются сами. Опрос вместо постоянного соединения:
  // проще и надёжнее на мобильном, где связь часто рвётся. Пока вкладка скрыта —
  // не опрашиваем, чтобы не тратить батарею и трафик.
  useEffect(() => {
    if (!id || !myId) return
    let timer = 0

    const tick = async () => {
      if (document.hidden) return
      try {
        const res = await api.getChatMessages(id)
        // Опрос возвращает только последние сообщения — дописываем новые,
        // а не заменяем список целиком, иначе подгруженная история пропадёт.
        setMessages((prev) => {
          if (prev.length === 0) return res
          const known = new Set(prev.map((m) => m.id))
          const fresh = res.filter((m) => !known.has(m.id))
          return fresh.length > 0 ? [...prev, ...fresh] : prev
        })
        // пришло чужое — сразу помечаем прочитанным, раз чат открыт
        if (res.some((m) => m.sender_id !== myId && !m.is_read)) {
          api.markChatRead(id).catch(() => {})
        }
      } catch { /* следующая попытка через интервал */ }
    }

    timer = setInterval(tick, 4000)
    const onVisible = () => { if (!document.hidden) tick() }
    document.addEventListener('visibilitychange', onVisible)

    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', onVisible) }
  }, [id, myId])

  const [loadingOlder, setLoadingOlder] = useState(false)
  const [hasOlder, setHasOlder] = useState(true)
  const scrollRef = useRef(null)

  // Старые сообщения подгружаются при прокрутке вверх: сразу грузим
  // только последние, иначе длинная переписка открывается секундами.
  const loadOlder = async () => {
    if (loadingOlder || !hasOlder || messages.length === 0) return
    setLoadingOlder(true)
    const box = scrollRef.current
    const before = messages[0]?.created_at
    const heightBefore = box?.scrollHeight || 0
    try {
      const older = await api.getChatMessages(id, before)
      if (older.length === 0) { setHasOlder(false); return }
      setMessages((prev) => [...older, ...prev])
      // сохраняем положение: иначе список прыгает под пальцем
      requestAnimationFrame(() => {
        if (box) box.scrollTop = box.scrollHeight - heightBefore
      })
    } catch { /* попробуем в следующий раз */ }
    finally { setLoadingOlder(false) }
  }

  const prevCount = useRef(0)
  useEffect(() => {
    if (messages.length !== prevCount.current) {
      prevCount.current = messages.length
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const send = async () => {
    if (!text.trim() || !myId) return
    setSending(true)
    setSendError(null)
    try {
      await api.sendMessage(id, text.trim())
      setText('')
      const res = await api.getChatMessages(id)
      setMessages(res)
    } catch {
      // Текст остаётся в поле — человек не должен набирать заново то,
      // что просто не ушло.
      setSendError(t('chat.send_failed'))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-head">
        <button className="cats-back" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div>
          <div className="chat-head-name">{otherName() || '...'}</div>
          {chat?.listing_title && <div className="chat-head-listing">{chat.listing_title}</div>}
        </div>
      </div>

      <div
        className="chat-messages"
        ref={scrollRef}
        onScroll={(e) => { if (e.currentTarget.scrollTop < 60) loadOlder() }}
      >
        {loadingOlder && <p className="empty-hint">{t('actions.loading')}</p>}
        {messages.map((m) => (
          m.kind === 'review_request' ? (
            <ReviewRequest
              key={m.id}
              chatId={id}
              targetId={chat?.buyer?.id === myId ? chat?.seller?.id : chat?.buyer?.id}
              listingId={chat?.listing?.id}
              targetName={otherName()}
              onDone={load}
            />
          ) : (
            <div key={m.id} className={m.sender_id === myId ? 'chat-bubble mine' : 'chat-bubble'}>
              {m.text}
            </div>
          )
        ))}
        {messages.length === 0 && <p className="empty-hint">{t('chat.empty')}</p>}
        <div ref={bottomRef} />
      </div>

      {sendError && <p className="chat-error">{sendError}</p>}
      <div className="chat-input-row">
        <input
          type="text"
          value={text}
          onChange={(e) => { setText(e.target.value); if (sendError) setSendError(null) }}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder={t('chat.message_ph')}
        />
        <button className="chat-send-btn" disabled={sending || !text.trim()} onClick={send} aria-label={t('actions.send')}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
