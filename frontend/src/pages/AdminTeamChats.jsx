import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'
import { timeAgo } from '../utils/time'
import teamText from '../utils/teamText'

/*
 * Ответы людей на письмо от команды. Войти в аккаунт «Команда PLONK»
 * нельзя, поэтому переписка читается и пишется отсюда.
 */
export default function AdminTeamChats() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [onlyUnread, setOnlyUnread] = useState(true)
  const [items, setItems] = useState([])
  const [unread, setUnread] = useState(0)
  const [openId, setOpenId] = useState(null)
  const [thread, setThread] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)

  const load = useCallback(() => {
    setLoaded(false)
    api.teamChats({ only_unread: onlyUnread })
      .then((res) => { setItems(res.items || []); setUnread(res.unread || 0); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [onlyUnread])

  const userId = user?.id
  useEffect(() => {
    if (authLoading) return
    if (!userId) { navigate('/login', { replace: true }); return }
    load()
  }, [authLoading, userId, load, navigate])

  const open = async (id) => {
    if (openId === id) { setOpenId(null); setThread(null); return }
    setOpenId(id); setThread(null)
    try { setThread(await api.teamChat(id)) } catch { setThread({ error: true }) }
  }

  const send = async (id) => {
    if (!draft.trim()) return
    setBusy(true)
    try {
      await api.teamChatReply(id, draft.trim())
      setDraft('')
      setThread(await api.teamChat(id))
      load()
    } catch { alert(t('support.failed')) }
    finally { setBusy(false) }
  }

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('team_inbox.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-support">
      <PageHeader title={t('team_inbox.title')} />

      <div className="admin-bar">
        <div className="admin-chips">
          <button className={`chip ${onlyUnread ? 'chip-active' : ''}`} onClick={() => setOnlyUnread(true)}>
            {t('team_inbox.unread')}
            {unread ? <b>{unread}</b> : null}
          </button>
          <button className={`chip ${onlyUnread ? '' : 'chip-active'}`} onClick={() => setOnlyUnread(false)}>
            {t('team_inbox.all')}
          </button>
        </div>
      </div>
      <div className="admin-list">
        {!loaded && <AdminRowSkeletons count={4} />}
        {items.map((c) => (
          <div key={c.id} className="admin-row">
            <button className="admin-row-main" onClick={() => open(c.id)}>
              <div className="admin-row-name">
                <span className="name-text">{c.person?.name || '—'}</span>
                {c.unread > 0 && <span className="tag tag-new">{c.unread}</span>}
              </div>
              <div className="admin-row-meta team-row-last">
                {c.last_from_team && <span>{t('chats.you')}: </span>}
                {(c.last_text || '').replace(/[#*]/g, '').replace(/\s+/g, ' ').slice(0, 70)}
                {' · '}{timeAgo(c.last_at, t, i18n.language)}
              </div>
            </button>

            {openId === c.id && (
              <div className="admin-card">
                {!thread && <p className="empty">{t('admin.loading')}</p>}
                {thread?.error && <p className="empty">{t('admin.card_error')}</p>}
                {thread && !thread.error && (
                  <>
                    <div className="support-thread">
                      {thread.messages.map((m) => (
                        <div key={m.id} className={`support-msg ${m.from_team ? 'from-staff' : ''}`}>
                          {m.kind === 'team' ? teamText(m.text) : m.text}
                        </div>
                      ))}
                    </div>
                    <input
                      className="field-input"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      placeholder={t('team_inbox.reply_ph')}
                    />
                    <div className="admin-actions">
                      <button disabled={busy || !draft.trim()} onClick={() => send(c.id)}>
                        {t('support.send')}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      {loaded && !items.length && (
        <div className="admin-empty">
          <span className="admin-empty-title">{t('team_inbox.empty')}</span>
          <span className="admin-empty-text">{t('team_inbox.empty_hint')}</span>
        </div>
      )}
    </div>
  )
}
