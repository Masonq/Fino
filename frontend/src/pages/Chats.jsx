import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import ChatList from '../components/ChatList'
import useScrollFade from '../hooks/useScrollFade'

export default function Chats() {
  const chipsRef = useScrollFade()
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  // Поиск и отбор нужны, когда есть что отбирать: при пустом списке
  // они только занимают верх экрана.
  const [count, setCount] = useState(null)
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  if (!user) {
    return (
      <div className="fav-page chats-page">
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
    <div className="fav-page chats-page">
      <PageHeader title={t('nav.chats')} back={false} />

      {/* На десктопе список — левая колонка постоянно открытой
          двухпанельной переписки (см. .chats-layout в styles.css и
          ChatScreen.jsx, где та же колонка встаёт рядом с открытым
          чатом). Здесь же, пока чат не выбран, справа — просто
          приглашение выбрать переписку, а не пустое место. */}
      {/* Поиск и отбор — как в любом мессенджере: когда переписок
          больше десятка, найти нужную по памяти уже не выходит.
          «Непрочитанные» отдельно, потому что это главный вопрос при
          заходе: где мне не ответили. «Покупаю» и «Продаю» — вместо
          «Важных» у Avito: у нас две роли, и они и есть разные дела. */}
      {count > 0 && (
      <div className="chats-tools">
        <div className="chats-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m20 20-4.35-4.35" /></svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('chats.search_ph')}
            aria-label={t('chats.search_ph')}
          />
          {query && (
            <button className="chats-search-clear" onClick={() => setQuery('')} aria-label={t('actions.clear')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="m6 6 12 12M18 6 6 18" /></svg>
            </button>
          )}
        </div>
        <div className="field-chips chats-chips" ref={chipsRef}>
          {['all', 'unread', 'buying', 'selling'].map((key) => (
            <button
              key={key}
              className={filter === key ? 'chip chip-active' : 'chip'}
              onClick={() => setFilter(key)}
            >
              {t(`chats.filter_${key}`)}
            </button>
          ))}
        </div>
      </div>
      )}

      <div className="chats-layout">
        <div className="chats-list-pane">
          <ChatList query={query} filter={filter} onLoaded={setCount} />
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
