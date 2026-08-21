import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export default function ChatScreen() {
  const { id } = useParams()
  const navigate = useNavigate()
  const myId = localStorage.getItem('fino_user_id')

  const [chat, setChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)

  const otherName = () => {
    if (!chat) return ''
    return chat.buyer?.id === myId ? chat.seller?.display_name : chat.buyer?.display_name
  }

  const load = () => {
    api.getChat(id).then(setChat).catch(() => setChat(null))
    api.getChatMessages(id).then(setMessages).catch(() => setMessages([]))
  }

  useEffect(() => { load() }, [id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    if (!text.trim() || !myId) return
    setSending(true)
    try {
      await api.sendMessage(id, myId, text.trim())
      setText('')
      const res = await api.getChatMessages(id)
      setMessages(res)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-head">
        <button className="cats-back" onClick={() => navigate(-1)} aria-label="Назад">←</button>
        <div>
          <div className="chat-head-name">{otherName() || '...'}</div>
          {chat?.listing_title && <div className="chat-head-listing">{chat.listing_title}</div>}
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((m) => (
          <div key={m.id} className={m.sender_id === myId ? 'chat-bubble mine' : 'chat-bubble'}>
            {m.text}
          </div>
        ))}
        {messages.length === 0 && <p className="empty-hint">Сообщений пока нет — начните разговор</p>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Написать сообщение..."
        />
        <button className="chat-send-btn" disabled={sending || !text.trim()} onClick={send} aria-label="Отправить">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
