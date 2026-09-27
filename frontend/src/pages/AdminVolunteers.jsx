import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'

const TABS = ['new', 'accepted', 'rejected']

export default function AdminVolunteers() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [tab, setTab] = useState('new')
  const [items, setItems] = useState([])
  const [counts, setCounts] = useState({})
  const [openId, setOpenId] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)

  const load = useCallback(() => {
    setLoaded(false); setItems([])
    api.volunteerQueue({ status: tab })
      .then((res) => { setItems(res.items || []); setCounts(res.counts || {}); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [tab])

  const userId = user?.id
  useEffect(() => {
    if (authLoading) return
    if (!userId) { navigate('/login', { replace: true }); return }
    load()
  }, [authLoading, userId, load, navigate])

  const decide = async (id, accept) => {
    setBusy(true)
    try {
      await api.volunteerDecide(id, { accept, note: note.trim() || undefined })
      setNote(''); setOpenId(null); load()
    } catch { alert(t('support.failed')) }
    finally { setBusy(false) }
  }

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('volunteer.queue')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-support">
      <PageHeader title={t('volunteer.queue')} />
      <div className="admin-bar">
        <div className="admin-chips">
          {TABS.map((key) => (
            <button key={key} className={`chip ${tab === key ? 'chip-active' : ''}`} onClick={() => setTab(key)}>
              {t(`volunteer.status.${key}`)}
              {counts[key] ? <b>{counts[key]}</b> : null}
            </button>
          ))}
        </div>
      </div>

      {!loaded && <div className="admin-list"><AdminRowSkeletons count={4} /></div>}
      {loaded && !items.length && (
        <div className="admin-empty">
          <span className="admin-empty-title">{t('volunteer.queue_empty')}</span>
        </div>
      )}
      <div className="admin-list">
        {items.map((a) => (
          <div key={a.id} className="admin-row">
            <button className="admin-row-main" onClick={() => setOpenId(openId === a.id ? null : a.id)}>
              <div className="admin-row-name">
                <span className="name-text">{a.user?.name}</span>
                <span className="tag">{t(`volunteer.role.${a.role}`)}</span>
              </div>
              <div className="admin-row-meta">
                {a.languages.map((l) => t(`volunteer.lang.${l}`)).join(', ')} · {a.hours_per_week} {t('volunteer.hours_unit')} · {new Date(a.created_at).toLocaleDateString()}
              </div>
            </button>
            {openId === a.id && (
              <div className="admin-card">
                <p className="volunteer-about">{a.about}</p>
                {a.note && <p className="volunteer-note">{a.note}</p>}
                {a.status === 'new' && (
                  <>
                    <input
                      className="field-input"
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder={t('volunteer.note_placeholder')}
                    />
                    <div className="admin-actions">
                      <button disabled={busy} onClick={() => decide(a.id, true)}>{t('volunteer.accept')}</button>
                      <button disabled={busy} onClick={() => decide(a.id, false)}>{t('volunteer.reject')}</button>
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
