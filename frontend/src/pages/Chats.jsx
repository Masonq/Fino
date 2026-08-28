import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import ChatList from '../components/ChatList'

export default function Chats() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  if (!user) {
    return (
      <div className="fav-page">
        <PageHeader title={t('nav.chats')} back={false} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />
            </svg>
          </div>
          <p>{t('chats.need_auth')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fchats')}>
            {t('actions.continue')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page">
      <PageHeader title={t('nav.chats')} back={false} />

      {/* На десктопе список — левая колонка постоянно открытой
          двухпанельной переписки (см. .chats-layout в styles.css и
          ChatScreen.jsx, где та же колонка встаёт рядом с открытым
          чатом). Здесь же, пока чат не выбран, справа — просто
          приглашение выбрать переписку, а не пустое место. */}
      <div className="chats-layout">
        <div className="chats-list-pane">
          <ChatList />
        </div>
        <div className="chats-content-pane chats-placeholder">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.6L4 21l1.4-4a8 8 0 0 1-1.4-4.6A8 8 0 0 1 12.5 4a8 8 0 0 1 8 8Z" />
            </svg>
          </div>
          <p>{t('chats.pick_one')}</p>
        </div>
      </div>
    </div>
  )
}
