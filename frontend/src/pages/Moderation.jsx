import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { displayCity } from '../data/cities'
import PageHeader from '../components/PageHeader'
import { ModCardSkeletons } from '../components/Skeletons'
import { formatPrice } from '../utils/money'

// Переживает размонтирование страницы — заполняется при первой загрузке
// и читается при возврате назад. Модератор открывает объявление,
// смотрит его, жмёт «назад» — и до этого кэша список уже успевал
// стать пустым к моменту, когда браузер восстанавливал прокрутку
// (страница ещё не догрузилась и была короче, чем нужно), так что
// возврат неизменно бросал наверх, а не туда, где смотрели.
let cache = null

// Готовые причины отклонения — ровно то, что чаще всего приходится
// писать руками. «other» не из их числа: по нему открывается обычное
// текстовое поле, а не отправляется буквальное слово «other».
const REASON_KEYS = [
  'wrong_category', 'bad_photos', 'unclear_description',
  'duplicate', 'prohibited', 'suspicious_price',
]

export default function Moderation() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState(() => cache?.items || [])
  const [total, setTotal] = useState(() => cache?.total || 0)
  const [loaded, setLoaded] = useState(() => !!cache)
  const [reportsLoaded, setReportsLoaded] = useState(() => !!cache)
  const [busyId, setBusyId] = useState(null)
  const [denied, setDenied] = useState(false)
  const [tab, setTab] = useState('listings')
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

  const load = () => {
    api.modQueue(i18n.language)
      .then((res) => {
        const items = res.items || []
        const total = res.total || 0
        setItems(items); setTotal(total); setDenied(false)
        cache = { ...cache, items, total }
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

  useEffect(() => {
    if (!user) { setLoaded(true); return }
    // Кэш уже настоящий список с той же прокруткой, что видел
    // модератор — если он есть, доверяем ему и не спрашиваем сервер
    // заново. Иначе load() всегда запрашивает первую страницу (50
    // штук) и стирал бы то, что дозагрузили прокруткой, при каждом
    // возврате со страницы объявления.
    if (cache) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, i18n.language])

  const decide = async (id, approve, reason = null) => {
    setBusyId(id)
    try {
      if (approve) await api.modApprove(id)
      else await api.modReject(id, reason)
      setItems((prev) => {
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
    } catch { /* оставляем в очереди */ }
    finally { setBusyId(null) }
  }

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

      <div className="my-tabs">
        <button className={tab === 'listings' ? 'my-tab active' : 'my-tab'} onClick={() => setTab('listings')}>
          {t('mod.tab_listings')}
          {total > 0 && <span className="my-tab-count">{total}</span>}
        </button>
        <button className={tab === 'reports' ? 'my-tab active' : 'my-tab'} onClick={() => setTab('reports')}>
          {t('mod.tab_reports')}
          {reportsTotal > 0 && <span className="my-tab-count">{reportsTotal}</span>}
        </button>
      </div>

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
          {items.map((l) => (
            <div className="mod-card" key={l.id}>
              {/* Открывается как обычное объявление — та же страница,
                  тот же переход, что и везде на сайте, а не отдельная
                  ссылка сбоку. */}
              <Link to={l.path} className="mod-open-link">
                {l.photos?.length > 0 && (
                  <div className="mod-photos">
                    {l.photos.map((url, i) => <img key={i} src={url} alt="" loading="lazy" />)}
                  </div>
                )}

                <div className="mod-body">
                  {l.category_name && <div className="mod-category">{l.category_name}</div>}
                  <div className="mod-title">{l.title}</div>
                  <div className="mod-price">
                    {formatPrice(l.price, l.currency, i18n.language) || t('detail.no_price')}
                  </div>
                  {l.description && <p className="mod-desc">{l.description}</p>}
                  <div className="mod-meta">
                    {l.owner_name} · {displayCity(l.city, i18n.language)}
                  </div>
                </div>
              </Link>

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
