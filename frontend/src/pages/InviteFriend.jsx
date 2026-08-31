import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

export default function InviteFriend() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.myReferrals().then(setStats).catch(() => setStats(null))
  }, [])

  // Короткий код — первые 8 символов id, тот же приём, что уже
  // используется для ссылок на объявления (см. seo.py на бэкенде) —
  // не весь UUID, а то ссылка получалась на километр длиной.
  const link = user ? `${window.location.origin}/?ref=${user.id.slice(0, 8)}` : ''

  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: t('invite.share_title'), url: link }) } catch { /* закрыл меню сам — не ошибка */ }
      return
    }
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* буфер недоступен — редкий случай, молча ничего не делаем */ }
  }

  return (
    <div className="fav-page invite-page">
      <PageHeader title={t('invite.title')} />

      <div className="invite-hero">
        <div className="invite-hero-icon">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg>
        </div>
        <h2>{t('invite.hero_title')}</h2>
        <p>{t('invite.hero_text', { amount: 100 })}</p>
      </div>

      <div className="invite-link-row">
        <span className="invite-link-text">{link}</span>
      </div>
      <button type="button" className="invite-share-btn" onClick={share}>
        {copied ? t('invite.copied') : t('invite.share_btn')}
      </button>

      {stats && stats.invited_total > 0 && (
        <div className="invite-stats">
          <div className="invite-stat">
            <b>{stats.invited_total}</b>
            <span>{t('invite.stat_invited')}</span>
          </div>
          <div className="invite-stat">
            <b>{stats.invited_rewarded}</b>
            <span>{t('invite.stat_rewarded')}</span>
          </div>
        </div>
      )}

      <p className="invite-fineprint">{t('invite.fineprint')}</p>
    </div>
  )
}
