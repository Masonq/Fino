import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'
import { formatPrice } from '../utils/money'

// Другие объявления этого же продавца — не путать с SimilarListings
// (те похожи по теме, но у разных продавцов). Тот же визуальный
// приём (.similar-*), что и там — не изобретаю новый стиль ради
// одного блока. На десктопе это ещё и заполняет пустое место в правой
// колонке карточки объявления (короткое описание оставляло много
// пустого белого фона под кнопками), на мобильном — то же самое
// просто ещё один блок в общей вертикальной ленте.
export default function SellerListings({ sellerId, excludeListingId }) {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (!sellerId) return
    setLoaded(false)
    api.sellerListings(sellerId, i18n.language)
      .then((res) => setItems((res.items || []).filter((l) => l.id !== excludeListingId)))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [sellerId, excludeListingId, i18n.language])

  // Без скелетона на время загрузки — тот же случай, что и у
  // SimilarListings рядом: скелетон, обещающий место под чужие
  // объявления, а продавец других не разместил — блок схлопывался бы
  // до null и утягивал бы всё, что ниже, вверх. Появляется, только
  // если объявления реально есть.
  if (!loaded || items.length === 0) return null

  return (
    <div className="similar-block seller-listings-block">
      <div className="similar-title">{t('detail.seller_other_listings')}</div>

      <div className="similar-strip">
        {items.slice(0, 6).map((l) => (
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
    </div>
  )
}
