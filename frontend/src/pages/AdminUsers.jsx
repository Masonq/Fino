import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'
import { since } from '../utils/time'

// Роли показываем словами: «seller_private» в списке ничего не говорит
// тому, кто не писал этот код.
const ROLES = [
  'guest', 'buyer', 'seller_private', 'seller_business', 'moderator', 'admin',
]

// Срезы списка — те же, что цифры в сводке над ним: нажал на «сегодня»
// — увидел ровно тех, кого сводка посчитала.
const FILTERS = [
  { key: 'all', label: 'admin.all', stat: 'total' },
  { key: 'today', label: 'admin.f_today', stat: 'new_today', params: { since: 'today' } },
  { key: 'week', label: 'admin.f_week', stat: 'new_week', params: { since: 'week' } },
  { key: 'online', label: 'admin.f_online', stat: 'online', params: { online: true } },
  { key: 'blocked', label: 'admin.blocked', stat: 'blocked', params: { blocked: true } },
  { key: 'seller_business', label: 'admin.companies', stat: 'business', params: { role: 'seller_business' } },
  { key: 'moderator', label: 'admin.moderators', params: { role: 'moderator' } },
]

const SORTS = ['new', 'seen', 'listings']
const PAGE = 50

// Буквы для кружка вместо аватара — по имени, а без имени по почте.
const initials = (u) => {
  const src = (u.company_name || u.display_name || u.email || '').trim()
  if (!src) return '?'
  const parts = src.split(/\s+/).filter(Boolean)
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : src.slice(0, 1)).toUpperCase()
}

