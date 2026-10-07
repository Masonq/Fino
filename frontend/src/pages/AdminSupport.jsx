import SlidePill from '../components/SlidePill'
import { showIsland } from '../utils/island'
import { useCallback, useEffect, useState } from 'react'
import { keepValue, readValue, useKeepPlace } from '../utils/keepPlace'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'
import { relativeDate } from '../utils/time'

const TABS = [
  { key: 'open', label: 'support.status.open' },
  { key: 'answered', label: 'support.status.answered' },
  { key: 'closed', label: 'support.status.closed' },
]

export default function AdminSupport() {
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('admin-support')
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [tab, setTab] = useState(() => readValue('support-tab', 'open'))
  useEffect(() => { keepValue('support-tab', tab) }, [tab])
  const [items, setItems] = useState([])
  const [counts, setCounts] = useState({})
  const [openId, setOpenId] = useState(null)
  const [card, setCard] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)

  const load = useCallback(() => {
    // Та же дыра, что и в AdminAudit.jsx — items.map ниже рендерится
    // без условия на loaded, а loaded не сбрасывался при смене tab.
    setLoaded(false)
    setItems([])
    api.supportQueue({ status: tab, limit: 100 })
      .then((res) => {
        setItems(res.items || [])
        setCounts(res.counts || {})
        setDenied(false)
      })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [tab])

  // Следим за userId, а не за объектом пользователя: контекст обновляет
  // его не один раз за загрузку (сперва то, что знали, потом ответ
  // сервера), и каждая новая ссылка перезапускает эффект — список
  // грузился дважды, а скелет показывался по второму разу. Та же
  // правка, что на «Пользователях» и в «Журнале действий».
  const userId = user?.id
  useEffect(() => {
    if (authLoading) return
    if (!userId) { navigate('/login', { replace: true }); return }
    load()
  }, [authLoading, userId, load, navigate])

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
    } catch { showIsland({ text: t('support.failed'), kind: 'warn' }) }
    finally { setBusy(false) }
  }

  const close = async (id) => {
    setBusy(true)
    try {
      await api.supportClose(id)
      setOpenId(null); setCard(null)
      load()
    } catch { showIsland({ text: t('support.failed'), kind: 'warn' }) }
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

      {/* Та же полоса отборов, что в журнале и у пользователей: одна
          строка чипов, число рядом с названием, а не через точку. */}
      <div className="admin-bar">
        <div className="admin-chips">
        <div className="pill-track pill-row">
          <SlidePill />
          {TABS.map((item) => (
            <button
              key={item.key}
              className={`chip ${tab === item.key ? 'chip-active' : ''}`}
              onClick={() => setTab(item.key)}
            >
              {t(item.label)}
              <b>{counts[item.key] || ''}</b>
            </button>
          ))}
        </div>
      </div>
      </div>
      <div className="admin-list">
        {!loaded && <AdminRowSkeletons count={6} />}
        {items.map((ticket) => {
          const who = (ticket.contact || '?').replace(/^[@+]/, '')
          const isOpen = openId === ticket.id
          return (
          <div key={ticket.id} className={isOpen ? 'tk open' : 'tk'}>
            {/* обращение — карточка: кто (круг с буквой), тема, раздел и когда; нажатие раскрывает переписку */}
            <button className="tk-head" onClick={() => openCard(ticket.id)}>
              <span className="tk-ava">{who.slice(0, 1).toUpperCase()}</span>
              <span className="tk-main">
                <span className="tk-subject">{ticket.subject}</span>
                <span className="tk-meta">
                  <span className="tk-topic">{t(`support.topic.${ticket.topic}`)}</span>
                  <span className="tk-contact">{ticket.contact}</span>
                </span>
              </span>
              <span className="tk-side">
                {ticket.updated_at && <span className="tk-time">{relativeDate(ticket.updated_at, t, i18n.language)}</span>}
                <svg className="tk-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="m6 9 6 6 6-6" /></svg>
              </span>
            </button>

            {isOpen && (
              <div className="tk-body">
                {!card && <div className="tk-loading"><span className="sk-block" style={{ height: 44, width: '70%' }} /><span className="sk-block" style={{ height: 44, width: '55%', alignSelf: 'flex-end' }} /></div>}
                {card?.error && <p className="empty">{t('admin.card_error')}</p>}
                {card && !card.error && (
                  <>
                    <div className="support-thread">
                      {(card.messages || []).map((m) => (
                        <div key={m.id} className={`support-msg ${m.from_staff ? 'from-staff' : ''}`}>
                          {m.body}
                          {(m.author || m.created_at) && <span className="support-author">{m.author}{m.author && m.created_at ? ' · ' : ''}{m.created_at ? relativeDate(m.created_at, t, i18n.language) : ''}</span>}
                        </div>
                      ))}
                    </div>

                    {card.listing_id && (
                      <button className="tk-listing" onClick={() => navigate(`/go/${card.listing_id}`)}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3h7v7M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" /></svg>
                        {t('support.open_listing')}
                      </button>
                    )}

                    {/* быстрые ответы — частые фразы одним нажатием, дальше можно дописать */}
                    <div className="tk-quick">
                      {['q1', 'q2', 'q3', 'q4'].map((k) => (
                        <button key={k} type="button" onClick={() => setDraft((d) => (d ? `${d} ` : '') + t(`tk.${k}`))}>{t(`tk.${k}_short`)}</button>
                      ))}
                    </div>
                    <textarea className="support-body tk-input" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t('support.answer')} rows={3} />
                    <div className="tk-actions">
                      <button className="tk-send" disabled={busy || !draft.trim()} onClick={() => answer(ticket.id)}>{t('support.send')}</button>
                      <button className="tk-close" disabled={busy} onClick={() => close(ticket.id)}>{t('support.close')}</button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
          )
        })}
      </div>
      {loaded && !items.length && (
        <div className="admin-empty">
          <span className="admin-empty-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a8 8 0 1 1-3.3-6.5" /><path d="M8 11h8M8 15h5" /></svg>
          </span>
          <span className="admin-empty-title">{t('support.queue_empty')}</span>
          <span className="admin-empty-text">{t('support.queue_empty_hint')}</span>
        </div>
      )}
    </div>
  )
}
