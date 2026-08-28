import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'

// Роли показываем словами: «seller_private» в списке ничего не говорит
// тому, кто не писал этот код.
const ROLES = [
  'guest', 'buyer', 'seller_private', 'seller_business', 'moderator', 'admin',
]

const FILTERS = [
  { key: 'all', label: 'admin.all' },
  { key: 'blocked', label: 'admin.blocked' },
  { key: 'moderator', label: 'admin.moderators' },
  { key: 'seller_business', label: 'admin.companies' },
]

export default function AdminUsers() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)
  const [openId, setOpenId] = useState(null)
  const [card, setCard] = useState(null)
  const [busy, setBusy] = useState(false)
  // Причина блокировки — полем в карточке, а не window.prompt: тот
  // же паттерн, что уже чинили в модерации и на странице объявления —
  // нативный prompt на мобильном ведёт себя не как остальной интерфейс.
  const [blockingId, setBlockingId] = useState(null)
  const [blockReasonText, setBlockReasonText] = useState('')

  const canEdit = user?.role === 'admin'
  const roleName = (role) => t(`admin.role_${role}`, role)

  const load = useCallback(() => {
    const params = { limit: 50 }
    if (query.trim()) params.q = query.trim()
    if (filter === 'blocked') params.blocked = true
    else if (filter !== 'all') params.role = filter

    api.adminUsers(params)
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [query, filter])

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }
    load()
  }, [authLoading, user, load, navigate])

  // Поиск ждёт, пока человек допечатает: запрос на каждую букву грузит
  // сервер и мигает списком.
  useEffect(() => {
    const id = setTimeout(load, 350)
    return () => clearTimeout(id)
  }, [query, load])

  const openCard = async (id) => {
    if (openId === id) { setOpenId(null); setCard(null); return }
    setOpenId(id)
    setCard(null)
    try {
      const [full, summary, listings, logins] = await Promise.all([
        api.adminUser(id),
        api.adminUserSummary(id).catch(() => null),
        api.adminUserListings(id).catch(() => ({ items: [] })),
        api.adminUserLogins(id).catch(() => ({ items: [] })),
      ])
      setCard({ ...full, summary, listings: listings.items || [], logins: logins.items || [] })
    } catch { setCard({ error: true }) }
  }

  const changeRole = async (id, role) => {
    setBusy(true)
    try {
      await api.adminSetRole(id, role)
      setItems((prev) => prev.map((u) => (u.id === id ? { ...u, role } : u)))
      setCard((c) => (c && c.id === id ? { ...c, role } : c))
    } catch (e) {
      alert(e.status === 400 ? t('admin.err_self') : t('admin.err_role'))
    } finally { setBusy(false) }
  }

  const block = async (id, reason) => {
    if (!reason || !reason.trim()) return
    setBusy(true)
    try {
      const res = await api.adminBlock(id, reason.trim())
      setItems((prev) => prev.map((u) => (
        u.id === id ? { ...u, is_blocked: true, block_reason: reason.trim() } : u
      )))
      setBlockingId(null); setBlockReasonText('')
      if (res.hidden_listings) {
        alert(t('admin.hidden', { count: res.hidden_listings }))
      }
    } catch { alert(t('admin.err_block')) }
    finally { setBusy(false) }
  }

  const unblock = async (id) => {
    setBusy(true)
    try {
      await api.adminUnblock(id)
      setItems((prev) => prev.map((u) => (
        u.id === id ? { ...u, is_blocked: false, block_reason: null } : u
      )))
    } catch { alert(t('admin.err_unblock')) }
    finally { setBusy(false) }
  }

  const requestReverify = async (id) => {
    setBusy(true)
    try {
      await api.adminRequestReverify(id)
      alert(t('admin.reverify_sent'))
    } catch (e) {
      alert(e.code === 'already_pending' ? t('admin.reverify_pending') : t('admin.err_reverify'))
    } finally { setBusy(false) }
  }

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('admin.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-users">
      <PageHeader title={t('admin.title')} subtitle={loaded ? `${total}` : null} />

      <input
        className="admin-search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t('admin.search')}
      />

      <div className="admin-filters-wrap">
        <div className="admin-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`chip ${filter === f.key ? 'chip-active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {t(f.label)}
            </button>
          ))}
        </div>
      </div>

      {!loaded && <div className="admin-list"><AdminRowSkeletons count={6} /></div>}
      {loaded && !items.length && <p className="empty">{t('admin.empty')}</p>}

      <div className="admin-list">
        {items.map((u) => (
          <div key={u.id} className={`admin-row ${u.is_blocked ? 'blocked' : ''}`}>
            <button className="admin-row-main" onClick={() => openCard(u.id)}>
              <div className="admin-row-name">
                {u.display_name || t('admin.no_name')}
                {u.is_blocked && <span className="tag tag-danger">{t('admin.tag_blocked')}</span>}
                {u.role !== 'buyer' && (
                  <span className="tag">{roleName(u.role)}</span>
                )}
              </div>
              <div className="admin-row-meta">
                {u.email || u.phone || '—'}
                {' · '}
                {t('admin.listings', { count: u.listings })}
                {u.listings_active
                  ? ` (${t('admin.in_feed', { count: u.listings_active })})`
                  : ''}
              </div>
            </button>

            {openId === u.id && (
              <div className="admin-card">
                {!card && <p className="empty">{t('admin.loading')}</p>}
                {card?.error && <p className="empty">{t('admin.card_error')}</p>}
                {card && !card.error && (
                  <>
                    {card.block_reason && (
                      <p className="admin-note">
                        {t('admin.block_reason', { reason: card.block_reason })}
                      </p>
                    )}
                    {card.summary?.listings_suspicious && (
                      <p className="admin-note admin-note-warn">
                        {t('admin.suspicious', {
                          count: card.summary.listings_last_day,
                          days: card.summary.account_age_days,
                        })}
                      </p>
                    )}
                    {card.summary?.device_changed && card.summary?.country_changed && (
                      <p className="admin-note admin-note-warn">
                        {t('admin.suspicious_device', {
                          location: card.summary.last_city
                            ? `${card.summary.last_city}, ${card.summary.last_country}`
                            : card.summary.last_country,
                        })}
                      </p>
                    )}

                    <div className="admin-facts">
                      <span>
                        {t('admin.rating', {
                          value: card.rating_avg, count: card.rating_count,
                        })}
                      </span>
                      {card.company_name && (
                        <span>{t('admin.company', { name: card.company_name })}</span>
                      )}
                      {card.email_verified && <span>{t('admin.email_ok')}</span>}
                    </div>

                    {canEdit && (
                      <div className="admin-actions">
                        <select
                          value={card.role}
                          disabled={busy}
                          onChange={(e) => changeRole(u.id, e.target.value)}
                        >
                          {ROLES.map((role) => (
                            <option key={role} value={role}>{roleName(role)}</option>
                          ))}
                        </select>
                        {u.is_blocked ? (
                          <button disabled={busy} onClick={() => unblock(u.id)}>
                            {t('admin.unblock')}
                          </button>
                        ) : blockingId === u.id ? null : (
                          <button
                            className="danger"
                            disabled={busy}
                            onClick={() => { setBlockingId(u.id); setBlockReasonText('') }}
                          >
                            {t('admin.block')}
                          </button>
                        )}
                        {/* Заподозрили, что аккаунт продали или передали
                            другому — значок «Проверенный» должен
                            принадлежать конкретному человеку. */}
                        {card.document_verified && (
                          <button disabled={busy} onClick={() => requestReverify(u.id)}>
                            {t('admin.reverify')}
                          </button>
                        )}
                      </div>
                    )}

                    {blockingId === u.id && (
                      <div className="mod-reason-box">
                        <textarea
                          className="mod-reason-input"
                          placeholder={t('admin.block_prompt')}
                          value={blockReasonText}
                          onChange={(e) => setBlockReasonText(e.target.value)}
                          autoFocus
                        />
                        <div className="admin-actions">
                          <button onClick={() => { setBlockingId(null); setBlockReasonText('') }}>
                            {t('actions.cancel')}
                          </button>
                          <button
                            className="danger"
                            disabled={busy || !blockReasonText.trim()}
                            onClick={() => block(u.id, blockReasonText)}
                          >
                            {t('admin.block')}
                          </button>
                        </div>
                      </div>
                    )}

                    {!!card.listings?.length && (
                      <div className="admin-listings">
                        {card.listings.slice(0, 10).map((l) => (
                          <button
                            key={l.id}
                            className="admin-listing"
                            onClick={() => navigate(`/go/${l.id}`)}
                          >
                            <span>{l.title || t('admin.untitled')}</span>
                            <span className="admin-listing-status">{l.status}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    <div className="admin-subtitle">{t('admin.logins_title')}</div>
                    {card.logins?.length ? (
                      <div className="admin-logins">
                        {card.logins.map((l) => (
                          <div key={l.id} className="admin-login-row">
                            <div className="admin-login-line1">
                              <span className="admin-login-when">
                                {l.created_at ? new Date(l.created_at).toLocaleString(i18n.language) : '—'}
                              </span>
                              <span className="admin-login-where">
                                {l.city ? `${l.city}, ${l.country}` : (l.country || '—')}
                              </span>
                            </div>
                            <div className="admin-login-line2">
                              <span className="admin-login-ip">{l.ip_address || '—'}</span>
                              <span className="admin-login-device" title={l.device_guid || ''}>
                                {l.device_guid ? l.device_guid.slice(0, 8) : '—'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="admin-note admin-note-neutral">{t('admin.no_logins')}</p>
                    )}
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
