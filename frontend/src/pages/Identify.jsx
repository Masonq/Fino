import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

export default function Identify() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const returnTo = params.get('returnTo') || '/'

  const [phone, setPhone] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true)
    try {
      const user = await api.quickIdentify(phone, displayName)
      localStorage.setItem('fino_user_id', user.id)
      navigate(`${returnTo}${returnTo.includes('?') ? '&' : '?'}identified=1`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="post-ad-page">
      <button className="post-back" onClick={() => navigate(-1)}>← Назад</button>
      <h2>Как к вам обращаться?</h2>
      <p className="empty-hint" style={{ margin: '4px 0 20px' }}>Нужно, чтобы продавец знал, кто пишет</p>

      <div className="post-fields">
        <div className="post-field">
          <label>Телефон</label>
          <input type="tel" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+381 6..." />
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
  )
}