export default function AdminUsers() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('new')
  const [overview, setOverview] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef(null)
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
    // Та же дыра, что и в AdminAudit.jsx/AdminSupport.jsx — items.map
    // ниже рендерится без условия на loaded, а loaded не сбрасывался
    // при смене query/filter.
    setLoaded(false)
    setItems([])
    const params = { limit: PAGE, sort }
    if (query.trim()) params.q = query.trim()
    Object.assign(params, FILTERS.find((f) => f.key === filter)?.params || {})

    api.adminUsers(params)
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [query, filter, sort])

  // Сводка — отдельно от списка и реже: цифры не меняются от поиска.
  useEffect(() => {
    if (authLoading || !user) return
    const tick = () => api.adminUsersOverview().then(setOverview).catch(() => {})
    tick()
    const timer = setInterval(tick, 60_000)
    return () => clearInterval(timer)
  }, [authLoading, user?.id])

  // Подгрузка по прокрутке: людей будут тысячи, и первые пятьдесят —
  // не список, а его начало.
  const loadMore = useCallback(() => {
    if (loadingMore || !loaded || items.length >= total) return
    setLoadingMore(true)
    const params = { limit: PAGE, offset: items.length, sort }
    if (query.trim()) params.q = query.trim()
    Object.assign(params, FILTERS.find((f) => f.key === filter)?.params || {})
    api.adminUsers(params)
      .then((res) => setItems((prev) => {
        const have = new Set(prev.map((u) => u.id))
        return [...prev, ...(res.items || []).filter((u) => !have.has(u.id))]
      }))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [loadingMore, loaded, items.length, total, sort, query, filter])

  useEffect(() => {
    if (!loaded || items.length === 0 || items.length >= total) return
    const el = sentinelRef.current
    if (!el) return
    const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) loadMore() }, { rootMargin: '600px' })
    io.observe(el)
    return () => io.disconnect()
  }, [loaded, items.length, total, loadMore])

  // Загрузку запускает один эффект, а не два.
  //
  // Раньше их было именно два: один грузил список, как только
  // становилось известно, кто вошёл, второй ждал 350мс после ввода в
  // поиске — и при первом открытии страницы срабатывали оба.
  // Замерил в браузере: три запроса списка на один заход, и скелет
  // показывался заново после каждого (load сбрасывает loaded и items).
  // Со стороны это выглядит как страница, которая грузится дважды.
  //
  // Пауза нужна только печати: на первом заходе и при смене фильтра
  // ждать нечего, поэтому задержку даём, лишь когда изменилась строка
  // поиска.
  //
  // Следим за userId, а не за самим объектом: контекст обновляет его
  // не один раз за загрузку (сперва то, что знали, потом ответ
  // сервера), и каждая новая ссылка перезапускала эффект — после
  // объединения двух эффектов в один это всё ещё давало два запроса
  // вместо одного.
  const userId = user?.id
  const lastQuery = useRef(null)
  useEffect(() => {
    if (authLoading) return
    if (!userId) { navigate('/login', { replace: true }); return }
    const typing = lastQuery.current !== null && lastQuery.current !== query
    lastQuery.current = query
    const id = setTimeout(load, typing ? 350 : 0)
    return () => clearTimeout(id)
  }, [authLoading, userId, load, navigate, query])

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
      <PageHeader title={t('admin.title')} subtitle={loaded ? t('admin.found', { count: total }) : null} />

      {/* Сводка: каждая цифра — фильтр списка. */}
      <div className="admin-overview">
        {FILTERS.filter((f) => f.stat).map((f) => (
          <button
            key={f.key}
            className={`admin-stat${filter === f.key ? ' active' : ''}${f.key === 'today' ? ' accent' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            <b>{overview ? (f.key === 'today' || f.key === 'week' ? `+${overview[f.stat]}` : overview[f.stat]) : '–'}</b>
            <span>{t(f.label)}</span>
          </button>
        ))}
      </div>

      <div className="admin-toolbar">
        <div className="admin-search-wrap">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.6-3.6" /></svg>
          <input
            className="admin-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('admin.search')}
            inputMode="search"
          />
          {query && (
            <button className="admin-search-clear" onClick={() => setQuery('')} aria-label={t('actions.cancel')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
          )}
        </div>
        <label className="admin-sort">
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label={t('admin.sort')}>
            {SORTS.map((k) => <option key={k} value={k}>{t(`admin.sort_${k}`)}</option>)}
          </select>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="m6 9 6 6 6-6" /></svg>
        </label>
      </div>

      <div className="admin-filters">
        {FILTERS.filter((f) => f.key === 'all' || f.key === 'moderator' || f.key === 'blocked').map((f) => (
          <button
            key={f.key}
            className={`chip ${filter === f.key ? 'chip-active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {t(f.label)}
          </button>
        ))}
      </div>

      {!loaded && <div className="admin-list"><AdminRowSkeletons count={6} /></div>}
      {loaded && !items.length && <p className="empty">{t('admin.empty')}</p>}

      <div className="admin-list">
        {items.map((u) => {
          const isNew = u.created_at && Date.now() - new Date(u.created_at + 'Z').getTime() < 86400000
          const online = u.last_seen_at && Date.now() - new Date(u.last_seen_at + 'Z').getTime() < 15 * 60000
          return (
          <div key={u.id} className={`admin-row ${u.is_blocked ? 'blocked' : ''} ${openId === u.id ? 'open' : ''}`}>
            <button className="admin-row-main" onClick={() => openCard(u.id)}>
              <span className={`admin-avatar${u.role === 'seller_business' ? ' is-company' : ''}`}>
                {u.avatar_url ? <img src={u.avatar_url} alt="" /> : initials(u)}
                {online && <i className="admin-online" aria-hidden="true" />}
              </span>
              <span className="admin-row-text">
                <span className="admin-row-name">
                  {u.company_name || u.display_name || t('admin.no_name')}
                  {isNew && <span className="tag tag-new">{t('admin.tag_new')}</span>}
                  {u.is_blocked && <span className="tag tag-danger">{t('admin.tag_blocked')}</span>}
                  {u.document_verified && <span className="tag tag-ok">{t('admin.tag_verified')}</span>}
                  {u.role !== 'buyer' && u.role !== 'seller_private' && (
                    <span className="tag">{roleName(u.role)}</span>
                  )}
                </span>
                <span className="admin-row-meta">
                  {u.email || u.phone || '—'}
                </span>
                <span className="admin-row-meta">
                  {t('admin.registered', { when: u.created_at ? since(u.created_at, t, i18n.language) : '—' })}
                  {' · '}
                  {u.last_seen_at ? t('admin.seen', { when: since(u.last_seen_at, t, i18n.language) }) : t('admin.never_seen')}
                </span>
              </span>
              <span className={`admin-row-count${u.listings_active ? ' has' : ''}`}>
                <b>{u.listings_active || 0}</b>
                <span>{u.listings > u.listings_active ? `/ ${u.listings}` : ''}</span>
              </span>
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
                    {card.summary?.device_changed && (card.summary?.country_changed || card.summary?.isp_changed) && (
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
          )
        })}
      </div>

      {loaded && items.length > 0 && items.length < total && (
        <div ref={sentinelRef} className="feed-sentinel">
          {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}
        </div>
      )}
    </div>
  )
}
