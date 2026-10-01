import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PriceFlame from './Flame'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useFavorites } from '../context/FavoritesContext'
import { displayCity } from '../data/cities'
import { formatPrice } from '../utils/money'
import { cardMeta } from '../data/cardMeta'
import { relativeDate, isFresh } from '../utils/time'

export default function ListingCard({ listing, large = false, priority = false }) {
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
      <Link
        to={listing.path}
        className="s-photo-wrap"
        // Пока палец лежит на карточке, объявление уже запрашивается: к
        // моменту перехода ответ готов, и страница открывается без
        // ожидания. На мышке — при наведении, по той же причине.
        onTouchStart={() => api.prefetchListing(listing.id)}
        onMouseEnter={() => api.prefetchListing(listing.id)}
      >
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
        ) : listing.photos?.length > 1 ? (
          <CardPhotos listingId={listing.id} photos={listing.photos} priority={priority} />
        ) : listing.cover_photo ? (
          // Картинки грузятся по мере приближения к экрану, а не все
          // двадцать разом: видны шесть, остальные тянут сеть впустую и
          // задерживают те, что нужны сейчас.
          //
          // Первые четыре — исключение: они видны в тот же миг, и лень
          // для них лишняя задержка. Браузер сперва решает, нужна ли
          // картинка, и только потом просит её.
          //
          // decoding=async везде — чтобы распаковка не тормозила
          // прокрутку. Это же правило теперь на всех страницах сайта.
          <img
            src={listing.cover_photo}
            alt=""
            // Имя для переноса фотографии на страницу объявления.
            //
            // Браузер видит одно и то же имя на карточке и на странице —
            // и переносит снимок между ними, а не гасит один и не
            // показывает другой. Имя своё у каждого объявления, иначе
            // браузер не поймёт, какую именно карточку переносить.
            style={{ viewTransitionName: `photo-${listing.id}` }}
            loading={priority ? 'eager' : 'lazy'}
            fetchpriority={priority ? 'high' : 'auto'}
            decoding="async"
          />
        ) : (
          <div className="photo-placeholder" />
        )}
        {listing.is_xl && <div className="badge-top xl">{t('misc.promoted')}</div>}
        {listing.is_company && <div className="badge-top company">{t('seller.company_badge')}</div>}
        {listing.is_reserved && <div className="badge-top reserved">{t('misc.reserved')}</div>}
        {/* Свежее — заметно. Лента должна показывать, что площадка
            живая: на карточках моложе суток — метка внизу фото. Внизу,
            а не сверху: сверху стоят «Продвинуто» и сердечко. */}
        {isFresh(listing.published_at) && <div className="badge-fresh"><span className="badge-dot" aria-hidden="true" />{t('fresh.badge')}</div>}
      </Link>
      {/* Сердечко лежит на фото, а не в строке названия: там оно
          отнимало у названия целых 29 точек ширины, и «Велосипед Trek
          FX 2» переносился с одинокой «2» на второй строке. Кнопка —
          соседка ссылки на фото, а не её ребёнок: кнопка внутри ссылки
          недопустима. */}
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
        {/* Кольцо расходится один раз, когда сердечко только что нажали (тот же признак, что и «хлопок») */}
        {justFaved && fav && <span className="s-fav-burst" aria-hidden="true" />}
      </button>
      <div className="s-row">
        <Link to={listing.path} className="s-title">{listing.title}</Link>
      </div>
      {/* Цена, город и дата тоже ведут в объявление.
          Раньше нажималось только фото и заголовок: палец попадал в
          цену — и ничего не происходило. Человек не разбирается, что
          тут ссылка, а что нет, он нажимает на карточку. */}
      <div className="s-price-line">
      <Link to={listing.path} className="s-price">
        {/* «Бесплатно» и «цена не указана» — разные вещи: мимо второго
            читатель проходит, а первое как раз и ищут. */}
        {listing.is_free
          ? <span className="price-free">{t('detail.free')}</span>
          : formatPrice(listing.price, listing.currency, i18n.language)
            || <span className="price-none">{t('detail.no_price')}</span>}
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
      </Link>
      {/* Огонёк «цена заметно ниже» — сразу за ценой и одного с ней размера.
          Отдельная кнопка, а не значок внутри ссылки на объявление: по
          нажатию он объясняет, что это, а не уводит на другую страницу. */}
      {listing.price_mark && <PriceFlame listing={listing} />}
      {/* Остаток строки тоже ведёт в объявление, как и раньше вся строка. */}
      <Link to={listing.path} className="s-price-fill" aria-hidden="true" tabIndex={-1} />
      </div>
      {/* «2-комн., 45 м², 3/9 эт.» — то, что человек заполнил на форме
          публикации, иначе никуда дальше формы не попадало. */}
      {meta && <Link to={listing.path} className="s-attrs">{meta}</Link>}
      {/* Рисуем всегда, даже пустым: без города карточка была ниже соседней,
          и низ ряда получался рваным. */}
      <Link to={listing.path} className="s-meta">
        <span>{listing.city ? displayCity(listing.city, i18n.language) : ''}</span>
        {listing.published_at && <span className="s-date">{relativeDate(listing.published_at, t, i18n.language)}</span>}
      </Link>
    </div>
  )
}

/**
 * Листание фото прямо в карточке ленты: пальцем, с «защёлкиванием» на каждом снимке; внизу тонкие полоски,
 * какой из скольких. Картинки, кроме первой, браузер грузит, только когда до них долистали.
 *
 * Свайп по фото не переключает вкладку ленты: окончание касания дальше не передаётся (начало передаётся —
 * по нему карточка заранее запрашивает объявление). Нажатие по фото открывает объявление, как и раньше;
 * первый снимок носит имя для плавного переноса фото на страницу объявления.
 */
function CardPhotos({ listingId, photos, priority }) {
  const [index, setIndex] = useState(0)
  const onScroll = (e) => {
    const el = e.currentTarget
    const next = Math.round(el.scrollLeft / Math.max(1, el.clientWidth))
    if (next !== index) setIndex(next)
  }
  return (
    <>
      <div className="s-photos" onScroll={onScroll} onTouchEnd={(e) => e.stopPropagation()}>
        {photos.map((src, i) => (
          <img
            key={src}
            src={src}
            alt=""
            style={i === 0 ? { viewTransitionName: `photo-${listingId}` } : undefined}
            loading={i === 0 && priority ? 'eager' : 'lazy'}
            fetchpriority={i === 0 && priority ? 'high' : 'auto'}
            decoding="async"
            draggable="false"
          />
        ))}
      </div>
      <span className="s-photos-bars" aria-hidden="true">
        {photos.map((src, i) => <span key={src} className={i === index ? 'on' : ''} />)}
      </span>
    </>
  )
}
