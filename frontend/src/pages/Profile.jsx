import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

export default function Profile() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, loading, signOut } = useAuth()

  if (loading) {
    return <div className="fav-page"><PageHeader title={t('nav.profile')} back={false} /></div>
  }

  if (!user) {
    return (
      <div className="fav-page">
        <PageHeader title={t('nav.profile')} back={false} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" />
            </svg>
          </div>
          <p>{t('auth.subtitle')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fprofile')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  const initial = (user.display_name || '?').trim().charAt(0).toUpperCase()

  return (
    <div className="fav-page">
      <PageHeader title={t('nav.profile')} back={false} />

      <div className="profile-head">
        <div className="profile-avatar">
          {user.avatar_url ? <img src={user.avatar_url} alt="" /> : initial}
        </div>
        <div className="profile-info">
          <div className="profile-name">{user.display_name}</div>
          {user.email && <div className="profile-contact">{user.email}</div>}
          {user.phone && <div className="profile-contact">{user.phone}</div>}
        </div>
      </div>

      <div className="profile-menu">
        <Link className="profile-row" to="/favorites">
          {t('nav.favorites')}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/chats">
          {t('nav.chats')}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/my">
          {t('my.title')}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/post">
          {t('nav.post')}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      <button
        className="profile-logout"
        onClick={() => { signOut(); navigate('/') }}
      >
        {t('auth.logout')}
      </button>
    </div>
  )
}
