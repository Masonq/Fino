import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

const TABS = [
  { key: 'open', label: 'support.status.open' },
  { key: 'answered', label: 'support.status.answered' },
  { key: 'closed', label: 'support.status.closed' },
]

export default function AdminSupport() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [tab, setTab] = useState('open')
  const [items, setItems] = useState([])
  const [counts, setCounts] = useState({})
  const [openId, setOpenId] = useState(null)
  const [card, setCard] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)

  const load = useCallback(() => {
    api.supportQueue({ status: tab, limit: 100 })
      .then((res) => {
        setItems(res.items || [])
        setCounts(res.counts || {})
        setDenied(false)
      })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [tab])

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }
    load()
  }, [authLoading, user, load, navigate])

  const openCard = async (id) => {
    if (openId === id) { setOpenId(null); setCard(null); return }
    setOpenId(id); setCard(null); setDraft('')
    try { setCard(await api.supportTicket(id)) } catch { setCard({ error: true }) }
  }

  const answer = async (id) => {
    if (!draft.trim()) return
    setBusy(true)
    try {
      await api.supportAnswer(id, draft.trim())
      setDraft('')
      setCard(await api.supportTicket(id))
      load()
    } catch { alert(t('support.failed')) }
    finally { setBusy(false) }
  }

  const close = async (id) => {
    setBusy(true)
    try {
      await api.supportClose(id)
      setOpenId(null); setCard(null)
      load()
    } catch { alert(t('support.failed')) }
    finally { setBusy(false) }
  }

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('support.queue')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-support">
      <PageHeader title={t('support.queue')} />

      <div className="admin-filters">
        {TABS.map((item) => (
          <button
            key={item.key}
            className={`chip ${tab === item.key ? 'chip-active' : ''}`}
            onClick={() => setTab(item.key)}
          >
            {t(item.label)}
            {counts[item.key] ? ` · ${counts[item.key]}` : ''}
          </button>
        ))}
      </div>

      {!loaded && <p className="empty">{t('admin.loading')}</p>}
      {loaded && !items.length && <p className="empty">{t('support.queue_empty')}</p>}

      <div className="admin-list">
        {items.map((ticket) => (
          <div key={ticket.id} className="admin-row">
            <button className="admin-row-main" onClick={() => openCard(ticket.id)}>
              <div className="admin-row-name">
                {ticket.subject}
                <span className="tag">{t(`support.topic.${ticket.topic}`)}</span>
              </div>
              <div className="admin-row-meta">{ticket.contact}</div>
            </button>

            {openId === ticket.id && (
              <div className="admin-card">
                {!card && <p className="empty">{t('admin.loading')}</p>}
                {card?.error && <p className="empty">{t('admin.card_error')}</p>}
                {card && !card.error && (
                  <>
                    <div className="support-thread">
                      {(card.messages || []).map((m) => (
                        <div
                          key={m.id}
                          className={`support-msg ${m.from_staff ? 'from-staff' : ''}`}
                        >
                          {m.body}
                          {m.author && <span className="support-author">{m.author}</span>}
                        </div>
                      ))}
                    </div>

                    {card.listing_id && (
                      <button
                        className="admin-listing"
                        onClick={() => navigate(`/go/${card.listing_id}`)}
                      >
                        <span>{t('support.open_listing')}</span>
                      </button>
                    )}

                    <textarea
                      className="support-body"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      placeholder={t('support.answer')}
                      rows={3}
                    />
                    <div className="admin-actions">
                      <button disabled={busy} onClick={() => answer(ticket.id)}>
                        {t('support.send')}
                      </button>
                      <button disabled={busy} onClick={() => close(ticket.id)}>
                        {t('support.close')}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
