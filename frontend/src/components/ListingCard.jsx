import { Link } from 'react-router-dom'
import { useState } from 'react'

export default function ListingCard({ listing, large = false }) {
  const [fav, setFav] = useState(false)

  return (
    <div className={large ? 's-card l-card' : 's-card'}>
      <Link to={`/listing/${listing.id}`} className="s-photo-wrap">
        {listing.cover_photo ? (
          <img src={listing.cover_photo} alt="" />
        ) : (
          <div className="photo-placeholder" />
        )}
        {listing.is_urgent && <div className="badge-top urgent">Срочно</div>}
      </Link>
      <div className="s-row">
        <Link to={`/listing/${listing.id}`} className="s-title">{listing.title}</Link>
        <button
          className={fav ? 's-fav on' : 's-fav'}
          onClick={(e) => { e.preventDefault(); setFav(!fav) }}
          aria-label="favorite"
        >
          <svg width={large ? 18 : 17} height={large ? 18 : 17} viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.8">
            <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
          </svg>
        </button>
      </div>
      <div className="s-price">
        {listing.price != null ? `${listing.price} ${listing.currency === 'EUR' ? '€' : listing.currency}` : 'Цена не указана'}
      </div>
      {listing.city && <div className="s-meta">{listing.city}</div>}
    </div>
  )
}
