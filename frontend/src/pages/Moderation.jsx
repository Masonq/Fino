import { useCallback, useEffect, useRef, useState } from 'react'
import { keepValue, readValue, useKeepPlace } from '../utils/keepPlace'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { displayCity } from '../data/cities'
import PageHeader from '../components/PageHeader'
import { ModCardSkeletons } from '../components/Skeletons'
import { formatPrice } from '../utils/money'
import { timeAgo } from '../utils/time'

// Переживает размонтирование страницы — заполняется при первой загрузке
// и читается при возврате назад. Модератор открывает объявление,
// смотрит его, жмёт «назад» — и до этого кэша список уже успевал
// стать пустым к моменту, когда браузер восстанавливал прокрутку
// (страница ещё не догрузилась и была короче, чем нужно), так что
// возврат неизменно бросал наверх, а не туда, где смотрели.
//
// Но кэш без срока жизни ушёл в другую крайность: очередь модерации
// меняется (другой модератор одобрил/отклонил, появилось новое) —
// а список после первой загрузки не обновлялся вообще никогда за всю
// сессию, сколько бы времени ни прошло между заходами. CACHE_TTL —
// компромисс: быстрый заход-выход (посмотрел объявление, сразу
// назад) видит тот же список без мигания пустым экраном, а настоящий
// возврат спустя время подтягивает свежие данные.
const CACHE_TTL = 60_000
let cache = null

// Готовые причины отклонения — ровно то, что чаще всего приходится
// писать руками. «other» не из их числа: по нему открывается обычное
// текстовое поле, а не отправляется буквальное слово «other».
const REASON_KEYS = [
  'wrong_category', 'bad_photos', 'unclear_description',
  'duplicate', 'prohibited', 'suspicious_price',
]

