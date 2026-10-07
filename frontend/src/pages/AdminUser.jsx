import SlidePill from '../components/SlidePill'
import { showIsland } from '../utils/island'
import { useEffect, useState } from 'react'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { since, intlLocale } from '../utils/time'

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
  // Удаление стирает человека совсем, поэтому два шага: первое нажатие
  // показывает, что именно пропадёт, второе — стирает.
  const [deleting, setDeleting] = useState(false)
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
  // Намеренно: зависим от идентификатора, а не от всего объекта: иначе карточка перезапрашивалась бы на каждое обновление.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, authLoading, me?.id, navigate])

  const changeRole = async (role) => {
    setBusy(true)
    try {
      await api.adminSetRole(id, role)
      setCard((c) => ({ ...c, role }))
    } catch (e) {
      showIsland({ text: e.status === 400 ? t('admin.err_self') : t('admin.err_role'), kind: 'warn' })
    } finally { setBusy(false) }
  }

  const block = async () => {
    if (!reason.trim()) return
    setBusy(true)
    try {
      const res = await api.adminBlock(id, reason.trim())
      setCard((c) => ({ ...c, is_blocked: true, block_reason: reason.trim() }))
      setBlocking(false); setReason('')
      if (res.hidden_listings) showIsland({ text: t('admin.hidden', { count: res.hidden_listings }), kind: 'ok' })
    } catch { showIsland({ text: t('admin.err_block'), kind: 'warn' }) }
    finally { setBusy(false) }
  }

  const resetName = async () => {
    setBusy(true)
    try {
      const res = await api.adminResetName(id)
      setCard((c) => ({ ...c, display_name: res.display_name, must_rename: true }))
    } catch { showIsland({ text: t('auth.err_generic'), kind: 'warn' }) }
    finally { setBusy(false) }
  }

  const removeForever = async () => {
    setBusy(true)
    try {
      await api.adminDeleteUser(id)
      navigate('/admin/users', { replace: true })
    } catch { showIsland({ text: t('admin.err_delete'), kind: 'warn' }) } finally { setBusy(false) }
  }

  const unblock = async () => {
    setBusy(true)
    try {
      await api.adminUnblock(id)
      setCard((c) => ({ ...c, is_blocked: false, block_reason: null }))
    } catch { showIsland({ text: t('admin.err_unblock'), kind: 'warn' }) }
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
        <PageHeader title={t('au.title')} />
        {/* скелет — в форме новой страницы: карточка человека, контакты, три плитки, список управления */}
        <div className="au-card" aria-hidden="true">
          <span className="sk-block" style={{ width: 84, height: 84, borderRadius: '50%' }} />
          <span className="sk-block" style={{ width: 160, height: 24, borderRadius: 8 }} />
          <span className="sk-block" style={{ width: 120, height: 22, borderRadius: 10 }} />
        </div>
        <div className="sk-block" style={{ height: 118, borderRadius: 22, marginBottom: 12 }} />
        <div className="au-stats">{[0, 1, 2].map((i) => <div key={i} className="au-stat sk-block" />)}</div>
        <div className="sk-block" style={{ height: 176, borderRadius: 22 }} />
      </div>
    )
  }

  const name = card.company_name || card.display_name || t('admin.no_name')

  return (
    <div className="page admin-users admin-user-page">
      <PageHeader title={t('au.title')} />

      {/* PLONK 2.0: карточка человека — как профиль продавца (аватар, имя, отметки), под ней — контакты строками
          с действием (написать, позвонить) и цифры цветными плитками; управление — списком настроек, а опасное
          («Заблокировать», «Удалить навсегда») — отдельной красной зоной в самом низу, подальше от случайного
          нажатия (раньше «Удалить навсегда» стояло прямо рядом с именем). */}
      <div className="au-card">
        <div className="au-ava-wrap">
          <Avatar src={card.avatar_url} name={name} className={`admin-avatar big${card.role === 'seller_business' ? ' is-company' : ''}`} />
          {card.last_seen_at && (Date.now() - new Date(card.last_seen_at).getTime()) < 5 * 60 * 1000 && <span className="au-online" title={t('au.online')} />}
        </div>
        <div className="au-name">{name}</div>
        <div className="au-badges">
          <span className="au-badge">{roleName(card.role)}</span>
          {card.document_verified && <span className="au-badge ok">✓ {t('admin.tag_verified')}</span>}
          {card.is_blocked && <span className="au-badge bad">{t('admin.tag_blocked')}</span>}
          {card.must_rename && <span className="au-badge warn">{t('admin.tag_renaming')}</span>}
        </div>
        <div className="au-when">
          {t('admin.registered', { when: card.created_at ? since(card.created_at, t, i18n.language) : '—' })}
          {' · '}
          {card.last_seen_at ? t('admin.seen', { when: since(card.last_seen_at, t, i18n.language) }) : t('admin.never_seen')}
        </div>
      </div>

      <div className="au-group">
        <div className="au-row">
          <span className="au-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="3" /><path d="m22 7-10 6L2 7" /></svg></span>
          <span className="au-row-main"><span className="au-row-label">{t('au.email')}</span><span className="au-row-value">{card.email || '—'}</span></span>
          {card.email && <a className="au-row-go" href={`mailto:${card.email}`}>{t('au.write')}</a>}
        </div>
        <div className="au-row">
          <span className="au-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" /></svg></span>
          <span className="au-row-main"><span className="au-row-label">{t('au.phone')}</span><span className="au-row-value">{card.phone || '—'}</span></span>
          {card.phone && <a className="au-row-go" href={`tel:${card.phone}`}>{t('au.call')}</a>}
        </div>
      </div>

      <div className="au-stats">
        <div className="au-stat" style={{ background: '#E2F1E6' }}><b>{card.listings_active}</b><span>{t('admin.in_feed_label')}</span></div>
        <div className="au-stat" style={{ background: '#E3ECFA' }}><b>{card.listings}</b><span>{t('admin.all_listings')}</span></div>
        <div className="au-stat" style={{ background: '#FAE5EE' }}><b>{card.rating_count || 0}</b><span>{t('admin.reviews')}</span></div>
      </div>

      {/* баланс человека: внесённые деньги и бонусы отдельно — видно, начислился ли бонус (за первое объявление, приглашение) */}
      <div className="au-balance">
        <div><span>{t('admin.balance_money')}</span><b>{Math.round(card.balance || 0).toLocaleString('ru-RU')} RSD</b></div>
        <div className="bonus"><span>{t('admin.balance_bonus')}</span><b>{Math.round(card.bonus_balance || 0).toLocaleString('ru-RU')} RSD</b></div>
      </div>

      {card.block_reason && (
        <div className="au-alert bad">{t('admin.block_reason', { reason: card.block_reason })}</div>
      )}
      {summary?.listings_suspicious && (
        <div className="au-alert warn">{t('admin.suspicious', { count: summary.listings_last_day, days: summary.account_age_days })}</div>
      )}
      {summary?.device_changed && (summary?.country_changed || summary?.isp_changed) && (
        <div className="au-alert warn">
          {t('admin.suspicious_device', { location: summary.last_city ? `${summary.last_city}, ${summary.last_country}` : summary.last_country })}
        </div>
      )}

      {canEdit && (
        <>
          <div className="au-sec">{t('au.manage')}</div>
          <div className="au-group">
            <label className="au-row">
              <span className="au-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg></span>
              <span className="au-row-main"><span className="au-row-value">{t('au.role')}</span></span>
              <select className="au-select" value={card.role} disabled={busy} onChange={(e) => changeRole(e.target.value)}>
                {ROLES.map((role) => <option key={role} value={role}>{roleName(role)}</option>)}
              </select>
            </label>
            <button type="button" className="au-row" disabled={busy} onClick={async () => {
              const res = await api.adminVerify(card.id, !card.document_verified).catch(() => null)
              if (res) setCard((c) => ({ ...c, document_verified: res.document_verified }))
            }}>
              <span className="au-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 12 2 2 4-4" /><path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" /></svg></span>
              <span className="au-row-main"><span className="au-row-value">{t('au.verified')}</span><span className="au-row-label">{t('au.verified_note')}</span></span>
              <span className={card.document_verified ? 'au-switch on' : 'au-switch'} aria-hidden="true"><i /></span>
            </button>
            <button type="button" className="au-row" disabled={busy || card.must_rename} onClick={resetName}>
              <span className="au-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" /></svg></span>
              <span className="au-row-main"><span className="au-row-value">{card.must_rename ? t('admin.name_reset_done') : t('admin.reset_name')}</span><span className="au-row-label">{t('au.reset_note')}</span></span>
              <svg className="au-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="m9 6 6 6-6 6" /></svg>
            </button>
          </div>

          <div className="au-sec danger">{t('au.danger')}</div>
          <div className="au-group danger">
            {card.is_blocked ? (
              <button type="button" className="au-row" disabled={busy} onClick={unblock}>
                <span className="au-row-main"><span className="au-row-value">{t('admin.unblock')}</span></span>
              </button>
            ) : (
              <button type="button" className="au-row bad" disabled={busy} onClick={() => setBlocking(true)}>
                <span className="au-row-main"><span className="au-row-value">{t('admin.block')}</span><span className="au-row-label">{t('au.block_note')}</span></span>
              </button>
            )}
            {card.role !== 'admin' && (
              <button type="button" className="au-row bad" disabled={busy} onClick={() => setDeleting(true)}>
                <span className="au-row-main"><span className="au-row-value">{t('admin.delete_user')}</span><span className="au-row-label">{t('au.delete_note')}</span></span>
              </button>
            )}
          </div>
        </>
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

      {deleting && (
        <div className="admin-confirm">
          <p className="admin-note">
            {t('admin.delete_warn', {
              listings: card.listings_total ?? 0,
              name: card.display_name || card.email || '—',
            })}
          </p>
          <div className="admin-actions">
            <button disabled={busy} onClick={() => setDeleting(false)}>{t('actions.cancel')}</button>
            <button className="danger" disabled={busy} onClick={removeForever}>
              {t('admin.delete_confirm')}
            </button>
          </div>
        </div>
      )}

      <div className="my-tabs">
        <div className="pill-track pill-row">
          <SlidePill />
        {TABS.map((k) => (
          <button key={k} className={tab === k ? 'my-tab active' : 'my-tab'} onClick={() => setTab(k)}>
            {t(`admin.tab_${k}`)}
          </button>
        ))}
        </div>
      </div>

      {tab === 'listings' && (
        listings.length ? (
          <div className="admin-listings">
            {listings.map((l) => (
              <Link key={l.id} className="admin-listing" to={`/go/${l.id}`}>
                <span>{l.title || t('admin.untitled')}</span>
                <span className={`admin-listing-status st-${l.status}`}>{t(`admin.st_${l.status}`, l.status)}</span>
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
                    {l.created_at ? new Date(l.created_at).toLocaleString(intlLocale(i18n.language)) : '—'}
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
                    {a.created_at ? new Date(a.created_at).toLocaleString(intlLocale(i18n.language)) : '—'}
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
