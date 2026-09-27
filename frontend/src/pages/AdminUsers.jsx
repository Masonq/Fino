import { useCallback, useEffect, useRef, useState } from 'react'
import { keepValue, readValue, useKeepPlace } from '../utils/keepPlace'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminRowSkeletons } from '../components/Skeletons'
import { since } from '../utils/time'

// Роли показываем словами: «seller_private» в списке ничего не говорит
// тому, кто не писал этот код.
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
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('admin-users')
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [query, setQuery] = useState(() => readValue('users-query', ''))
  useEffect(() => { keepValue('users-query', query) }, [query])
  const [filter, setFilter] = useState(() => readValue('users-filter', 'all'))
  useEffect(() => { keepValue('users-filter', filter) }, [filter])
  const [sort, setSort] = useState(() => readValue('users-sort', 'new'))
  useEffect(() => { keepValue('users-sort', sort) }, [sort])
  const [overview, setOverview] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef(null)
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)
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
  // Намеренно: зависим от user?.id, а не от всего объекта: он пересобирается при каждом обновлении профиля, и запрос уходил бы снова и снова.
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

      {/* Управление одной полосой: сводка, поиск, порядок, отборы.
          Раньше это было четыре ряда подряд — плитки сводки в два
          ряда, поле поиска, ряд фишек, — и они занимали пол-экрана
          прежде, чем показывался первый человек.

          Сводка стала строкой меток: каждая цифра по-прежнему
          переключает отбор, но места занимает впятеро меньше. */}
      <div className="admin-bar">
        <div className="admin-chips admin-summary">
          {FILTERS.filter((f) => f.stat).map((f) => (
            <button
              key={f.key}
              className={`chip ${filter === f.key ? 'chip-active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {t(f.label)}
              <b>{overview
                ? (f.key === 'today' || f.key === 'week'
                  ? `+${overview[f.stat] ?? 0}`
                  : (overview[f.stat] ?? 0))
                : '—'}</b>
            </button>
          ))}
        </div>

        <div className="admin-toolbar">
          <div className="search-field admin-bar-search">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('admin.search')}
              inputMode="search"
            />
            {query && (
              <button className="search-clear" onClick={() => setQuery('')} aria-label={t('actions.clear')}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
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
      </div>

      {!loaded && <div className="admin-list"><AdminRowSkeletons count={6} /></div>}
      {loaded && !items.length && (
        <div className="admin-empty">
          <span className="admin-empty-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="4" /><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" /></svg>
          </span>
          <span className="admin-empty-title">{t('admin.empty')}</span>
          <span className="admin-empty-text">{t('admin.empty_hint')}</span>
        </div>
      )}

      <div className="admin-list">
        {items.map((u) => {
          const isNew = u.created_at && Date.now() - new Date(u.created_at + 'Z').getTime() < 86400000
          const online = u.last_seen_at && Date.now() - new Date(u.last_seen_at + 'Z').getTime() < 15 * 60000
          return (
          <div key={u.id} className={`admin-row ${u.is_blocked ? 'blocked' : ''}`}>
            <Link className="admin-row-main" to={`/admin/users/${u.id}`}>
              <span className={`admin-avatar${u.role === 'seller_business' ? ' is-company' : ''}`}>
                <Avatar src={u.avatar_url} name={initials(u)} className="admin-avatar-inner" />
                {online && <i className="admin-online" aria-hidden="true" />}
              </span>
              <span className="admin-row-text">
                <span className="admin-row-name">
                  <span className="name-text">{u.company_name || u.display_name || t('admin.no_name')}</span>
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
            </Link>
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
