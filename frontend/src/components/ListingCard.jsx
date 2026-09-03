import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useFavorites } from '../context/FavoritesContext'
import { displayCity } from '../data/cities'
import { formatPrice } from '../utils/money'
import { cardMeta } from '../data/cardMeta'
import { relativeDate } from '../utils/time'

export default function ListingCard({ listing, large = false }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { isFavorite, toggle } = useFavorites()
  const fav = isFavorite(listing.id)
  const meta = cardMeta(listing.category_slug, listing.attributes, t)
  // XL-карточка (куплена продвижением) — крупнее соседних и занимает
  // обе колонки сетки, тот же приём, что и large, только для конкретной
  // карточки, а не для всего списка разом. Выделение цветом — можно
  // купить и вместе с XL, и отдельно само по себе.
  const cardClass = [
    's-card',
    (large || listing.is_xl) && 'l-card',
    listing.is_xl && 'xl-span',
    listing.is_highlighted && 'highlighted',
  ].filter(Boolean).join(' ')

  // Стрелка у цены — только если валюта не менялась вместе с ценой:
  // иначе «дороже/дешевле» надо сравнивать не по голым числам, а мы
  // предпочитаем промолчать, чем показать направление наугад.
  const prev = listing.previous_price
  const priceDirection =
    prev && listing.price != null && prev.currency === listing.currency
      ? listing.price < prev.price ? 'down' : listing.price > prev.price ? 'up' : null
      : null

  // Отскок — только при добавлении, не при снятии: убирать из
  // избранного тем же радостным пульсом было бы странно, это не то
  // действие, которое стоит подчёркивать анимацией.
  const [justFaved, setJustFaved] = useState(false)
  const onFavClick = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    const wasFav = fav
    const res = await toggle(listing.id)
    // не представился — отправляем знакомиться, потом вернём обратно
    if (res?.needAuth) navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
    else if (!wasFav) {
      setJustFaved(true)
      setTimeout(() => setJustFaved(false), 450)
    }
  }

  return (
    <div className={cardClass}>
      {/* Адрес приходит от приложения: он одинаков везде — в ленте,
          в боте, в письме и в карте сайта. Запасной на случай старых
          записей. */}
      <Link to={listing.path} className="s-photo-wrap">
        {listing.cover_is_video && listing.cover_video_url ? (
          <video
            className="s-cover-video"
            src={listing.cover_video_url}
            poster={listing.cover_photo || undefined}
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
          />
        ) : listing.cover_photo ? (
          // Картинка грузится, когда карточка подходит к экрану, а не все
          // двадцать разом при открытии ленты: видны шесть, остальные
          // тянут сеть впустую и задерживают те, что нужны сейчас.
          // decoding=async — чтобы распаковка картинки не тормозила
          // прокрутку.
          <img src={listing.cover_photo} alt="" loading="lazy" decoding="async" />
        ) : (
          <div className="photo-placeholder" />
        )}
        {listing.is_xl && <div className="badge-top xl">{t('misc.promoted')}</div>}
        {listing.is_company && <div className="badge-top company">{t('seller.company_badge')}</div>}
        {listing.is_reserved && <div className="badge-top reserved">{t('misc.reserved')}</div>}
      </Link>
      <div className="s-row">
        <Link to={listing.path} className="s-title">{listing.title}</Link>
        <button
          className={fav ? 's-fav on' : 's-fav'}
          onClick={onFavClick}
          aria-label={t('misc.in_favorites')}
        >
          <svg
            width={large ? 22 : 21} height={large ? 22 : 21} viewBox="0 0 24 24"
            fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.7"
            className={justFaved ? 'fav-pop' : ''}
          >
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
