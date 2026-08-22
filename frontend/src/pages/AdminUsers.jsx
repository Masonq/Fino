import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

// Роли показываем словами: «seller_private» в списке ничего не говорит
// тому, кто не писал этот код.
const ROLE_NAMES = {
  guest: 'Гость',
  buyer: 'Покупатель',
  seller_private: 'Продавец',
  seller_business: 'Компания',
  moderator: 'Модератор',
  admin: 'Владелец',
}

const FILTERS = [
  { key: 'all', title: 'Все' },
  { key: 'blocked', title: 'Заблокированные' },
  { key: 'moderator', title: 'Модераторы' },
  { key: 'seller_business', title: 'Компании' },
]

export default function AdminUsers() {
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

  const canEdit = user?.role === 'admin'

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
      const [full, summary, listings] = await Promise.all([
        api.adminUser(id),
        api.adminUserSummary(id).catch(() => null),
        api.adminUserListings(id).catch(() => ({ items: [] })),
      ])
      setCard({ ...full, summary, listings: listings.items || [] })
    } catch { setCard({ error: true }) }
  }

  const changeRole = async (id, role) => {
    setBusy(true)
    try {
      await api.adminSetRole(id, role)
      setItems((prev) => prev.map((u) => (u.id === id ? { ...u, role } : u)))
      setCard((c) => (c && c.id === id ? { ...c, role } : c))
    } catch (e) {
      alert(e.status === 400 ? 'Себя понизить нельзя' : 'Не удалось изменить роль')
    } finally { setBusy(false) }
  }

  const block = async (id) => {
    const reason = prompt('За что блокируем? Причина будет видна в карточке.')
    if (!reason || !reason.trim()) return
    setBusy(true)
    try {
      const res = await api.adminBlock(id, reason.trim())
      setItems((prev) => prev.map((u) => (
        u.id === id ? { ...u, is_blocked: true, block_reason: reason.trim() } : u
      )))
      if (res.hidden_listings) {
        alert(`Объявлений снято с публикации: ${res.hidden_listings}`)
      }
    } catch { alert('Не удалось заблокировать') }
    finally { setBusy(false) }
  }

  const unblock = async (id) => {
    setBusy(true)
    try {
      await api.adminUnblock(id)
      setItems((prev) => prev.map((u) => (
        u.id === id ? { ...u, is_blocked: false, block_reason: null } : u
      )))
    } catch { alert('Не удалось снять блокировку') }
    finally { setBusy(false) }
  }

  if (denied) {
    return (
      <div className="page">
        <PageHeader title="Пользователи" />
        <p className="empty">Этот раздел доступен только сотрудникам.</p>
      </div>
    )
  }

  return (
    <div className="page admin-users">
      <PageHeader title="Пользователи" subtitle={loaded ? `${total}` : null} />

      <input
        className="admin-search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Имя, почта, телефон или компания"
      />

      <div className="admin-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`chip ${filter === f.key ? 'chip-active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {f.title}
          </button>
        ))}
      </div>

      {!loaded && <p className="empty">Загружаем…</p>}
      {loaded && !items.length && <p className="empty">Никого не нашлось.</p>}

      <div className="admin-list">
        {items.map((u) => (
          <div key={u.id} className={`admin-row ${u.is_blocked ? 'blocked' : ''}`}>
            <button className="admin-row-main" onClick={() => openCard(u.id)}>
              <div className="admin-row-name">
                {u.display_name || 'Без имени'}
                {u.is_blocked && <span className="tag tag-danger">заблокирован</span>}
                {u.role !== 'buyer' && (
                  <span className="tag">{ROLE_NAMES[u.role] || u.role}</span>
                )}
              </div>
              <div className="admin-row-meta">
                {u.email || u.phone || '—'} · объявлений {u.listings}
                {u.listings_active ? ` (в ленте ${u.listings_active})` : ''}
              </div>
            </button>

            {openId === u.id && (
              <div className="admin-card">
                {!card && <p className="empty">Загружаем…</p>}
                {card?.error && <p className="empty">Не удалось открыть карточку.</p>}
                {card && !card.error && (
                  <>
                    {card.block_reason && (
                      <p className="admin-note">Причина блокировки: {card.block_reason}</p>
                    )}
                    {card.summary?.suspicious && (
                      <p className="admin-note admin-note-warn">
                        За сутки {card.summary.listings_last_day} объявлений,
                        учётной записи {card.summary.account_age_days} дн. —
                        стоит посмотреть внимательнее.
                      </p>
                    )}

                    <div className="admin-facts">
                      <span>Рейтинг: {card.rating_avg} ({card.rating_count})</span>
                      {card.company_name && <span>Компания: {card.company_name}</span>}
                      {card.email_verified && <span>Почта подтверждена</span>}
                    </div>

                    {canEdit && (
                      <div className="admin-actions">
                        <select
                          value={card.role}
                          disabled={busy}
                          onChange={(e) => changeRole(u.id, e.target.value)}
                        >
                          {Object.entries(ROLE_NAMES).map(([key, title]) => (
                            <option key={key} value={key}>{title}</option>
                          ))}
                        </select>
                        {u.is_blocked ? (
                          <button disabled={busy} onClick={() => unblock(u.id)}>
                            Разблокировать
                          </button>
                        ) : (
                          <button className="danger" disabled={busy} onClick={() => block(u.id)}>
                            Заблокировать
                          </button>
                        )}
                      </div>
                    )}

                    {!!card.listings?.length && (
                      <div className="admin-listings">
                        {card.listings.slice(0, 10).map((l) => (
                          <button
                            key={l.id}
                            className="admin-listing"
                            onClick={() => navigate(`/listing/${l.id}`)}
                          >
                            <span>{l.title || 'Без названия'}</span>
                            <span className="admin-listing-status">{l.status}</span>
                          </button>
                        ))}
                      </div>
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
