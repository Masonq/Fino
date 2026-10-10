import { goBack } from '../utils/goBack'
import { confirmSheet, promptSheet } from '../utils/confirm'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, chatWsUrl } from '../api/client'
import { useAuth } from '../context/AuthContext'
import ReviewRequest from '../components/ReviewRequest'
import ChatList from '../components/ChatList'
import { ChatSkeleton } from '../components/Skeletons'
import { formatPrice } from '../utils/money'
import teamText from '../utils/teamText'
import useScrollFade from '../hooks/useScrollFade'

export default function ChatScreen() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const { id } = useParams()
  const navigate = useNavigate()
  const myId = user?.id

  const [chat, setChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [messagesLoaded, setMessagesLoaded] = useState(false)
  const quickRef = useScrollFade()
  const [text, setText] = useState('')
  const [typing, setTyping] = useState(false)
  const typingTimer = useRef(0)
  const typingStopTimer = useRef(0)
  const lastTypingSent = useRef(0)
  const wsRef = useRef(null)
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState(null)
  const [blockBusy, setBlockBusy] = useState(false)
  const [callBusy, setCallBusy] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  // Плавающее уведомление про звонок сверху экрана, не строка снизу —
  // закрывается крестиком независимо от самого решения (закрыть — не
  // то же самое, что отклонить: продавец мог просто отвлечься, запрос
  // остаётся висеть, ответить можно и из меню). Сбрасывается, когда
  // само состояние запроса меняется — новый запрос снова покажет
  // уведомление, даже если прошлое уже закрывали.
  const [callNoticeDismissed, setCallNoticeDismissed] = useState(false)
  const [offerOpen, setOfferOpen] = useState(false)
  // Закрыто крестиком — не навсегда, только на этот просмотр чата:
  // тот же принцип, что уже есть у уведомления про звонок
  // (callNoticeDismissed). Пропадает совсем — человек забудет, что
  // вообще можно поторговаться; пропадает до следующего захода —
  // не мешает прямо сейчас, но не теряется как возможность.
  const [offerPillDismissed, setOfferPillDismissed] = useState(false)
  const [offerAmount, setOfferAmount] = useState('')
  const [offerBusy, setOfferBusy] = useState(false)
  const [reserveBusy, setReserveBusy] = useState(false)
  const bottomRef = useRef(null)

  const isSeller = chat?.seller?.id === myId
  // Быстрые ответы: разговор о вещи почти всегда начинается с одних и
  // тех же вопросов. Показываем, пока в поле пусто и последнее слово не
  // за нами — иначе кнопки предлагали бы писать самому себе.
  const lastMsg = messages[messages.length - 1]
  const quickKeys = !chat || chat.is_team || !chat.listing_path || text
    || (lastMsg && lastMsg.sender_id === myId)
    ? []
    : isSeller ? ['yes', 'evening', 'final'] : ['available', 'bargain', 'when', 'where']

  // Новый запрос — снова показываем уведомление, даже если прошлое
  // уже закрывали крестиком: это другое событие, не то же самое.
  useEffect(() => {
    if (chat?.call_request_pending) setCallNoticeDismissed(false)
  }, [chat?.call_request_pending])

  const otherName = () => {
    if (!chat) return ''
    return chat.buyer?.id === myId ? chat.seller?.display_name : chat.buyer?.display_name
  }

  const load = () => {
    api.getChat(id, i18n.language).then(setChat).catch(() => setChat(null))
    api.getChatMessages(id)
      .then(setMessages)
      .catch(() => setMessages([]))
      .finally(() => setMessagesLoaded(true))
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
    // сообщений в новом чате просто переставала работать. То же для
    // messagesLoaded — иначе список сообщений прошлого чата на миг
    // показывался бы как «уже готовый» результат нового.
    // chat — тот же класс, только для шапки, не списка сообщений:
    // {chat && (...)} в разметке ниже защищает от null, но не от
    // УСТАРЕВШЕГО chat — раньше при переходе между двумя чатами имя
    // ПРЕЖНЕГО собеседника оставалось в шапке даже после того, как
    // адрес уже сменился на новый чат, пропадало только когда
    // приходил ответ сервера (проверил настоящим переходом).
    setHasOlder(true)
    setLoadingOlder(false)
    setMessagesLoaded(false)
    setChat(null)
    load()
  // Намеренно: load пересоздаётся на каждой отрисовке: с ним в зависимостях переписка перезагружалась бы бесконечно.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // Живой чат — WebSocket вместо опроса раз в 4 секунды: сообщения,
  // разрешения на звонок, отметки «прочитано» приходят сразу, а не
  // с задержкой до следующего тика. Раньше опрос вдобавок подтягивал
  // только сообщения — chat.phone_revealed/call_request_pending не
  // обновлялись вовсе у собеседника, кнопка «Позвонить» не появлялась,
  // сколько ни жди, до самой перезагрузки страницы.
  useEffect(() => {
    if (!id || !myId) return
    let ws = null
    let reconnectTimer = 0
    let closedByUs = false

    const refreshChatState = () => {
      api.getChat(id, i18n.language).then(setChat).catch(() => {})
    }

    const connect = () => {
      const url = chatWsUrl(id)
      if (!url) return
      ws = new WebSocket(url)
      wsRef.current = ws

      ws.onmessage = (event) => {
        let data
        try { data = JSON.parse(event.data) } catch { return }

        if (data.type === 'message') {
          setMessages((prev) => (
            prev.some((m) => m.id === data.message.id) ? prev : [...prev, data.message]
          ))
          if (data.message.sender_id !== myId) api.markChatRead(id).catch(() => {})
        } else if (data.type === 'message_edited') {
          setMessages((prev) => prev.map((m) => (m.id === data.message_id ? { ...m, text: data.text, edited_at: data.edited_at } : m)))
        } else if (data.type === 'message_deleted') {
          setMessages((prev) => prev.map((m) => (m.id === data.message_id ? { ...m, kind: 'deleted', text: null, audio_url: null, reactions: null } : m)))
        } else if (data.type === 'reaction') {
          setMessages((prev) => prev.map((m) => (m.id === data.message_id ? { ...m, reactions: data.reactions } : m)))
        } else if (data.type === 'typing' && data.user_id !== myId) {
          setTyping(true)
          clearTimeout(typingTimer.current)
          // Если собеседник просто закрыл вкладку, «перестал печатать»
          // не придёт — гасим сами через три секунды.
          typingTimer.current = setTimeout(() => setTyping(false), 3000)
        } else if (data.type === 'typing_stop' && data.user_id !== myId) {
          clearTimeout(typingTimer.current)
          setTyping(false)
        } else if (data.type === 'chat_updated') {
          // Не рассылаем сериализованный чат целиком (он разный для
          // покупателя и продавца — номер телефона видит только один) —
          // просто перечитываем свою версию по сигналу.
          refreshChatState()
        }
      }

      ws.onclose = () => {
        if (closedByUs) return
        // Соединение оборвалось не по нашей воле (сеть моргнула,
        // телефон заснул) — пробуем снова через паузу, не сразу:
        // мгновенный повтор при недоступной сети просто зациклился бы.
        reconnectTimer = setTimeout(connect, 2000)
      }
      ws.onerror = () => { ws?.close() }
    }

    connect()

    // Запасной, редкий опрос — только на случай, если WebSocket в
    // принципе не работает (очень старый браузер, необычный прокси у
    // оператора связи): не даёт чату замереть насовсем, но не спорит
    // с живым каналом, пока тот в порядке.
    const fallbackTick = async () => {
      if (document.hidden) return
      if (ws && ws.readyState === WebSocket.OPEN) return
      try {
        const res = await api.getChatMessages(id)
        setMessages((prev) => {
          if (prev.length === 0) return res
          const known = new Set(prev.map((m) => m.id))
          const fresh = res.filter((m) => !known.has(m.id))
          return fresh.length > 0 ? [...prev, ...fresh] : prev
        })
        refreshChatState()
      } catch { /* следующая попытка через интервал */ }
    }
    const fallbackTimer = setInterval(fallbackTick, 15000)

    return () => {
      closedByUs = true
      ws?.close()
      if (reconnectTimer) clearTimeout(reconnectTimer)
      clearInterval(fallbackTimer)
    }
  // Намеренно: язык здесь не влияет на подписку: пересоздавать соединение при смене языка незачем.
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Сообщаем собеседнику, что печатаем — но не на каждую букву:
  // одно событие в две секунды, и «перестал» через паузу в молчании.
  const notifyTyping = () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const now = Date.now()
    if (now - lastTypingSent.current > 2000) {
      ws.send('typing')
      lastTypingSent.current = now
    }
    clearTimeout(typingStopTimer.current)
    typingStopTimer.current = setTimeout(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('typing_stop')
      lastTypingSent.current = 0
    }, 2500)
  }

  // Готовый текст (быстрый ответ) уходит сразу; иначе берём из поля.
  // Обработчик нажатия передаёт событие — его за текст не считаем.
  // ответ, реакции, перевод — долгим нажатием на сообщение (как в Telegram)
  const [replyTo, setReplyTo] = useState(null)
  const [menuFor, setMenuFor] = useState(null)
  const [translated, setTranslated] = useState({})
  const holdTimer = useRef(null)
  const voiceOk = typeof window !== 'undefined' && !!window.MediaRecorder && !!navigator.mediaDevices?.getUserMedia
  const holdHandlers = (m) => ({
    onContextMenu: (e) => { e.preventDefault(); setMenuFor(m) },
    onTouchStart: () => { clearTimeout(holdTimer.current); holdTimer.current = setTimeout(() => { setMenuFor(m); try { navigator.vibrate?.(12) } catch { /* нет вибрации */ } }, 420) },
    onTouchMove: () => clearTimeout(holdTimer.current),
    onTouchEnd: () => clearTimeout(holdTimer.current),
  })
  const react = (m, emoji) => {
    setMenuFor(null)
    api.reactMessage(id, m.id, emoji).then((r) => setMessages((prev) => prev.map((x) => (x.id === m.id ? { ...x, reactions: r.reactions } : x)))).catch(() => {})
  }
  const doTranslate = (m) => {
    setMenuFor(null)
    if (translated[m.id]) { setTranslated((x) => { const n = { ...x }; delete n[m.id]; return n }); return }
    api.translateMessage(id, m.id, i18n.language).then((r) => setTranslated((x) => ({ ...x, [m.id]: r.text }))).catch(() => setSendError(t('chat.translate_failed')))
  }
  const jumpTo = (mid) => {
    const el = document.querySelector(`[data-mid="${mid}"]`)
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1200) }
  }

  const send = async (ready) => {
    const body = (typeof ready === 'string' ? ready : text).trim()
    if (!body || !myId) return
    setSending(true)
    setSendError(null)
    try {
      await api.sendMessage(id, body, null, replyTo?.id)
      setReplyTo(null)
      if (typeof ready !== 'string') setText('')
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

  // Предложение цены — свой ввод, не общее поле «text»: цифра и
  // обычное сообщение отправляются по-разному (offer_price отдельным
  // полем), смешивать их в одном инпуте только путает.
  const sendOffer = async () => {
    const amount = Number(offerAmount)
    if (!amount || amount <= 0) return
    setOfferBusy(true)
    try {
      await api.sendMessage(id, null, amount)
      setOfferAmount('')
      setOfferOpen(false)
      const res = await api.getChatMessages(id)
      setMessages(res)
    } catch {
      setSendError(t('chat.send_failed'))
    } finally {
      setOfferBusy(false)
    }
  }

  const respondOffer = async (messageId, status) => {
    setOfferBusy(true)
    try {
      await api.respondToOffer(id, messageId, status)
      const res = await api.getChatMessages(id)
      setMessages(res)
    } catch { /* оставляем как было — можно попробовать снова */ }
    finally { setOfferBusy(false) }
  }

  // Бронь — по умолчанию 48 часов, без формы выбора срока: «придержи
  // на пару дней» и есть тот самый частый случай, который и решает
  // эта кнопка. Дольше — редкость, не стоит усложнять первый экран.
  const doReserve = async () => {
    if (!chat) return
    setReserveBusy(true)
    try {
      await api.reserveListing(chat.listing_id, chat.buyer.id, 48)
      const fresh = await api.getChat(id, i18n.language)
      setChat(fresh)
    } catch { /* оставляем как было */ }
    finally { setReserveBusy(false) }
  }

  const cancelReserve = async () => {
    if (!chat) return
    setReserveBusy(true)
    try {
      await api.cancelReservation(chat.listing_id)
      const fresh = await api.getChat(id, i18n.language)
      setChat(fresh)
    } catch { /* оставляем как было */ }
    finally { setReserveBusy(false) }
  }

  const toggleBlock = async () => {
    if (!chat) return
    if (!chat.i_blocked_them && !(await confirmSheet({ title: t('chat.confirm_block'), confirm: t('confirm.block'), danger: true }))) return
    setBlockBusy(true)
    try {
      if (chat.i_blocked_them) await api.unblockChatPartner(id)
      else await api.blockChatPartner(id)
      const fresh = await api.getChat(id, i18n.language)
      setChat(fresh)
    } catch { /* оставляем как было */ }
    finally { setBlockBusy(false) }
  }

  // Три действия вокруг номера телефона — покупатель просит,
  // продавец разрешает или отклоняет (или разрешает сам, без запроса).
  // Все три ведут в одно место: перезагружаем чат целиком, чтобы
  // phone_revealed/call_request_pending — и, если номер раскрылся,
  // сам номер — сразу обновились в одной строке над полем ввода, не
  // дожидаясь следующего опроса раз в 4 секунды.
  const doRequestCall = async () => {
    setCallBusy(true)
    try {
      await api.requestCall(id)
      const [fresh, freshMessages] = await Promise.all([api.getChat(id, i18n.language), api.getChatMessages(id)])
      setChat(fresh); setMessages(freshMessages)
    } catch { /* оставляем как было */ }
    finally { setCallBusy(false) }
  }
  const doAllowCall = async () => {
    setCallBusy(true)
    try {
      await api.allowCall(id)
      const [fresh, freshMessages] = await Promise.all([api.getChat(id, i18n.language), api.getChatMessages(id)])
      setChat(fresh); setMessages(freshMessages)
    } catch { /* оставляем как было */ }
    finally { setCallBusy(false) }
  }
  const doDeclineCall = async () => {
    setCallBusy(true)
    try {
      await api.declineCall(id)
      const [fresh, freshMessages] = await Promise.all([api.getChat(id, i18n.language), api.getChatMessages(id)])
      setChat(fresh); setMessages(freshMessages)
    } catch { /* оставляем как было */ }
    finally { setCallBusy(false) }
  }
  const doRevokeCall = async () => {
    setCallBusy(true)
    try {
      await api.revokeCall(id)
      const [fresh, freshMessages] = await Promise.all([api.getChat(id, i18n.language), api.getChatMessages(id)])
      setChat(fresh); setMessages(freshMessages)
    } catch { /* оставляем как было */ }
    finally { setCallBusy(false) }
  }

  return (
    <div className="chats-layout in-chat">
      <div className="chats-list-pane">
        <ChatList activeId={id} />
      </div>
      <div className="chats-content-pane">
      <div className="chat-page">
      <div className="chat-head">
        <button className="cats-back" onClick={() => goBack(navigate, '/chats')} aria-label={t('actions.back')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        {/* В шапке — только собеседник: заголовок объявления переехал
            в полоску ниже, где он с фотографией, ценой и ссылкой.
            Держать его в двух местах подряд незачем. */}
        <div className="chat-head-who">
          <div className="chat-head-name">{otherName() || '...'}</div>
          {!chat?.listing_path && chat?.listing_title && (
            <div className="chat-head-listing">{chat.listing_title}</div>
          )}
        </div>


        {chat && (
          <div className="chat-head-actions">
            {/* Номер уже раскрыт — вместо кнопки «Позвонить» снизу
                (просили убрать) теперь просто иконка здесь, рядом с
                меню. Только у покупателя — у продавца номера
                собеседника тут никогда нет, см. серверную часть. */}
            {!isSeller && chat.phone_revealed && chat.other_phone && (
              <a className="chat-head-call-btn" href={`tel:${chat.other_phone}`} aria-label={t('chat.call_number', { phone: chat.other_phone })}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
                </svg>
              </a>
            )}
          <div className="chat-menu-wrap">
            {/* У чата с командой в меню нет ни одного пункта — ни
                звонка, ни брони, ни блокировки. Пустая шторка по
                нажатию хуже отсутствия кнопки. */}
            {!chat?.is_team && (
            <button className="chat-menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label={t('chat.menu')}>
              <svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" /></svg>
            </button>
            )}
            {menuOpen && (
              <>
                <div className="chat-menu-backdrop" onClick={() => setMenuOpen(false)} />
                <div className="chat-menu">
                  {/* Покупатель запрашивает звонок — тем же местом, что
                      и у продавца «Разрешить звонок» ниже: одна и та же
                      логика меню для обеих ролей, не отдельный элемент
                      где-то ещё. Пока запрос уже отправлен и висит без
                      ответа — пункт превращается в неактивную подпись,
                      не пропадает совсем (человек должен видеть, что
                      что-то уже сделал, а не гадать, сработало ли). */}
                  {!isSeller && chat.seller_has_phone && !chat.phone_revealed && (
                    chat.call_request_pending ? (
                      <div className="chat-menu-item disabled-note">
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
                        </svg>
                        {t('chat.call_pending')}
                      </div>
                    ) : (
                      <button
                        className="chat-menu-item"
                        disabled={callBusy}
                        onClick={() => { setMenuOpen(false); doRequestCall() }}
                      >
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
                        </svg>
                        {t('chat.call_request')}
                      </button>
                    )
                  )}
                  {/* Проактивное разрешение (без запроса от покупателя) —
                      только продавцу и только пока ещё не разрешено;
                      ответ на уже пришедший запрос — своё плавающее
                      уведомление сверху экрана, не тут. */}
                  {isSeller && chat.seller_has_phone && !chat.phone_revealed && (
                    <button
                      className="chat-menu-item"
                      disabled={callBusy}
                      onClick={() => { setMenuOpen(false); doAllowCall() }}
                    >
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
                      </svg>
                      {t('chat.call_allow_proactive')}
                    </button>
                  )}
                  {isSeller && chat.phone_revealed && (
                    <button
                      className="chat-menu-item"
                      disabled={callBusy}
                      onClick={() => { setMenuOpen(false); doRevokeCall() }}
                    >
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
                        <path d="M4 4l16 16" />
                      </svg>
                      {t('chat.call_revoke')}
                    </button>
                  )}
                  {/* Бронирование — только продавцу, только пока
                      объявление ещё активно (снятое с продажи или уже
                      проданное бронировать нечего). */}
                  {isSeller && chat.listing_status === 'active' && (
                    chat.listing_is_reserved ? (
                      <button
                        className="chat-menu-item"
                        disabled={reserveBusy}
                        onClick={() => { setMenuOpen(false); cancelReserve() }}
                      >
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
                        {t('chat.reservation_cancel')}
                      </button>
                    ) : (
                      <button
                        className="chat-menu-item"
                        disabled={reserveBusy}
                        onClick={() => { setMenuOpen(false); doReserve() }}
                      >
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
                        {t('chat.reserve_for_them')}
                      </button>
                    )
                  )}
                  {/* Команду блокировать нельзя: это единственный канал,
                      которым мы пишем человеку и отвечаем ему. */}
                  {!chat?.is_team && (
                  <button
                    className="chat-menu-item"
                    disabled={blockBusy}
                    onClick={() => { setMenuOpen(false); toggleBlock() }}
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="9" /><path d="m5.5 5.5 13 13" />
                    </svg>
                    {t(chat.i_blocked_them ? 'chat.unblock' : 'chat.block')}
                  </button>
                  )}
                </div>
              </>
            )}
          </div>
          </div>
        )}
      </div>

      {/* Объявление, о котором речь, — полоской под шапкой и со
          ссылкой на него. Переписка тянется днями, и вспомнить, о чём
          она, бывает нечем: имя собеседника ни о чём не говорит, а
          заголовок в шапке не нажимается. Снимок и цена возвращают
          разговор к вещи, а нажатие — к самому объявлению. */}
      {chat?.listing_path && (
        <Link to={chat.listing_path} className="chat-listing-bar">
          <div className="chat-listing-thumb">
            {chat.listing_photo
              ? <img src={chat.listing_photo} alt="" />
              : <div className="photo-placeholder" />}
          </div>
          <div className="chat-listing-text">
            <div className="chat-listing-title">{chat.listing_title}</div>
            <div className="chat-listing-price">
              {chat.listing_is_free
                ? t('detail.free')
                : chat.listing_price != null
                  ? formatPrice(chat.listing_price, chat.listing_currency, i18n.language)
                  : t('detail.no_price')}
              {chat.listing_status === 'sold' && <span className="chat-listing-gone">{t('chat.listing_sold')}</span>}
              {chat.listing_status === 'archived' && <span className="chat-listing-gone">{t('chat.listing_archived')}</span>}
            </div>
          </div>
          <svg className="chat-listing-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      )}

      <div
        className="chat-messages"
        ref={scrollRef}
        onScroll={(e) => { if (e.currentTarget.scrollTop < 60) loadOlder() }}
      >
        {loadingOlder && <p className="empty-hint">{t('actions.loading')}</p>}
        {!messagesLoaded ? (
          <ChatSkeleton />
        ) : (
          <>
            {messages.map((m) => (
              m.kind === 'safety_note' ? (
                /* Памятка о безопасности. Не пугаем и не поучаем: одна
                   фраза о том, как обманывают чаще всего, и как этого
                   не допустить. Стоит первым сообщением, видят оба. */
                <div key={m.id} className="chat-safety-note">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
                       strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5z" />
                    <path d="m9 12 2 2 4-4" />
                  </svg>
                  <span>{t('chat.safety_note')}</span>
                </div>
              ) : m.kind === 'review_request' ? (
                <ReviewRequest
                  key={m.id}
                  chatId={id}
                  targetId={chat?.buyer?.id === myId ? chat?.seller?.id : chat?.buyer?.id}
                  listingId={chat?.listing?.id}
                  targetName={otherName()}
                  onDone={load}
                />
              ) : m.kind === 'call_request' || m.kind === 'call_allowed' || m.kind === 'call_declined' || m.kind === 'call_revoked' ? (
                // Просто запись в истории — вся интерактивность (кнопки
                // разрешить/отклонить/запросить) живёт в одной панели
                // над полем ввода, не тут: два места для одного и того
                // же действия только путают.
                <div key={m.id} className="chat-system-note">
                  {t(`chat.${m.kind}_note`, { name: m.sender_id === myId ? t('chat.you') : otherName() })}
                </div>
              ) : m.kind === 'price_offer' ? (
                // Тут интерактивность прямо на сообщении, не вынесена в
                // отдельную панель, как у звонка: предложений за
                // переписку может быть несколько подряд, кнопки должны
                // относиться к конкретному, а не к «последнему».
                <div key={m.id} className={m.sender_id === myId ? 'chat-offer mine' : 'chat-offer'}>
                  <div className="chat-offer-amount">
                    {t('chat.offer_label')} {formatPrice(m.offer_price, chat?.listing_currency, i18n.language)}
                  </div>
                  {m.offer_status === 'accepted' && (
                    <div className="chat-offer-status accepted">{t('chat.offer_accepted')}</div>
                  )}
                  {m.offer_status === 'declined' && (
                    <div className="chat-offer-status declined">{t('chat.offer_declined')}</div>
                  )}
                  {!m.offer_status && isSeller && m.sender_id !== myId && (
                    <div className="chat-offer-actions">
                      <button disabled={offerBusy} onClick={() => respondOffer(m.id, 'accepted')}>
                        {t('chat.offer_accept')}
                      </button>
                      <button disabled={offerBusy} onClick={() => respondOffer(m.id, 'declined')}>
                        {t('chat.offer_decline')}
                      </button>
                    </div>
                  )}
                  {!m.offer_status && !isSeller && (
                    <div className="chat-offer-status pending">{t('chat.offer_pending')}</div>
                  )}
                </div>
              ) : (
                <div key={m.id} data-mid={m.id} className={m.sender_id === myId ? 'chat-bubble-wrap mine' : 'chat-bubble-wrap'}>
                <div className={`${m.sender_id === myId ? 'chat-bubble mine' : 'chat-bubble'}${menuFor?.id === m.id ? ' is-held' : ''}`}
                  {...holdHandlers(m)}>
                  {m.reply_to && (
                    <button type="button" className="msg-quote" onClick={() => jumpTo(m.reply_to.id)}>
                      <span className="msg-quote-who">{m.reply_to.sender_id === myId ? t('chat.you') : (otherName() || t('chat.them'))}</span>
                      <span className="msg-quote-text">{m.reply_to.text || '🎤'}</span>
                    </button>
                  )}
                  {m.kind === 'deleted' ? <span className="msg-deleted">{t('chat.deleted')}</span>
                    : m.kind === 'voice' ? <VoicePlayer src={m.audio_url} seconds={m.audio_seconds} mine={m.sender_id === myId} />
                    : (m.kind === 'team' ? teamText(m.text) : m.text)}
                  {m.edited_at && m.kind !== 'deleted' && <span className="msg-edited">{t('chat.edited')}</span>}
                  {translated[m.id] && <div className="msg-translated"><span>{t('chat.translated')}</span>{translated[m.id]}</div>}
                  {/* Галочка у своих сообщений: одна — доставлено,
                      две — собеседник открыл чат и прочитал. Без неё
                      переписка ощущается односторонней: написал и не
                      знаешь, видели ли вообще. */}
                  {m.sender_id === myId && (
                    <span className={m.is_read ? 'chat-ticks read' : 'chat-ticks'} aria-hidden="true">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                        <path d="m4 13 4 4 8-9" />
                        {m.is_read && <path d="m12 17 8-9" />}
                      </svg>
                    </span>
                  )}
                </div>

                {/* На что похоже чужое сообщение. Не прячем и не
                    блокируем — те же слова пишет и честный продавец, —
                    но говорим получателю, чего остеречься. Только под
                    чужими: предупреждать человека о его собственных
                    словах глупо. */}
                {Object.keys(m.reactions || {}).length > 0 && (
                  <div className={m.sender_id === myId ? 'msg-reacts mine' : 'msg-reacts'}>
                    {Object.entries(m.reactions).map(([e, who]) => (
                      <button key={e} type="button" className={who.includes(String(myId)) ? 'msg-react on' : 'msg-react'} onClick={() => react(m, e)}>
                        {e}{who.length > 1 && <b>{who.length}</b>}
                      </button>
                    ))}
                  </div>
                )}
                {m.risk && m.sender_id !== myId && (
                  <div className="chat-risk">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"
                         strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 9v4M12 17h.01M10.3 3.9 2.6 17.2a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
                    </svg>
                    <span>{t(`chat.risk_${m.risk}`)}</span>
                  </div>
                )}
                </div>
              )
            ))}
            {messages.length === 0 && <p className="empty-hint">{t('chat.empty')}</p>}
            {menuFor && (
              <div className="msg-menu-backdrop" onClick={() => setMenuFor(null)}>
                <div className="msg-menu" onClick={(e) => e.stopPropagation()} role="menu">
                  <div className="msg-menu-reacts">
                    {['👍', '❤️', '😂', '😮', '🙏', '🔥'].map((e) => (
                      <button key={e} type="button" className={(menuFor.reactions?.[e] || []).includes(String(myId)) ? 'on' : ''} onClick={() => react(menuFor, e)}>{e}</button>
                    ))}
                  </div>
                  <div className="msg-menu-preview">{menuFor.kind === 'voice' ? '🎤' : menuFor.text}</div>
                  <button type="button" className="msg-menu-item" onClick={() => { setReplyTo(menuFor); setMenuFor(null); document.querySelector('.chat-input-row textarea, .chat-input-row input')?.focus() }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 14 4 9l5-5" /><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" /></svg>
                    {t('chat.reply')}
                  </button>
                  {menuFor.kind !== 'voice' && (menuFor.text || '').trim() && (
                    <button type="button" className="msg-menu-item" onClick={() => doTranslate(menuFor)}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 8 6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6" /></svg>
                      {translated[menuFor.id] ? t('chat.untranslate') : t('chat.translate')}
                    </button>
                  )}
                  {menuFor.kind !== 'voice' && (menuFor.text || '').trim() && (
                    <button type="button" className="msg-menu-item" onClick={() => { navigator.clipboard?.writeText(menuFor.text).catch(() => {}); setMenuFor(null) }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="12" height="12" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></svg>
                      {t('chat.copy')}
                    </button>
                  )}
                  {/* своё текстовое сообщение можно исправить — в течение суток, у обоих с пометкой «изменено» */}
                  {menuFor.sender_id === myId && menuFor.kind === 'user' && menuFor.text && (Date.now() - new Date(menuFor.created_at).getTime() < 864e5) && (
                    <button type="button" className="msg-menu-item" onClick={async () => {
                      const m = menuFor; setMenuFor(null)
                      const next = await promptSheet({ title: t('chat.edit_prompt'), value: m.text })
                      if (next == null || !next.trim() || next.trim() === m.text) return
                      setMessages((prev) => prev.map((x) => (x.id === m.id ? { ...x, text: next.trim(), edited_at: new Date().toISOString() } : x)))
                      api.editMessage(id, m.id, next.trim()).catch(() => setMessages((prev) => prev.map((x) => (x.id === m.id ? { ...x, text: m.text, edited_at: m.edited_at } : x))))
                    }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                      {t('chat.edit')}
                    </button>
                  )}
                  {/* своё сообщение можно удалить — у обоих (раньше отправленное было не убрать) */}
                  {menuFor.sender_id === myId && (menuFor.kind === 'user' || menuFor.kind === 'voice') && (
                    <button type="button" className="msg-menu-item danger" onClick={async () => {
                      const m = menuFor; setMenuFor(null)
                      if (!(await confirmSheet({ title: t('chat.delete_confirm'), danger: true }))) return
                      setMessages((prev) => prev.map((x) => (x.id === m.id ? { ...x, kind: 'deleted', text: null, audio_url: null, reactions: null } : x)))
                      api.deleteMessage(id, m.id).catch(() => {})
                    }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" /></svg>
                      {t('chat.delete')}
                    </button>
                  )}
                </div>
              </div>
            )}
          </>
        )}
        {typing && (
          <div className="chat-typing">
            <span /><span /><span />
            {t('chat.typing', { name: otherName() })}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {sendError && <p className="chat-error">{sendError}</p>}

      {/* Плавающее уведомление — прилипает к шапке чата снизу, не к
          самому верху экрана (там системная строка телефона, задевать
          её не нужно). Продавцу — явный выбор «Да»/«Нет», не просто
          подразумеваемое «нажми на текст». Покупателю решать нечего —
          только посмотреть и закрыть крестиком. */}
      {chat && chat.call_request_pending && !callNoticeDismissed && (
        <div className="call-toast">
          <div className="call-toast-text">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
            </svg>
            <span className="call-toast-text-inner">
              {isSeller ? t('chat.call_requested_by_them') : t('chat.call_pending')}
            </span>
          </div>
          {isSeller ? (
            <div className="call-toast-actions">
              <button className="call-toast-yes" disabled={callBusy} onClick={doAllowCall}>
                {t('chat.yes')}
              </button>
              <button className="call-toast-no" disabled={callBusy} onClick={doDeclineCall}>
                {t('chat.no')}
              </button>
            </div>
          ) : (
            <button
              className="call-toast-close"
              aria-label={t('actions.close')}
              onClick={() => setCallNoticeDismissed(true)}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          )}
        </div>
      )}

      {/* Бронь — короткая плашка, без крестика (в отличие от звонка):
          это факт состояния объявления, не разовое уведомление —
          должна быть видна всё время, пока действует. */}
      {chat?.listing_is_reserved && (
        <div className="reservation-banner">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
          {isSeller
            ? t('chat.reservation_active_seller')
            : chat.listing_reserved_for_me
              ? t('chat.reservation_active_for_me')
              : t('chat.reservation_active_other')}
        </div>
      )}

      {chat?.blocked_by_them ? (
        <p className="chat-blocked-notice">{t('chat.you_are_blocked')}</p>
      ) : (
        <>
          {/* Предложить цену — только покупателю, только если продавец
              разрешил торг на самом объявлении. Отдельная маленькая
              панель, раскрывается по кнопке — не отдельная форма на
              весь экран ради одной цифры. */}
          {!isSeller && chat?.listing_price_negotiable && chat?.listing_status === 'active' && !offerPillDismissed && (
            <div className="offer-panel">
              {offerOpen ? (
                <div className="offer-panel-form">
                  <input
                    type="number"
                    inputMode="decimal"
                    value={offerAmount}
                    onChange={(e) => setOfferAmount(e.target.value)}
                    placeholder={t('chat.offer_amount_ph')}
                    autoFocus
                  />
                  <button disabled={offerBusy || !offerAmount} onClick={sendOffer}>{t('chat.offer_send')}</button>
                  <button className="offer-panel-cancel" onClick={() => { setOfferOpen(false); setOfferAmount('') }}>
                    {t('actions.cancel')}
                  </button>
                </div>
              ) : (
                <div className="offer-panel-open-row">
                  <button className="offer-panel-open" onClick={() => setOfferOpen(true)}>
                    {t('chat.offer_open')}
                  </button>
                  <button
                    className="offer-panel-dismiss"
                    onClick={() => setOfferPillDismissed(true)}
                    aria-label={t('actions.close')}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
                  </button>
                </div>
              )}
            </div>
          )}
          {quickKeys.length > 0 && (
            <div className="quick-replies" ref={quickRef} role="group" aria-label={t('chat.quick_label')}>
              {quickKeys.map((key) => (
                <button key={key} disabled={sending} onClick={() => send(t(`chat.quick.${key}`))}>
                  {t(`chat.quick.${key}`)}
                </button>
              ))}
            </div>
          )}
          {replyTo && (
            <div className="reply-bar">
              <div className="reply-bar-body">
                <span className="reply-bar-who">{t('chat.reply_to')} · {replyTo.sender_id === myId ? t('chat.you') : (otherName() || '')}</span>
                <span className="reply-bar-text">{replyTo.kind === 'voice' ? '🎤' : replyTo.text}</span>
              </div>
              <button type="button" className="reply-bar-x" aria-label={t('actions.close')} onClick={() => setReplyTo(null)}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
              </button>
            </div>
          )}
          <div className="chat-input-row">
            <input
              type="text"
              value={text}
              onChange={(e) => { setText(e.target.value); notifyTyping(); if (sendError) setSendError(null) }}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder={t('chat.message_ph')}
            />
{!text.trim() && voiceOk ? (
              <VoiceButton onSend={(blob, secs) => api.sendVoice(id, blob, secs, replyTo?.id).then((msg) => { setReplyTo(null); setMessages((prev) => (prev.some((x) => x.id === msg.id) ? prev : [...prev, msg])) }).catch(() => setSendError(t('chat.send_failed')))} />
            ) : (            <button className="chat-send-btn" disabled={sending || !text.trim()} onClick={send} aria-label={t('actions.send')}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
              </svg>
            </button>)}
          </div>
        </>
      )}
      </div>
      </div>
    </div>
  )
}

/** Кнопка голосового: удерживать — запись (до 2 минут), отпустить — отправить, увести палец в сторону — отмена. */
function VoiceButton({ onSend }) {
  const { t } = useTranslation()
  const [rec, setRec] = useState(null) // { mr, st }
  const [secs, setSecs] = useState(0)
  const [note, setNote] = useState('')
  const cancelRef = useRef(false)
  const pressed = useRef(false)     // палец/кнопка мыши всё ещё зажаты
  const recRef = useRef(null)
  const timer = useRef(null)
  const say = (msg) => { setNote(msg); setTimeout(() => setNote(''), 2600) }

  const start = async () => {
    pressed.current = true
    cancelRef.current = false
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      pressed.current = false
      say(e?.name === 'NotAllowedError' ? t('chat.mic_denied') : t('chat.mic_failed'))
      return
    }
    // Микрофон открывается не мгновенно, а в первый раз iPhone ещё и спрашивает разрешение (палец при этом
    // «отпускается»). Если кнопку уже отпустили — ничего не записываем, просто подсказываем удерживать.
    if (!pressed.current) {
      stream.getTracks().forEach((tr) => tr.stop())
      say(t('chat.hold_hint'))
      return
    }
    // iPhone пишет mp4/aac (его же и проигрывают все), остальные — webm/opus
    const type = ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm'].find((x) => MediaRecorder.isTypeSupported?.(x)) || ''
    const mr = new MediaRecorder(stream, type ? { mimeType: type } : undefined)
    const chunks = []
    mr.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
    const st = Date.now()
    mr.onstop = () => {
      stream.getTracks().forEach((tr) => tr.stop())
      const dur = (Date.now() - st) / 1000
      if (cancelRef.current) return
      if (dur < 0.8 || !chunks.length) { say(t('chat.hold_hint')); return }
      onSend(new Blob(chunks, { type: mr.mimeType || type || 'audio/webm' }), dur)
    }
    mr.start(250)
    recRef.current = { mr, st }
    setRec({ mr, st }); setSecs(0)
    timer.current = setInterval(() => { const s2 = Math.round((Date.now() - st) / 1000); setSecs(s2); if (s2 >= 120) stop() }, 250)
    try { navigator.vibrate?.(10) } catch { /* нет вибрации */ }
  }
  const stop = () => {
    pressed.current = false
    clearInterval(timer.current)
    const r = recRef.current
    recRef.current = null
    if (r && r.mr.state !== 'inactive') r.mr.stop()
    setRec(null)
  }
  return (
    <>
      {rec && <div className="voice-rec"><span className="voice-dot" />{Math.floor(secs / 60)}:{String(secs % 60).padStart(2, '0')}<span className="voice-hint">{t('chat.release_to_send')}</span></div>}
      {!rec && note && <div className="voice-rec voice-note">{note}</div>}
      <button type="button" className={rec ? 'chat-voice-btn on' : 'chat-voice-btn'} aria-label={t('chat.hold_to_record')}
        onTouchStart={(e) => { e.preventDefault(); start() }} onTouchEnd={stop} onTouchCancel={stop}
        onTouchMove={(e) => { const tch = e.touches[0]; const r = e.currentTarget.getBoundingClientRect(); if (tch.clientX < r.left - 80) { cancelRef.current = true; stop() } }}
        onMouseDown={start} onMouseUp={stop} onMouseLeave={() => { if (recRef.current) stop() }}
        onContextMenu={(e) => e.preventDefault()}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
      </button>
    </>
  )
}

/** Голосовое сообщение: кнопка «играть», полоска прогресса и длительность. */
function VoicePlayer({ src, seconds, mine }) {
  const a = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [pos, setPos] = useState(0)
  const dur = seconds || 1
  return (
    <div className={mine ? 'voice mine' : 'voice'}>
      <button type="button" className="voice-play" onClick={() => { const el = a.current; if (!el) return; if (el.paused) el.play().catch(() => {}); else el.pause() }}>
        {playing ? <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
          : <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.5.9l10-6.5a1 1 0 0 0 0-1.7l-10-6.5A1 1 0 0 0 8 5.5z" /></svg>}
      </button>
      <span className="voice-track"><span className="voice-fill" style={{ width: `${Math.min(100, (pos / dur) * 100)}%` }} /></span>
      <span className="voice-time">{Math.floor(dur / 60)}:{String(Math.round(dur % 60)).padStart(2, '0')}</span>
      <audio ref={a} src={src} preload="none" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => { setPlaying(false); setPos(0) }} onTimeUpdate={(e) => setPos(e.currentTarget.currentTime)} />
    </div>
  )
}
