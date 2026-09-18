import { useEffect, useState } from 'react'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { since } from '../utils/time'

// Карточка человека отдельным экраном, а не раскрывашкой в списке.
//
// Раньше подробности разворачивались прямо в строке: у продавца с
// двадцатью объявлениями и тридцатью входами строка становилась на три
// экрана, а список под ней уезжал так, что вернуться к нему было
// нельзя. Здесь то же самое, но с вкладками и своим адресом — карточку
// можно открыть ссылкой из жалобы, из тревог, из журнала.

const ROLES = ['guest', 'buyer', 'seller_private', 'seller_business', 'moderator', 'admin']
const TABS = ['listings', 'logins', 'actions']

export default function AdminUser() {
  const { t, i18n } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { user: me, loading: authLoading } = useAuth()

  const [card, setCard] = useState(null)
  const [summary, setSummary] = useState(null)
  const [listings, setListings] = useState([])
  const [logins, setLogins] = useState([])
  const [audit, setAudit] = useState([])
  const [tab, setTab] = useState('listings')
  const [busy, setBusy] = useState(false)
  const [denied, setDenied] = useState(false)
  const [blocking, setBlocking] = useState(false)
  const [reason, setReason] = useState('')

  const canEdit = me?.role === 'admin'
  const roleName = (role) => t(`admin.role_${role}`, role)

  useEffect(() => {
    if (authLoading) return
    if (!me) { navigate('/login', { replace: true }); return }
    let alive = true
    Promise.all([
      api.adminUser(id),
      api.adminUserSummary(id).catch(() => null),
      api.adminUserListings(id).catch(() => ({ items: [] })),
      api.adminUserLogins(id).catch(() => ({ items: [] })),
      api.adminAudit({ target_id: id, limit: 30 }).catch(() => ({ items: [] })),
    ]).then(([full, sum, list, log, acts]) => {
      if (!alive) return
      setCard(full); setSummary(sum)
      setListings(list.items || []); setLogins(log.items || []); setAudit(acts.items || [])
    }).catch((e) => { if (e.status === 403) setDenied(true); else setCard({ error: true }) })
    return () => { alive = false }
  }, [id, authLoading, me?.id, navigate])

  const changeRole = async (role) => {
    setBusy(true)
    try {
      await api.adminSetRole(id, role)
      setCard((c) => ({ ...c, role }))
    } catch (e) {
      alert(e.status === 400 ? t('admin.err_self') : t('admin.err_role'))
    } finally { setBusy(false) }
  }

  const block = async () => {
    if (!reason.trim()) return
    setBusy(true)
    try {
      const res = await api.adminBlock(id, reason.trim())
      setCard((c) => ({ ...c, is_blocked: true, block_reason: reason.trim() }))
      setBlocking(false); setReason('')
      if (res.hidden_listings) alert(t('admin.hidden', { count: res.hidden_listings }))
    } catch { alert(t('admin.err_block')) }
    finally { setBusy(false) }
  }

  const resetName = async () => {
    setBusy(true)
    try {
      const res = await api.adminResetName(id)
      setCard((c) => ({ ...c, display_name: res.display_name, must_rename: true }))
    } catch { alert(t('auth.err_generic')) }
    finally { setBusy(false) }
  }

  const unblock = async () => {
    setBusy(true)
    try {
      await api.adminUnblock(id)
      setCard((c) => ({ ...c, is_blocked: false, block_reason: null }))
    } catch { alert(t('admin.err_unblock')) }
    finally { setBusy(false) }
  }

  if (denied) {
    return (
      <div className="page admin-users">
        <PageHeader title={t('admin.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  if (!card) {
    return (
      <div className="page admin-users">
        <PageHeader title={t('admin.title')} />
        <p className="empty">{t('admin.loading')}</p>
      </div>
    )
  }

  const name = card.company_name || card.display_name || t('admin.no_name')

  return (
    <div className="page admin-users admin-user-page">
      <PageHeader title={name} />

      <div className="admin-user-head">
        <Avatar
          src={card.avatar_url}
          name={name}
          className={`admin-avatar big${card.role === 'seller_business' ? ' is-company' : ''}`}
        />
        <div className="admin-user-facts">
          <div className="admin-row-name">
            {name}
            {card.is_blocked && <span className="tag tag-danger">{t('admin.tag_blocked')}</span>}
            {card.must_rename && <span className="tag tag-warn">{t('admin.tag_renaming')}</span>}
            {card.document_verified && <span className="tag tag-ok">{t('admin.tag_verified')}</span>}
            <span className="tag">{roleName(card.role)}</span>
          </div>
          <div className="admin-row-meta">{card.email || '—'}</div>
          <div className="admin-row-meta">{card.phone || '—'}</div>
          <div className="admin-row-meta">
            {t('admin.registered', { when: card.created_at ? since(card.created_at, t, i18n.language) : '—' })}
            {' · '}
            {card.last_seen_at ? t('admin.seen', { when: since(card.last_seen_at, t, i18n.language) }) : t('admin.never_seen')}
          </div>
        </div>
      </div>

      <div className="admin-overview admin-user-stats">
        <div className="admin-stat"><b>{card.listings_active}</b><span>{t('admin.in_feed_label')}</span></div>
        <div className="admin-stat"><b>{card.listings}</b><span>{t('admin.all_listings')}</span></div>
        <div className="admin-stat"><b>{card.rating_count || 0}</b><span>{t('admin.reviews')}</span></div>
      </div>

      {card.block_reason && (
        <p className="admin-note">{t('admin.block_reason', { reason: card.block_reason })}</p>
      )}
      {summary?.listings_suspicious && (
        <p className="admin-note admin-note-warn">
          {t('admin.suspicious', { count: summary.listings_last_day, days: summary.account_age_days })}
        </p>
      )}
      {summary?.device_changed && (summary?.country_changed || summary?.isp_changed) && (
        <p className="admin-note admin-note-warn">
          {t('admin.suspicious_device', {
            location: summary.last_city ? `${summary.last_city}, ${summary.last_country}` : summary.last_country,
          })}
        </p>
      )}

      {canEdit && (
        <div className="admin-actions admin-user-actions">
          <select value={card.role} disabled={busy} onChange={(e) => changeRole(e.target.value)}>
            {ROLES.map((role) => <option key={role} value={role}>{roleName(role)}</option>)}
          </select>
          {card.is_blocked
            ? <button disabled={busy} onClick={unblock}>{t('admin.unblock')}</button>
            : <button className="danger" disabled={busy} onClick={() => setBlocking(true)}>{t('admin.block')}</button>}
          {/* Сбросить имя — мягче блокировки: человек ничего не нарушил,
              кроме того, что назвался рядом значков. */}
          <button disabled={busy || card.must_rename} onClick={resetName}>
            {card.must_rename ? t('admin.name_reset_done') : t('admin.reset_name')}
          </button>
        </div>
      )}

      {blocking && (
        <div className="mod-reason-box">
          <textarea
            className="mod-reason-input"
            placeholder={t('admin.block_prompt')}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            autoFocus
          />
          <div className="admin-actions">
            <button onClick={() => { setBlocking(false); setReason('') }}>{t('actions.cancel')}</button>
            <button className="danger" disabled={busy || !reason.trim()} onClick={block}>{t('admin.block')}</button>
          </div>
        </div>
      )}

      <div className="my-tabs">
        {TABS.map((k) => (
          <button key={k} className={tab === k ? 'my-tab active' : 'my-tab'} onClick={() => setTab(k)}>
            {t(`admin.tab_${k}`)}
          </button>
        ))}
      </div>

      {tab === 'listings' && (
        listings.length ? (
          <div className="admin-listings">
            {listings.map((l) => (
              <Link key={l.id} className="admin-listing" to={`/go/${l.id}`}>
                <span>{l.title || t('admin.untitled')}</span>
                <span className="admin-listing-status">{t(`admin.st_${l.status}`, l.status)}</span>
              </Link>
            ))}
          </div>
        ) : <p className="empty">{t('admin.empty')}</p>
      )}

      {tab === 'logins' && (
        logins.length ? (
          <div className="admin-logins">
            {logins.map((l) => (
              <div key={l.id} className="admin-login-row">
                <div className="admin-login-line1">
                  <span className="admin-login-when">
                    {l.created_at ? new Date(l.created_at).toLocaleString(i18n.language) : '—'}
                  </span>
                  <span className="admin-login-where">{l.city ? `${l.city}, ${l.country}` : (l.country || '—')}</span>
                </div>
                <div className="admin-login-line2">
                  <span className="admin-login-ip">{l.ip_address || '—'}</span>
                  <span className="admin-login-device">{l.device_guid ? l.device_guid.slice(0, 8) : '—'}</span>
                </div>
              </div>
            ))}
          </div>
        ) : <p className="admin-note admin-note-neutral">{t('admin.no_logins')}</p>
      )}

      {tab === 'actions' && (
        audit.length ? (
          <div className="admin-logins">
            {audit.map((a) => (
              <div key={a.id} className="admin-login-row">
                <div className="admin-login-line1">
                  <span className="admin-login-when">{t(`audit.act.${a.action}`, a.action)}</span>
                  <span className="admin-login-where">{a.actor}</span>
                </div>
                <div className="admin-login-line2">
                  <span className="admin-login-ip">
                    {a.created_at ? new Date(a.created_at).toLocaleString(i18n.language) : '—'}
                  </span>
                  {a.reason && <span className="admin-login-device">{a.reason}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : <p className="admin-note admin-note-neutral">{t('admin.no_actions')}</p>
      )}
    </div>
  )
}
