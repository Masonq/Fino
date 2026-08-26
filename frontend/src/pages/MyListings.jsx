import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { displayCity } from '../data/cities'
import PageHeader from '../components/PageHeader'
import { formatPrice } from '../utils/money'

const TABS = [
  { key: 'active', labelKey: 'my.tab_active' },
  { key: 'pending_moderation', labelKey: 'my.tab_pending' },
  { key: 'sold', labelKey: 'my.tab_sold' },
  { key: 'archived', labelKey: 'my.tab_archived' },
]

export default function MyListings() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [counts, setCounts] = useState({})
  const [tab, setTab] = useState('active')
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState(null)

  const load = () => {
    if (!user) { setLoaded(true); return }
    api.myListings(i18n.language)
      .then((res) => { setItems(res.items || []); setCounts(res.counts || {}) })
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }

  useEffect(load, [user, i18n.language])

  const changeStatus = async (id, status) => {
    setBusyId(id)
    try {
      await api.setListingStatus(id, status)
      load()
    } catch { /* оставляем как было */ }
    finally { setBusyId(null) }
  }

  const remove = async (id) => {
    if (!window.confirm(t('my.confirm_delete'))) return
    setBusyId(id)
    try {
      await api.deleteListing(id)
      load()
    } catch { /* оставляем как было */ }
    finally { setBusyId(null) }
  }

  if (authLoading) return <div className="fav-page"><PageHeader title={t('my.title')} /></div>

  if (!user) {
    return (
      <div className="fav-page">
        <PageHeader title={t('my.title')} />
        <div className="fav-empty">
          <p>{t('my.need_login')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fmy')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  const visible = items.filter((l) => l.status === tab)

  return (
    <div className="fav-page">
      <PageHeader title={t('my.title')} />

      <div className="my-tabs">
        {TABS.map((tb) => (
          <button
            key={tb.key}
            className={tab === tb.key ? 'my-tab active' : 'my-tab'}
            onClick={() => setTab(tb.key)}
          >
            {t(tb.labelKey)}
            {counts[tb.key] > 0 && <span className="my-tab-count">{counts[tb.key]}</span>}
          </button>
        ))}
      </div>

      {!loaded ? (
        <p className="empty-hint">{t('actions.loading')}</p>
      ) : visible.length === 0 ? (
        <div className="fav-empty">
          <p>{t('my.empty')}</p>
          <Link className="fav-cta" to="/post">{t('nav.post')}</Link>
        </div>
      ) : (
        <div className="my-list">
          {visible.map((l) => (
            <div className="my-row" key={l.id}>
              <Link to={l.path} className="my-main">
                <div className="my-thumb">
                  {l.cover_photo ? <img src={l.cover_photo} alt="" /> : <div className="photo-placeholder" />}
                </div>
                <div className="my-body">
                  <div className="my-title">{l.title}</div>
                  <div className="my-price">
                    {formatPrice(l.price, l.currency, i18n.language) || t('detail.no_price')}
                  </div>
                  <div className="my-meta">
                    {displayCity(l.city, i18n.language)}
                    {l.views_count > 0 && ` · ${t('my.views')} ${l.views_count}`}
                  </div>
                </div>
              </Link>

              <div className="my-actions">
                <button disabled={busyId === l.id} onClick={() => navigate(`/edit/${l.id}`)}>
                  {t('edit.save_short')}
                </button>
                {l.status === 'active' && (
                  <>
                    <button disabled={busyId === l.id} onClick={() => changeStatus(l.id, 'sold')}>
                      {t('my.mark_sold')}
                    </button>
                    <button disabled={busyId === l.id} onClick={() => changeStatus(l.id, 'archived')}>
                      {t('my.archive')}
                    </button>
                  </>
                )}
                {(l.status === 'sold' || l.status === 'archived') && (
                  <>
                    <button disabled={busyId === l.id} onClick={() => changeStatus(l.id, 'active')}>
                      {t('my.restore')}
                    </button>
                    <button className="danger" disabled={busyId === l.id} onClick={() => remove(l.id)}>
                      {t('my.delete')}
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
