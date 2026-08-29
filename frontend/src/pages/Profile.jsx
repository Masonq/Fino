import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { ProfileSkeleton } from '../components/Skeletons'
import NotificationBell from '../components/NotificationBell'
import LanguageSwitcher from '../components/LanguageSwitcher'
import BalanceCard from '../components/BalanceCard'

export default function Profile() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, loading, signOut } = useAuth()

  if (loading) {
    return (
      <div className="fav-page profile-page">
        <PageHeader title={t('nav.profile')} back={false} />
        <ProfileSkeleton />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="fav-page profile-page">
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

  const initial = ((user.company_name || user.display_name) || '?').trim().charAt(0).toUpperCase()
  const isCompany = user.role === 'seller_business'

  return (
    <div className="fav-page profile-page">
      <PageHeader title={t('nav.profile')} back={false}>
        <NotificationBell />
      </PageHeader>

      <div className="profile-head-card">
        {/* Место под декоративную картинку — «обложка» профиля, тем же
            принципом, что и у популярных приложений. Пока просто
            градиент тем же зелёным, что и весь сайт — заменится
            настоящей картинкой, как только она будет готова. Высота
            подобрана и вот-вот будет измерена по-настоящему через
            рендер, не на глаз. */}
        <div className="profile-banner" />
        <div className="profile-head">
          <div className={isCompany ? 'profile-avatar is-company' : 'profile-avatar'}>
            {user.avatar_url ? <img src={user.avatar_url} alt="" /> : initial}
          </div>
          <div className="profile-info">
            <div className="profile-name">{user.company_name || user.display_name}</div>
            {isCompany && <div className="seller-badge">{t('seller.company_badge')}</div>}
            {user.email && <div className="profile-contact">{user.email}</div>}
            {user.phone && <div className="profile-contact">{user.phone}</div>}
            {/* Рейтинг — то, по чему покупатель судит о продавце. Прятать
                его от самого продавца странно: он должен видеть, как
                выглядит со стороны. */}
            <div className="profile-rating">
              {user.rating_count
                ? t('edit_profile.rating', {
                  value: user.rating_avg, count: user.rating_count,
                })
                : t('edit_profile.no_rating')}
            </div>
          </div>
        </div>
        <Link className="profile-edit-btn" to="/profile/edit">
          {t('edit_profile.edit')}
        </Link>
      </div>

      <BalanceCard />

      {/* Раньше все десять пунктов шли одним плоским списком без единой
          зацепки, что где искать, — теперь три смысловые группы, у
          каждого пункта своя иконка вместо одинаковой стрелочки.
          «Разместить», «Избранное», «Сообщения» отсюда убраны — они
          уже есть в нижнем меню на каждом экране, дублировать незачем. */}
      <div className="profile-section-title">{t('profile.sec_listings')}</div>
      <div className="profile-menu">
        <Link className="profile-row" to="/my">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><rect x="3" y="4" width="18" height="17" rx="2.5" /><path d="M7 9h10M7 13h10M7 17h6" /></svg>
          </span>
          {t('my.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/saved">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m20 20-4.35-4.35" /></svg>
          </span>
          {t('saved.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      <div className="profile-section-title">{t('profile.sec_activity')}</div>
      <div className="profile-menu">
        <Link className="profile-row" to="/history">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></svg>
          </span>
          {t('history.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      <div className="profile-section-title">{t('profile.sec_settings')}</div>
      <div className="profile-menu">
        <div className="profile-row profile-row-static">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.5 4 5.7 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.7-4-9s1.5-6.5 4-9Z" /></svg>
          </span>
          {t('profile.language')}
          <LanguageSwitcher variant="light" />
        </div>
        <Link className="profile-row" to="/profile/blocked">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="m5.5 5.5 13 13" /></svg>
          </span>
          {t('blocked.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      <div className="profile-section-title">{t('profile.sec_info')}</div>
      <div className="profile-menu">
        <Link className="profile-row" to="/support">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 16v.01M12 13c0-1.8 2-1.8 2-3.5A2 2 0 0 0 12 7.5 2 2 0 0 0 10 9.5" /></svg>
          </span>
          {t('support.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/rules">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M9 12h6M9 16h6M9 8h1" /><rect x="4" y="3" width="16" height="18" rx="2" /></svg>
          </span>
          {t('nav.rules')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/terms">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M6 2.5h9l3 3V21H6V2.5Z" /><path d="M9 9h6M9 13h6M9 17h4" /></svg>
          </span>
          {t('nav.terms')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/privacy">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M12 2.5 4.5 5.5v6c0 5 3.2 8 7.5 10 4.3-2 7.5-5 7.5-10v-6L12 2.5Z" /></svg>
          </span>
          {t('nav.privacy')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      {/* Разделы для сотрудников. Раньше в модерацию заходили по адресу,
          который надо было помнить наизусть. */}
      {(user.role === 'moderator' || user.role === 'admin') && (
        <>
          <div className="profile-section-title">{t('admin.staff')}</div>
          <div className="profile-menu">
            <Link className="profile-row" to="/moderation">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M20 6 9 17l-5-5" /></svg>
              </span>
              {t('admin.moderation')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/users">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="9" cy="8" r="3.3" /><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 8.5a3 3 0 1 1 3.6 3M21.5 20c0-2.8-2-5-4.7-5.7" /></svg>
              </span>
              {t('admin.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/stats">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M4 20V10M12 20V4M20 20v-7" /></svg>
              </span>
              {t('stats.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/audit">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M6 2.5h9l3 3V21H6V2.5Z" /><path d="M9 9h6M9 13h6M9 17h4" /></svg>
              </span>
              {t('audit.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/support">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 16v.01M12 13c0-1.8 2-1.8 2-3.5A2 2 0 0 0 12 7.5 2 2 0 0 0 10 9.5" /></svg>
              </span>
              {t('support.queue')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
          </div>
        </>
      )}

      <button
        className="profile-logout"
        onClick={() => { signOut(); navigate('/') }}
      >
        {t('auth.logout')}
      </button>
    </div>
  )
}
