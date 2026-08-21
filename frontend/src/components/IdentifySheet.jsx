import { useState } from 'react'
import { api } from '../api/client'

export default function IdentifySheet({ onDone, onClose }) {
  const [phone, setPhone] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    try {
      const user = await api.quickIdentify(phone, displayName)
      localStorage.setItem('fino_user_id', user.id)
      onDone(user.id)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <button className="sheet-close" onClick={onClose} aria-label="Закрыть">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
        <h3>Как к вам обращаться?</h3>
        <p className="empty-hint" style={{ margin: '4px 0 16px' }}>Нужно, чтобы продавец знал, кто пишет</p>
        <div className="post-fields">
          <div className="post-field">
            <label>Телефон</label>
            <input type="tel" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+381 6..." autoFocus />
          </div>
          <div className="post-field">
            <label>Имя</label>
            <input type="text" autoComplete="name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Ваше имя" />
          </div>
        </div>
        <button className="post-submit-btn" disabled={!phone || !displayName || loading} onClick={submit}>
          {loading ? '...' : 'Продолжить'}
        </button>
      </div>
    </div>
  )
}
