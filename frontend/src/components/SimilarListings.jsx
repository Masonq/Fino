import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { SimilarStripSkeleton } from './Skeletons'
import { displayCity } from '../data/cities'
import { formatPrice } from '../utils/money'

export default function SimilarListings({ listingId }) {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!listingId) return
    setLoaded(false)
    api.similarListings(listingId, i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [listingId, i18n.language])

  if (loaded && items.length === 0) return null

  return (
    <div className="similar-block">
      <div className="similar-title">{t('similar.title')}</div>

      {!loaded ? (
        <SimilarStripSkeleton />
      ) : (
      <div className="similar-strip">
        {items.map((l) => (
          <Link key={l.id} to={l.path} className="similar-card">
            <div className="similar-photo">
              {l.cover_photo
                ? <img src={l.cover_photo} alt="" loading="lazy" />
                : <div className="photo-placeholder" />}
            </div>
            <div className="similar-price">
              {l.is_free
                ? t('detail.free')
                : formatPrice(l.price, l.currency, i18n.language) || t('detail.no_price')}
            </div>
            <div className="similar-name">{l.title}</div>
            {l.city && <div className="similar-city">{displayCity(l.city, i18n.language)}</div>}
          </Link>
        ))}
      </div>
      )}
    </div>
  )
}
