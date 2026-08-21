import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

export default function Identify() {
  const { t } = useTranslation()
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
      <button className="post-back" onClick={() => navigate(-1)}>← {t('actions.back')}</button>
      <h2>{t('identify.title')}</h2>
      <p className="empty-hint" style={{ margin: '4px 0 20px' }}>{t('identify.subtitle')}</p>

      <div className="post-fields">
        <div className="post-field">
          <label>{t('post.phone')}</label>
          <input type="tel" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+381 6..." />
        </div>
        <div className="post-field">
          <label>{t('post.name')}</label>
          <input type="text" autoComplete="name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder={t('identify.name_ph')} />
        </div>
      </div>

      <button className="post-submit-btn" disabled={!phone || !displayName || loading} onClick={submit}>
        {loading ? '...' : t('actions.continue')}
      </button>
    </div>
  )
}
