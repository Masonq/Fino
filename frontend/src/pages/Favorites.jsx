import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import { CardSkeletons } from '../components/Skeletons'
import { useFavorites } from '../context/FavoritesContext'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

export default function Favorites() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { ids } = useFavorites()
  const { user } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const userId = user?.id

  useEffect(() => {
    if (!userId) { setLoaded(true); return }
    api.getFavorites(i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [userId, i18n.language])

  // убираем из списка то, что сняли с сердечка прямо на этом экране
  const visible = items.filter((l) => ids.has(l.id))

  if (!userId) {
    return (
      <div className="fav-page">
        <PageHeader title={t('favorites.title')} back={false} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </div>
          <p>{t('favorites.need_auth')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Ffavorites')}>
            {t('actions.continue')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page">
      <PageHeader title={t('favorites.title')} count={loaded ? visible.length : 0} back={false} />

      {!loaded ? (
        <div className="infinite-grid no-pad"><CardSkeletons count={4} /></div>
      ) : visible.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </div>
          <p>{t('favorites.empty')}</p>
          <Link className="fav-cta" to="/">{t('actions.to_listings')}</Link>
        </div>
      ) : (
        <div className="infinite-grid no-pad">
          {visible.map((l) => <ListingCard key={l.id} listing={l} />)}
        </div>
      )}
    </div>
  )
}
