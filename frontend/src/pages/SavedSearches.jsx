import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { SavedRowSkeletons } from '../components/Skeletons'
import { displayCity } from '../data/cities'

export default function SavedSearches() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const load = () => {
    if (!user) { setLoaded(true); return }
    api.savedSearches()
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }

  useEffect(load, [user])

  const openSearch = (filters) => {
    const p = new URLSearchParams()
    if (filters.q) p.set('q', filters.q)
    if (filters.category_slug) p.set('category', filters.category_slug)
    if (filters.price_min) p.set('price_min', filters.price_min)
    if (filters.price_max) p.set('price_max', filters.price_max)
    if (filters.city) p.set('city', filters.city)
    navigate(`/search?${p}`)
  }

  const describe = (f) => {
    const parts = []
    if (f.q) parts.push(`«${f.q}»`)
    if (f.price_min || f.price_max) parts.push(`${f.price_min || ''}–${f.price_max || ''} €`)
    if (f.city) parts.push(displayCity(f.city, i18n.language))
    return parts.join(' · ')
  }

  if (authLoading) return <div className="fav-page"><PageHeader title={t('saved.title')} /></div>

  if (!user) {
    return (
      <div className="fav-page">
        <PageHeader title={t('saved.title')} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
            </svg>
          </div>
          <p>{t('saved.need_login')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fsaved')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page">
      <PageHeader title={t('saved.title')} count={items.length} />

      {!loaded ? (
        <div className="saved-list"><SavedRowSkeletons count={3} /></div>
      ) : items.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
            </svg>
          </div>
          <p>{t('saved.empty')}</p>
          <button className="fav-cta" onClick={() => navigate('/search')}>
            {t('nav.home')}
          </button>
        </div>
      ) : (
        <div className="saved-list">
          {items.map((s) => (
            <div className="saved-row" key={s.id}>
              <button className="saved-main" onClick={() => openSearch(s.filters)}>
                <div className="saved-name">{s.name}</div>
                <div className="saved-desc">{describe(s.filters)}</div>
              </button>

              <div className="saved-actions">
                <label className="saved-toggle">
                  <input
                    type="checkbox"
                    checked={s.notify_enabled}
                    onChange={async (e) => {
                      const on = e.target.checked
                      setItems((prev) => prev.map((x) => x.id === s.id ? { ...x, notify_enabled: on } : x))
                      api.toggleSavedSearch(s.id, on).catch(() => load())
                    }}
                  />
                  {t('saved.notify')}
                </label>
                <button
                  className="saved-delete"
                  onClick={async () => {
                    setItems((prev) => prev.filter((x) => x.id !== s.id))
                    api.deleteSavedSearch(s.id).catch(() => load())
                  }}
                >
                  {t('my.delete')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
