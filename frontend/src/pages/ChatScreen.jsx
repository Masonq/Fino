import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api, chatWsUrl } from '../api/client'
import { useAuth } from '../context/AuthContext'
import ReviewRequest from '../components/ReviewRequest'
import ChatList from '../components/ChatList'
import { ChatSkeleton } from '../components/Skeletons'
import { formatPrice } from '../utils/money'

export default function ChatScreen() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const { id } = useParams()
  const navigate = useNavigate()
  const myId = user?.id

  const [chat, setChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [messagesLoaded, setMessagesLoaded] = useState(false)
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
    if (!chat.i_blocked_them && !window.confirm(t('chat.confirm_block'))) return
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
        <button className="cats-back" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
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
            <button className="chat-menu-btn" onClick={() => setMenuOpen((v) => !v)} aria-label={t('chat.menu')}>
              <svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" /></svg>
            </button>
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
                <div key={m.id} className={m.sender_id === myId ? 'chat-bubble mine' : 'chat-bubble'}>
                  {m.text}
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
              )
            ))}
            {messages.length === 0 && <p className="empty-hint">{t('chat.empty')}</p>}
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
          <div className="chat-input-row">
            <input
              type="text"
              value={text}
              onChange={(e) => { setText(e.target.value); notifyTyping(); if (sendError) setSendError(null) }}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder={t('chat.message_ph')}
            />
            <button className="chat-send-btn" disabled={sending || !text.trim()} onClick={send} aria-label={t('actions.send')}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
              </svg>
            </button>
          </div>
        </>
      )}
      </div>
      </div>
    </div>
  )
}
