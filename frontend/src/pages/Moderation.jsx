import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { displayCity } from '../data/cities'

export default function Moderation() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [denied, setDenied] = useState(false)
  const [tab, setTab] = useState('listings')
  const [reports, setReports] = useState([])
  const [reportsTotal, setReportsTotal] = useState(0)

  const load = () => {
    api.modQueue(i18n.language)
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))

    api.reportsQueue()
      .then((res) => { setReports(res.items || []); setReportsTotal(res.total || 0) })
      .catch(() => {})
  }

  const resolveReport = async (id, action) => {
    setBusyId(id)
    try {
      await api.resolveReport(id, action)
      setReports((prev) => prev.filter((r) => r.id !== id))
      setReportsTotal((n) => Math.max(0, n - 1))
    } catch { /* оставляем в очереди */ }
    finally { setBusyId(null) }
  }

  useEffect(() => {
    if (!user) { setLoaded(true); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, i18n.language])

  const decide = async (id, approve) => {
    let reason = null
    if (!approve) {
      reason = window.prompt(t('mod.reason_prompt'))
      if (reason === null) return
    }
    setBusyId(id)
    try {
      if (approve) await api.modApprove(id)
      else await api.modReject(id, reason)
      setItems((prev) => prev.filter((l) => l.id !== id))
      setTotal((n) => Math.max(0, n - 1))
    } catch { /* оставляем в очереди */ }
    finally { setBusyId(null) }
  }

  if (authLoading) return <div className="fav-page"><h2>{t('mod.title')}</h2></div>

  if (!user) {
    return (
      <div className="fav-page">
        <h2>{t('mod.title')}</h2>
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
      <div className="fav-page">
        <h2>{t('mod.title')}</h2>
        <p className="empty-hint">{t('mod.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="fav-page">
      <h2>
        {t('mod.title')}
        {total > 0 && <span className="fav-count">{total}</span>}
      </h2>

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
        reports.length === 0 ? (
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
                  <div className="mod-title">{r.listing_title || '—'}</div>
                  {r.comment && <p className="mod-desc">{r.comment}</p>}
                </div>
                <div className="mod-actions">
                  <button disabled={busyId === r.id} onClick={() => resolveReport(r.id, 'dismiss')}>
                    {t('mod.dismiss')}
                  </button>
                  <button className="mod-reject" disabled={busyId === r.id} onClick={() => resolveReport(r.id, 'block_listing')}>
                    {t('mod.block_listing')}
                  </button>
                  <button className="mod-reject" disabled={busyId === r.id} onClick={() => resolveReport(r.id, 'block_user')}>
                    {t('mod.block_user')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : !loaded ? (
        <p className="empty-hint">{t('actions.loading')}</p>
      ) : items.length === 0 ? (
        <p className="empty-hint">{t('mod.empty')}</p>
      ) : (
        <div className="mod-list">
          {items.map((l) => (
            <div className="mod-card" key={l.id}>
              {l.photos?.length > 0 && (
                <div className="mod-photos">
                  {l.photos.map((url, i) => <img key={i} src={url} alt="" loading="lazy" />)}
                </div>
              )}

              <div className="mod-body">
                <div className="mod-title">{l.title}</div>
                <div className="mod-price">
                  {l.price ? `${l.price} ${l.currency === 'EUR' ? '€' : l.currency}` : t('detail.no_price')}
                </div>
                {l.description && <p className="mod-desc">{l.description}</p>}
                <div className="mod-meta">
                  {l.owner_name} · {displayCity(l.city, i18n.language)}
                </div>
              </div>

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
                  onClick={() => decide(l.id, false)}
                >
                  {t('mod.reject')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
