import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useFavorites } from '../context/FavoritesContext'
import { displayCity } from '../data/cities'
import { formatPrice } from '../utils/money'
import { cardMeta } from '../data/cardMeta'

// «сегодня», «вчера», «3 дня назад» — как у Авито, вместо голой даты,
// которую на карточке пришлось бы читать дольше, чем она того стоит.
function relativeDate(iso, t) {
  if (!iso) return ''
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days <= 0) return t('misc.date_today')
  if (days === 1) return t('misc.date_yesterday')
  if (days < 7) return t('misc.date_days_ago', { count: days })
  return new Date(iso).toLocaleDateString()
}

export default function ListingCard({ listing, large = false }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { isFavorite, toggle } = useFavorites()
  const fav = isFavorite(listing.id)
  const meta = cardMeta(listing.category_slug, listing.attributes, t)

  // Стрелка у цены — только если валюта не менялась вместе с ценой:
  // иначе «дороже/дешевле» надо сравнивать не по голым числам, а мы
  // предпочитаем промолчать, чем показать направление наугад.
  const prev = listing.previous_price
  const priceDirection =
    prev && listing.price != null && prev.currency === listing.currency
      ? listing.price < prev.price ? 'down' : listing.price > prev.price ? 'up' : null
      : null

  const onFavClick = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    const res = await toggle(listing.id)
    // не представился — отправляем знакомиться, потом вернём обратно
    if (res?.needAuth) navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
  }

  return (
    <div className={large ? 's-card l-card' : 's-card'}>
      {/* Адрес приходит от приложения: он одинаков везде — в ленте,
          в боте, в письме и в карте сайта. Запасной на случай старых
          записей. */}
      <Link to={listing.path} className="s-photo-wrap">
        {listing.cover_photo ? (
          <img src={listing.cover_photo} alt="" />
        ) : (
          <div className="photo-placeholder" />
        )}
        {listing.is_urgent && <div className="badge-top urgent">{t('misc.urgent')}</div>}
      </Link>
      <div className="s-row">
        <Link to={listing.path} className="s-title">{listing.title}</Link>
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
        {/* «Бесплатно» и «цена не указана» — разные вещи: мимо второго
            читатель проходит, а первое как раз и ищут. */}
        {listing.is_free
          ? <span className="price-free">{t('detail.free')}</span>
          : formatPrice(listing.price, listing.currency, i18n.language) || t('detail.no_price')}
        {priceDirection && (
          <svg
            className={`s-price-arrow ${priceDirection}`}
            width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
            aria-label={t(priceDirection === 'down' ? 'misc.price_down' : 'misc.price_up')}
          >
            {priceDirection === 'down'
              ? <path d="M12 5v14M6 13l6 6 6-6" />
              : <path d="M12 19V5M6 11l6-6 6 6" />}
          </svg>
        )}
      </div>
      {/* «2-комн., 45 м², 3/9 эт.» — то, что человек заполнил на форме
          публикации, иначе никуда дальше формы не попадало. */}
      {meta && <div className="s-attrs">{meta}</div>}
      {/* Рисуем всегда, даже пустым: без города карточка была ниже соседней,
          и низ ряда получался рваным. */}
      <div className="s-meta">
        <span>{listing.city ? displayCity(listing.city, i18n.language) : ''}</span>
        {listing.published_at && <span className="s-date">{relativeDate(listing.published_at, t)}</span>}
      </div>
    </div>
  )
}
