import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useFavorites } from '../context/FavoritesContext'
import { displayCity } from '../data/cities'

export default function ListingCard({ listing, large = false }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { isFavorite, toggle } = useFavorites()
  const fav = isFavorite(listing.id)

  const onFavClick = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    const res = await toggle(listing.id)
    // не представился — отправляем знакомиться, потом вернём обратно
    if (res?.needAuth) navigate(`/identify?returnTo=${encodeURIComponent(window.location.pathname)}`)
  }

  return (
    <div className={large ? 's-card l-card' : 's-card'}>
      <Link to={`/listing/${listing.id}`} className="s-photo-wrap">
        {listing.cover_photo ? (
          <img src={listing.cover_photo} alt="" />
        ) : (
          <div className="photo-placeholder" />
        )}
        {listing.is_urgent && <div className="badge-top urgent">{t('misc.urgent')}</div>}
      </Link>
      <div className="s-row">
        <Link to={`/listing/${listing.id}`} className="s-title">{listing.title}</Link>
        <button
          className={fav ? 's-fav on' : 's-fav'}
          onClick={onFavClick}
          aria-label={t('misc.in_favorites')}
        >
          <svg width={large ? 22 : 21} height={large ? 22 : 21} viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.7">
            <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
          </svg>
        </button>
      </div>
      <div className="s-price">
        {listing.price != null ? `${listing.price} ${listing.currency === 'EUR' ? '€' : listing.currency}` : t('detail.no_price')}
      </div>
      {listing.city && <div className="s-meta">{displayCity(listing.city, i18n.language)}</div>}
    </div>
  )
}
