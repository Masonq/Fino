import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AuditRowSkeletons } from '../components/Skeletons'

const FILTERS = [
  { key: '', label: 'audit.all' },
  { key: 'user', label: 'audit.about_people' },
  { key: 'listing', label: 'audit.about_listings' },
]

// Час и минута важнее даты: смотрят журнал обычно сразу после события.
function when(iso, locale) {
  if (!iso) return ''
  const date = new Date(iso)
  const today = new Date()
  const sameDay = date.toDateString() === today.toDateString()
  return sameDay
    ? date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleString(locale, {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
}

export default function AdminAudit() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState('')
  const [actor, setActor] = useState('')
  const [summary, setSummary] = useState(null)
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)

  const load = useCallback(() => {
    // Проверено: items.map ниже рендерится вообще без условия на
    // loaded, а loaded никогда не сбрасывался обратно в false при
    // смене filter/actor — при смене фильтра скелетон не показывался
    // вовсе, сразу оставались старые, уже неверные по фильтру строки
    // до прихода новых. Сбрасываем оба явно.
    setLoaded(false)
    setItems([])
    const params = { days: 30, limit: 100 }
    if (filter) params.action = filter
    if (actor.trim()) params.actor = actor.trim()

    api.adminAudit(params)
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [filter, actor])

  // Одна загрузка вместо двух — та же правка, что и на странице
  // «Пользователи» (там замерил: три запроса списка на один заход, и
  // скелет показывался заново после каждого). Загрузку запускали два
  // эффекта: один по готовности авторизации, второй по паузе после
  // ввода в поле «кто» — при первом открытии срабатывали оба.
  //
  // Следим за userId, а не за объектом пользователя: контекст обновляет
  // его не один раз за загрузку, и каждая новая ссылка перезапускала
  // эффект. Пауза нужна только печати — на первом заходе и при смене
  // фильтра ждать нечего.
  const userId = user?.id
  const lastActor = useRef(null)
  useEffect(() => {
    if (authLoading) return
    if (!userId) { navigate('/login', { replace: true }); return }
    const typing = lastActor.current !== null && lastActor.current !== actor
    lastActor.current = actor
    const id = setTimeout(load, typing ? 350 : 0)
    return () => clearTimeout(id)
  }, [authLoading, userId, load, navigate, actor])

  // Сводка не зависит ни от фильтров, ни от строки поиска — грузим её
  // один раз, а не вместе с каждой перезагрузкой списка.
  useEffect(() => {
    if (authLoading || !userId) return
    api.adminAuditSummary(7).then(setSummary).catch(() => {})
  }, [authLoading, userId])

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('audit.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-audit">
      <PageHeader title={t('audit.title')} subtitle={loaded ? `${total}` : null} />

      <input
        className="admin-search"
        value={actor}
        onChange={(e) => setActor(e.target.value)}
        placeholder={t('audit.who')}
      />

      <div className="admin-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key || 'all'}
            className={`chip ${filter === f.key ? 'chip-active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {t(f.label)}
          </button>
        ))}
      </div>

      {summary?.by_actor?.length > 0 && (
        <div className="stats-block">
          <div className="stats-block-title">{t('audit.week')}</div>
          <div className="stats-rows">
            {summary.by_actor.slice(0, 5).map((row) => (
              <div key={row.actor} className="stats-row">
                <span>{row.actor}</span>
                <span>{row.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loaded && <div className="audit-list"><AuditRowSkeletons count={6} /></div>}
      {loaded && !items.length && <p className="empty">{t('audit.empty')}</p>}

      <div className="audit-list">
        {items.map((row) => (
          <div key={row.id} className="audit-row">
            <div className="audit-head">
              <span className="audit-action">{t(`audit.act.${row.action}`, row.action)}</span>
              <span className="audit-time">{when(row.created_at, i18n.language)}</span>
            </div>
            <div className="audit-meta">
              {row.actor}
              {row.details?.about ? ` → ${row.details.about}` : ''}
              {row.details?.was && row.details?.became
                ? ` · ${row.details.was} → ${row.details.became}`
                : ''}
              {row.details?.hidden_listings
                ? ` · ${t('audit.hidden', { count: row.details.hidden_listings })}`
                : ''}
            </div>
            {row.reason && <div className="audit-reason">{row.reason}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