export default function Moderation() {
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('moderation')
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState(() => cache?.items || [])
  const [total, setTotal] = useState(() => cache?.total || 0)
  const [loaded, setLoaded] = useState(() => !!cache)
  const [reportsLoaded, setReportsLoaded] = useState(() => !!cache)
  const [busyId, setBusyId] = useState(null)
  const [denied, setDenied] = useState(false)
  const [tab, setTab] = useState(() => readValue('moderation-tab', 'listings'))
  useEffect(() => { keepValue('moderation-tab', tab) }, [tab])
  const [reports, setReports] = useState(() => cache?.reports || [])
  const [reportsTotal, setReportsTotal] = useState(() => cache?.reportsTotal || 0)
  // Причина отклонения — списком готовых вариантов, а не window.prompt:
  // нативный prompt в мобильном браузере выглядит и ведёт себя не как
  // остальной интерфейс, легко принять за то, что причины вовсе нет.
  // «Другая причина» открывает текстовое поле — на случай, когда ни
  // один из готовых вариантов не подходит.
  const [rejectingId, setRejectingId] = useState(null)
  const [customReason, setCustomReason] = useState(false)
  const [reasonText, setReasonText] = useState('')
  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef(null)
  // Последнее решение — для «Отменить» в подсказке снизу. Живёт
  // шесть секунд; палец на телефоне промахивается, и без отмены ошибка
  // стоила бы объявлению публикации или ленте — спама.
  const [undo, setUndo] = useState(null)
  const undoTimer = useRef(null)
  // Очередь растёт, пока модератор её разбирает: раз в полминуты
  // спрашиваем счётчик и, если появилось новое, показываем плашку
  // «+N новых» — а не подсовываем их в список молча, сдвигая карточки
  // под пальцем.
  const [arrived, setArrived] = useState(0)
  // Карточка «в фокусе» для горячих клавиш на клавиатуре: J/K или
  // стрелки — по очереди, A — одобрить, R — отклонить, 1–6 — причина,
  // Esc — закрыть причины. На телефоне не видна и не мешает.
  const [focus, setFocus] = useState(0)
  // Отбор нескольких разом: один продавец часто выкладывает пачкой, и
  // разбирать их по одному — десять раз прочитать то же имя.
  const [picked, setPicked] = useState(() => new Set())
  const [day, setDay] = useState(null)

  const load = () => {
    api.modQueue(i18n.language)
      .then((res) => {
        const items = res.items || []
        const total = res.total || 0
        setItems(items); setTotal(total); setDenied(false)
        cache = { ...cache, items, total, fetchedAt: Date.now() }
      })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))

    api.reportsQueue()
      .then((res) => {
        const reports = res.items || []
        const reportsTotal = res.total || 0
        setReports(reports); setReportsTotal(reportsTotal)
        cache = { ...cache, reports, reportsTotal }
      })
      .catch(() => {})
      .finally(() => setReportsLoaded(true))
  }

  // Очередь сортирована «сначала старые» — так модератор разбирает по
  // порядку. Но при бэклоге за одним запросом (лимит 50) новые
  // объявления оказывались за пределами первой страницы и не
  // показывались вовсе, пока старые не разберут. Подгружаем по
  // прокрутке — тот же приём, что и в поиске.
  const loadMore = useCallback(() => {
    if (loadingMore || items.length >= total) return
    setLoadingMore(true)
    api.modQueue(i18n.language, items.length)
      .then((res) => setItems((prev) => {
        const next = [...prev, ...(res.items || [])]
        cache = { ...cache, items: next }
        return next
      }))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [i18n.language, items.length, total, loadingMore])

  useEffect(() => {
    if (!loaded || tab !== 'listings' || items.length === 0 || items.length >= total) return
    const el = sentinelRef.current
    if (!el) return
    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '600px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [loaded, tab, items.length, total, loadMore])

  const resolveReport = async (id, action) => {
    setBusyId(id)
    try {
      await api.resolveReport(id, action)
      setReports((prev) => {
        const next = prev.filter((r) => r.id !== id)
        cache = { ...cache, reports: next }
        return next
      })
      setReportsTotal((n) => {
        const next = Math.max(0, n - 1)
        cache = { ...cache, reportsTotal: next }
        return next
      })
    } catch { /* оставляем в очереди */ }
    finally { setBusyId(null) }
  }

  // userId, а не объект: контекст обновляет пользователя не один раз за
  // загрузку, и на каждую новую ссылку очередь перезапрашивалась заново.
  const userId = user?.id
  useEffect(() => {
    if (!userId) { setLoaded(true); return }
    // Кэш уже настоящий список с той же прокруткой, что видел
    // модератор — если он есть И не устарел, доверяем ему и не
    // спрашиваем сервер заново. Иначе load() всегда запрашивает первую
    // страницу (50 штук) и стирал бы то, что дозагрузили прокруткой,
    // при каждом возврате со страницы объявления.
    if (cache && Date.now() - cache.fetchedAt < CACHE_TTL) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, i18n.language])

  const decide = async (id, approve, reason = null) => {
    setBusyId(id)
    try {
      if (approve) await api.modApprove(id)
      else await api.modReject(id, reason)
      let removed = null
      let index = 0
      setItems((prev) => {
        index = prev.findIndex((l) => l.id === id)
        removed = prev[index] || null
        const next = prev.filter((l) => l.id !== id)
        cache = { ...cache, items: next }
        return next
      })
      setTotal((n) => {
        const next = Math.max(0, n - 1)
        cache = { ...cache, total: next }
        return next
      })
      setRejectingId(null)
      setCustomReason(false)
      setReasonText('')
      setFocus((f) => Math.max(0, Math.min(f, index)))
      clearTimeout(undoTimer.current)
      setUndo({ item: removed, index, approve })
      undoTimer.current = setTimeout(() => setUndo(null), 6000)
    } catch { /* оставляем в очереди */ }
    finally { setBusyId(null) }
  }

  const undoDecision = async () => {
    if (!undo?.item) return
    clearTimeout(undoTimer.current)
    const { item, index } = undo
    setUndo(null)
    try {
      await api.modReturn(item.id)
      setItems((prev) => {
        const next = [...prev]
        next.splice(Math.min(index, next.length), 0, item)
        cache = { ...cache, items: next }
        return next
      })
      setTotal((n) => { const next = n + 1; cache = { ...cache, total: next }; return next })
    } catch { /* решение уже не отменить */ }
  }

  // Новые в очереди — плашкой, не молча.
  useEffect(() => {
    if (!userId || denied) return
    const tick = () => {
      if (document.hidden) return
      api.modCounters().then((c) => {
        const known = (cache?.total ?? total)
        if (c.moderation > known) setArrived(c.moderation - known)
      }).catch(() => {})
    }
    const timer = setInterval(tick, 30_000)
    return () => clearInterval(timer)
     
  }, [userId, denied, total])

  useEffect(() => {
    if (!userId || denied || tab !== 'listings') return
    api.modMyDay().then(setDay).catch(() => {})
  }, [userId, denied, tab, total])

  const togglePick = (id) => setPicked((prev) => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })

  const pickOwner = (ownerId) => setPicked((prev) => {
    const next = new Set(prev)
    items.filter((l) => l.owner_id === ownerId).forEach((l) => next.add(l.id))
    return next
  })

  const bulk = async (approve, reason = null) => {
    const ids = [...picked]
    if (!ids.length) return
    setBusyId('bulk')
    try {
      await api.modBulk(ids, approve, reason)
      setItems((prev) => {
        const next = prev.filter((l) => !picked.has(l.id))
        cache = { ...cache, items: next }
        return next
      })
      setTotal((n) => {
        const next = Math.max(0, n - ids.length)
        cache = { ...cache, total: next }
        return next
      })
      setPicked(new Set())
      setRejectingId(null)
    } catch { /* оставляем в очереди */ }
    finally { setBusyId(null) }
  }

  const showArrived = () => {
    setArrived(0)
    cache = null
    setLoaded(false)
    load()
    window.scrollTo({ top: 0 })
  }

  // Горячие клавиши — только с физической клавиатуры и только на
  // вкладке объявлений; в текстовом поле не перехватываем.
  useEffect(() => {
    if (tab !== 'listings') return
    const onKey = (e) => {
      const tag = (e.target?.tagName || '').toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return
      const cur = items[focus]
      const k = e.key.toLowerCase()
      if (k === 'j' || e.key === 'ArrowDown') { e.preventDefault(); setFocus((f) => Math.min(f + 1, items.length - 1)) }
      else if (k === 'k' || e.key === 'ArrowUp') { e.preventDefault(); setFocus((f) => Math.max(f - 1, 0)) }
      else if (!cur || busyId) return
      else if (k === 'a') { e.preventDefault(); decide(cur.id, true) }
      else if (k === 'r') { e.preventDefault(); setRejectingId(cur.id); setCustomReason(false); setReasonText('') }
      else if (k === 'escape') { setRejectingId(null); setCustomReason(false) }
      else if (rejectingId === cur.id && /^[1-6]$/.test(e.key)) {
        e.preventDefault()
        decide(cur.id, false, t(`mod.reasons.${REASON_KEYS[Number(e.key) - 1]}`))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, items, focus, busyId, rejectingId])

  useEffect(() => {
    const el = document.querySelector('.mod-card.focused')
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [focus])

  if (authLoading) return <div className="fav-page mod-page"><PageHeader title={t('mod.title')} /></div>

  if (!user) {
    return (
      <div className="fav-page mod-page">
        <PageHeader title={t('mod.title')} />
        <div className="fav-empty">
          <p>{t('mod.need_login')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fmoderation')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  if (denied) {
    return (
      <div className="fav-page mod-page">
        <PageHeader title={t('mod.title')} />
        <p className="empty-hint">{t('mod.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="fav-page mod-page">
      <PageHeader title={t('mod.title')} count={total} />

      {/* Вкладки той же полосой, что отборы на остальных экранах
          админки: на каждом экране одно и то же место и один и тот же
          вид — не приходится заново искать, где переключать. */}
      <div className="admin-bar">
        <div className="admin-chips">
          <button className={tab === 'listings' ? 'chip chip-active' : 'chip'} onClick={() => setTab('listings')}>
            {t('mod.tab_listings')}
            <b>{total > 0 ? total : ''}</b>
          </button>
          <button className={tab === 'reports' ? 'chip chip-active' : 'chip'} onClick={() => setTab('reports')}>
            {t('mod.tab_reports')}
            <b>{reportsTotal > 0 ? reportsTotal : ''}</b>
          </button>
        </div>
      </div>

      {tab === 'listings' && !day && (
        <div className="mod-day" aria-hidden="true" style={{ visibility: 'hidden' }}>
          <span><b>0</b> {t('mod.day_mine')}</span>
          <span><b>0</b> {t('mod.day_team')}</span>
          <span><b>0</b> {t('mod.day_oldest')}</span>
        </div>
      )}
      {tab === 'listings' && day && (
        <div className="mod-day">
          <span><b>{day.mine.approved + day.mine.rejected}</b> {t('mod.day_mine')}</span>
          <span><b>{day.team.approved + day.team.rejected}</b> {t('mod.day_team')}</span>
          {day.oldest_waiting_hours != null && (
            <span className={day.oldest_waiting_hours > 24 ? 'warn' : ''}>
              <b>{day.oldest_waiting_hours < 1 ? '<1' : Math.round(day.oldest_waiting_hours)}</b> {t('mod.day_oldest')}
            </span>
          )}
        </div>
      )}

      {tab === 'listings' && <div className="mod-keys-hint">{t('mod.keys_hint')}</div>}

      {arrived > 0 && tab === 'listings' && (
        <button className="mod-arrived" onClick={showArrived}>
          {t('mod.arrived', { count: arrived })}
        </button>
      )}

      {tab === 'reports' ? (
        !reportsLoaded ? (
          <div className="mod-list"><ModCardSkeletons count={2} /></div>
        ) : reports.length === 0 ? (
          <p className="empty-hint">{t('mod.no_reports')}</p>
        ) : (
          <div className="mod-list">
            {reports.map((r) => (
              <div className="mod-card" key={r.id}>
                <div className="mod-body">
                  <div className="report-badge">
                    {t(`report.r_${r.reason}`)}
                    {r.same_target_count > 1 && (
                      <span className="report-count">×{r.same_target_count}</span>
                    )}
                  </div>
                  <div className="mod-title">
                    {r.listing_title || (r.target_user_name
                      ? `${t('report.on_user')}: ${r.target_user_name}`
                      : '—')}
                  </div>
                  {r.comment && <p className="mod-desc">{r.comment}</p>}
                </div>
                <div className="mod-actions">
                  <button disabled={busyId === r.id} onClick={() => resolveReport(r.id, 'dismiss')}>
                    {t('mod.dismiss')}
                  </button>
                  {r.listing_id && (
                    <button className="mod-reject" disabled={busyId === r.id} onClick={() => resolveReport(r.id, 'block_listing')}>
                      {t('mod.block_listing')}
                    </button>
                  )}
                  <button className="mod-reject" disabled={busyId === r.id} onClick={() => resolveReport(r.id, 'block_user')}>
                    {t('mod.block_user')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : !loaded ? (
        <div className="mod-list"><ModCardSkeletons count={3} /></div>
      ) : items.length === 0 ? (
        <p className="empty-hint">{t('mod.empty')}</p>
      ) : (
        <div className="mod-list">
          {items.map((l, i) => (
            <div className={`mod-card${i === focus ? ' focused' : ''}${picked.has(l.id) ? ' picked' : ''}${l.photos?.length > 0 ? '' : ' no-photo'}`} key={l.id} onClick={() => setFocus(i)}>
              <button
                className={`mod-pick${picked.has(l.id) ? ' on' : ''}`}
                onClick={(e) => { e.stopPropagation(); togglePick(l.id) }}
                aria-label={t('mod.pick')}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12.5 5 5L19 7" /></svg>
              </button>
              {/* Открывается как обычное объявление — та же страница,
                  тот же переход, что и везде на сайте, а не отдельная
                  ссылка сбоку. */}
              <Link to={l.path} className="mod-open-link">
                {l.photos?.length > 0 && (
                  <div className="mod-photos">
                    {l.photos.map((url, i) => <img key={i} src={url} alt="" loading="lazy" decoding="async" />)}
                  </div>
                )}

                <div className="mod-body">
                  {l.forbidden_warning && (
                    <div className="mod-forbidden-warning">{l.forbidden_warning}</div>
                  )}
                  {l.looks_duplicate && (
                    <div className="mod-dup">{t('mod.duplicate_hint')}</div>
                  )}
                  {l.category_name && <div className="mod-category">{l.category_name}</div>}
                  <div className="mod-title">{l.title}</div>
                  <div className="mod-price">
                    {formatPrice(l.price, l.currency, i18n.language) || t('detail.no_price')}
                  </div>
                  {l.description && <p className="mod-desc">{l.description}</p>}
                  <div className="mod-meta">
                    {displayCity(l.city, i18n.language)}
                    {l.created_at && <> · {t('mod.waiting', { when: timeAgo(l.created_at, t, i18n.language) })}</>}
                  </div>
                </div>
              </Link>

              {/* Кто выложил: новичок с нулём в ленте и парой отклонённых —
                  повод присмотреться; продавец с сотней в ленте —
                  наоборот. Видно сразу, без карточки человека. */}
              <div className="mod-seller">
                <span className="mod-seller-name">
                  <span className="name-text">{l.owner_name || '—'}</span>
                  {l.owner_verified && <span className="tag tag-ok">{t('admin.tag_verified')}</span>}
                  {l.owner_days != null && l.owner_days < 3 && <span className="tag tag-new">{t('admin.tag_new')}</span>}
                </span>
                {l.owner_pending > 1 && (
                  <button
                    className="mod-seller-pick"
                    onClick={(e) => { e.stopPropagation(); pickOwner(l.owner_id) }}
                  >
                    {t('mod.pick_owner', { count: items.filter((x) => x.owner_id === l.owner_id).length })}
                  </button>
                )}
                <span className="mod-seller-facts">
                  <span>{t('mod.seller_active', { count: l.owner_active })}</span>
                  <span className={l.owner_rejected ? 'warn' : ''}>{t('mod.seller_rejected', { count: l.owner_rejected })}</span>
                  {l.owner_pending > 1 && <span>{t('mod.seller_pending', { count: l.owner_pending })}</span>}
                </span>
              </div>

              {rejectingId === l.id ? (
                <div className="mod-reason-box">
                  {!customReason ? (
                    <>
                      <div className="mod-reason-chips">
                        {REASON_KEYS.map((key) => (
                          <button
                            key={key}
                            className="mod-reason-chip"
                            disabled={busyId === l.id}
                            onClick={() => decide(l.id, false, t(`mod.reasons.${key}`))}
                          >
                            {t(`mod.reasons.${key}`)}
                          </button>
                        ))}
                        <button
                          className="mod-reason-chip"
                          onClick={() => setCustomReason(true)}
                        >
                          {t('mod.reasons.other')}
                        </button>
                      </div>
                      <div className="mod-actions">
                        <button onClick={() => { setRejectingId(null) }}>
                          {t('actions.cancel')}
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <textarea
                        className="mod-reason-input"
                        placeholder={t('mod.reason_prompt')}
                        value={reasonText}
                        onChange={(e) => setReasonText(e.target.value)}
                        autoFocus
                      />
                      <div className="mod-actions">
                        <button onClick={() => { setCustomReason(false); setReasonText('') }}>
                          {t('actions.back')}
                        </button>
                        <button
                          className="mod-reject"
                          disabled={busyId === l.id || !reasonText.trim()}
                          onClick={() => decide(l.id, false, reasonText.trim())}
                        >
                          {t('mod.reject')}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="mod-actions">
                  <button
                    className="mod-approve"
                    disabled={busyId === l.id}
                    onClick={() => decide(l.id, true)}
                  >
                    {t('mod.approve')}
                  </button>
                  <button
                    className="mod-reject"
                    disabled={busyId === l.id}
                    onClick={() => { setRejectingId(l.id); setCustomReason(false); setReasonText('') }}
                  >
                    {t('mod.reject')}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {picked.size > 0 && (
        <div className="mod-bulkbar">
          <button className="mod-bulk-clear" onClick={() => setPicked(new Set())} aria-label={t('actions.cancel')}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
          <span className="mod-bulk-count">{t('mod.picked', { count: picked.size })}</span>
          <button className="mod-bulk-reject" disabled={busyId === 'bulk'} onClick={() => bulk(false, t('mod.reasons.prohibited'))}>
            {t('mod.reject')}
          </button>
          <button className="mod-bulk-approve" disabled={busyId === 'bulk'} onClick={() => bulk(true)}>
            {t('mod.approve')}
          </button>
        </div>
      )}

      {undo && !picked.size && (
        <div className="mod-undo" role="status">
          <span>{undo.approve ? t('mod.done_approve') : t('mod.done_reject')}</span>
          <button onClick={undoDecision}>{t('mod.undo')}</button>
        </div>
      )}

      {/* Показывается только на вкладке объявлений — счётчик total
          относится к очереди на модерацию, не к жалобам */}
      {tab === 'listings' && loaded && items.length > 0 && items.length < total && (
        <div ref={sentinelRef} className="feed-sentinel">
          {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}
        </div>
      )}
    </div>
  )
}
