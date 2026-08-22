import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'
import { addToHistory } from '../data/history'
import { useAuth } from '../context/AuthContext'
import { useFavorites } from '../context/FavoritesContext'
import ReportButton from '../components/ReportButton'
import SimilarListings from '../components/SimilarListings'
import { formatPrice } from '../utils/money'

export default function ListingDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const [scrolled, setScrolled] = useState(false)
  const [photoIdx, setPhotoIdx] = useState(0)
  // Просмотр во весь экран: в галерее фото вписано целиком и потому мелкое,
  // а разглядеть вещь перед покупкой — половина смысла объявления.
  const [fullscreen, setFullscreen] = useState(null)

  // При открытом просмотре страница под ним не должна прокручиваться:
  // иначе закрываешь снимок и оказываешься в другом месте объявления.
  useEffect(() => {
    if (fullscreen === null) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [fullscreen])

  // запоминаем просмотр — чтобы человек мог вернуться к тому, что смотрел
  useEffect(() => {
    if (id) addToHistory(id)
  }, [id])

  // Шапка появляется, когда фото уехало вверх — как у Avito:
  // сначала кнопки полупрозрачными кружками на фото, потом панель на белом.
  useEffect(() => {
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        setScrolled(window.scrollY > 210)
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); if (raf) cancelAnimationFrame(raf) }
  }, [])
  const [searchParams] = useSearchParams()

  const [listing, setListing] = useState(null)
  const [schema, setSchema] = useState([])
  const { isFavorite, toggle } = useFavorites()
  const fav = isFavorite(id)

  const onFav = async () => {
    const res = await toggle(id)
    if (res?.needAuth) navigate(`/login?returnTo=${encodeURIComponent(`/listing/${id}`)}`)
  }
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    api.getListing(id).then(setListing).catch(() => setListing(null))
  }, [id])

  useEffect(() => {
    if (!listing?.category_slug) return
    api.getCategorySchema(listing.category_slug)
      .then((res) => setSchema(res.attribute_schema || []))
      .catch(() => setSchema([]))
  }, [listing?.category_slug])

  const startChatWith = async () => {
    if (!listing) return
    setStarting(true)
    try {
      const chat = await api.startChat(listing.id)
      navigate(`/chat/${chat.id}`)
    } catch (e) {
      alert(t('detail.own_listing'))
    } finally {
      setStarting(false)
    }
  }

  useEffect(() => {
    if (searchParams.get('identified') === '1' && listing) {
      const myId = user?.id
      if (myId) startChatWith()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing])

  if (!listing) {
    // Скелетон вместо надписи: страница объявления загружается заметно,
    // и пустой экран с текстом выглядит как ошибка.
    return (
      <div className="detail-page">
        <div className="detail-photo sk-block" />
        <div className="detail-sheet">
          <div className="sk-line" style={{ height: 26, width: '45%', marginTop: 4 }} />
          <div className="sk-line" style={{ height: 17, width: '85%', marginTop: 14 }} />
          <div className="sk-line" style={{ height: 17, width: '60%', marginTop: 8 }} />
          <div className="sk-line" style={{ height: 13, width: '35%', marginTop: 18 }} />
        </div>
      </div>
    )
  }

  const lang = i18n.language
  const translation = listing.translations[lang] || Object.values(listing.translations)[0]
  // обложка идёт первой, остальные — следом
  const photos = (() => {
    const all = listing.photos || []
    const cov = all.find((ph) => ph.is_cover)
    return cov ? [cov, ...all.filter((ph) => ph !== cov)] : all
  })()

  const attrLabel = (key) => {
    const field = schema.find((f) => f.key === key)
    if (!field) return key
    return field.label?.[lang] || field.label?.ru || key
  }
  // Резюме — не товар: человек не продаёт себя, у него нет цены и он не
  // «продавец». Отличается только подачей, поэтому отдельной категории не
  // заводим, а правим формулировки там, где они не годятся.
  const isResume = listing?.attributes?.listing_kind === 'resume'

  const attrValue = (key, value) => {
    const field = schema.find((f) => f.key === key)
    if (field?.type === 'boolean') return value ? t('common.yes') : t('common.no')
    // Зарплата без валюты — просто число: «1800» не отличить от чего угодно.
    // Разделитель тысяч ставим только деньгам: «Год» превратился бы в «2 016».
    if (field?.unit === 'currency' && value !== '' && value != null) {
      return formatPrice(value, listing.currency, lang)
    }
    if (field?.type === 'select') {
      const opt = field.options?.find((o) => o.value === value)
      return opt?.label?.[lang] || opt?.label?.ru || value
    }
    // Атрибуты, заполненные словами («Вид услуги»), переводятся вместе с
    // объявлением — берём перевод, если он есть на нужном языке.
    if (field?.translatable) {
      return listing?.attributes_i18n?.[lang]?.[key] || value
    }
    return value
  }

  const handleWriteToSeller = () => {
    const myId = user?.id
    if (myId) {
      startChatWith()
    } else {
      navigate(`/login?returnTo=${encodeURIComponent(`/listing/${id}`)}`)
    }
  }

  return (
    <div className="detail-page">
      <div className="detail-photo">
        {photos.length > 0 ? (
          <div
            className="photo-strip"
            onScroll={(e) => {
              const el = e.currentTarget
              setPhotoIdx(Math.round(el.scrollLeft / el.clientWidth))
            }}
          >
            {photos.map((ph, i) => (
              /* Снимок показываем целиком, а поля по бокам заполняем его же
                 размытой копией: обрезка по высоте съедала половину
                 вертикальных фото — а их в объявлениях большинство. */
              <div
                className="photo-slide"
                key={ph.url || i}
                onClick={() => setFullscreen(i)}
              >
                <img className="photo-blur" src={ph.url} alt="" aria-hidden="true" />
                <img className="photo-main" src={ph.url} alt="" loading={i === 0 ? 'eager' : 'lazy'} />
              </div>
            ))}
          </div>
        ) : <div className="photo-placeholder" />}
        <div className={scrolled ? 'detail-topbar shown' : 'detail-topbar'}>
          <button className="topbar-btn" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <button className={fav ? 'topbar-btn on' : 'topbar-btn'} onClick={onFav} aria-label={t('misc.in_favorites')}>
            <svg viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </button>
        </div>

        <div className="detail-nav">
          <button className="circle-btn" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
              <path d="m15 18-6-6 6-6" />
            </svg>
          </button>
          <button className={fav ? 'circle-btn on' : 'circle-btn'} onClick={onFav} aria-label={t('misc.in_favorites')}>
            <svg viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </button>
        </div>
        {photos.length > 1 && (
          <>
            <div className="photo-count">{photoIdx + 1} / {photos.length}</div>
            <div className="photo-dots">
              {photos.map((_, i) => (
                <span key={i} className={i === photoIdx ? 'on' : ''} />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="detail-sheet">
        <div className="detail-price">
          {listing.price != null
            ? formatPrice(listing.price, listing.currency, lang)
            : t(isResume ? 'detail.no_salary' : 'detail.no_price')}
        </div>
        {isResume && listing.price != null && (
          <div className="price-note">{t('detail.desired_salary')}</div>
        )}
        {listing.price_negotiable && <div className="neg-pill">{t('detail.negotiable')}</div>}

        <div className="detail-title">{translation?.title}</div>
        {/* Помечаем явно: иначе продавец с нашего сайта конкурирует с
            перепечаткой и не понимает, почему объявление ведёт себя иначе. */}
        {listing.external_source === 'telegram' && (
          <div className="from-telegram">{t('detail.from_telegram')}</div>
        )}
        {listing.city && (
          <div className="detail-loc">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" />
            </svg>
            {displayCity(listing.city, lang)}
          </div>
        )}

        <div className="badge-row">
          {listing.safe_deal_available && (
            <div className="info-badge green">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6 9 17l-5-5" /></svg>
              {t('detail.safe_deal')}
            </div>
          )}
          {listing.delivery_available && <div className="info-badge grey">{t('detail.delivery')}</div>}
        </div>

        {Object.keys(listing.attributes || {}).length > 0 && (
          <div className="attr-card">
            {Object.entries(listing.attributes).map(([key, value]) => (
              <div className="attr-row" key={key}>
                <span className="k">{attrLabel(key)}</span>
                <span className="v">{String(attrValue(key, value))}</span>
              </div>
            ))}
          </div>
        )}

        {translation?.description && (
          <div className="desc-block">
            <div className="desc-title">{t('detail.description')}</div>
            <div className="desc-text">{translation.description}</div>
            {translation.is_auto_translated && (
              <div className="translate-note">{t('detail.auto_translated')} · <span>{t('detail.show_original')}</span></div>
            )}
          </div>
        )}

        {listing.owner && (
          <Link to={`/seller/${listing.owner.id}`} className="seller-row">
            <div className="seller-avatar">{listing.owner.display_name?.[0] || '?'}</div>
            <div>
              <div className="seller-name">
                {listing.owner.display_name}
                {listing.owner.phone_verified && (
                  <div className="seal seal-sm">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><path d="M20 6 9 17l-5-5" /></svg>
                  </div>
                )}
              </div>
              <div className="seller-meta">
                {listing.owner.rating_count > 0
                  ? `${listing.owner.rating_avg?.toFixed(1)} · ${t('rev.count', { count: listing.owner.rating_count })}`
                  : t('rev.none_yet')}
              </div>
            </div>
            {/* шеврон: без него строка не читается как ведущая куда-то */}
            <svg className="seller-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </Link>
        )}

        <SimilarListings listingId={listing.id} />

        <ReportButton listingId={listing.id} ownerId={listing.owner?.id} />
      </div>

      {/* Объявление перенесено из телеграм-чата: писать и звонить через сайт
          некому — автор у нас не зарегистрирован. Вместо двух погашенных
          кнопок даём одну рабочую, иначе экран выглядит сломанным. */}
      {listing.external_source === 'telegram' && listing.external_author ? (
        <div className="sticky-cta">
          <a
            className="cta-btn primary telegram"
            href={`https://t.me/${listing.external_author}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21.9 4.3 18.8 19c-.2 1-.9 1.3-1.7.8l-4.7-3.5-2.3 2.2c-.3.3-.5.5-1 .5l.4-4.9 9-8.1c.4-.3-.1-.5-.6-.2L7 10.7 2.4 9.2c-1-.3-1-1 .2-1.5l18-6.9c.8-.3 1.5.2 1.3 1.5Z" />
            </svg>
            {t('detail.open_telegram')}
          </a>
        </div>
      ) : (
      <div className="sticky-cta">
        <button className="cta-btn icon">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
          </svg>
        </button>
        <button className="cta-btn primary" disabled={starting} onClick={handleWriteToSeller}>
          {starting ? '...' : t(isResume ? 'detail.write_person' : 'detail.write_seller')}
        </button>
      </div>
      )}

      {fullscreen !== null && (
        <div className="lightbox" onClick={() => setFullscreen(null)}>
          <button className="lightbox-close" aria-label={t('actions.close')}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
          <div
            className="lightbox-strip"
            ref={(el) => {
              // открываем сразу на том снимке, который смотрели в ленте
              if (el && el.dataset.ready !== '1') {
                el.scrollLeft = fullscreen * el.clientWidth
                el.dataset.ready = '1'
              }
            }}
            onClick={(e) => e.stopPropagation()}
            onScroll={(e) => {
              const el = e.currentTarget
              setPhotoIdx(Math.round(el.scrollLeft / el.clientWidth))
            }}
          >
            {photos.map((ph, i) => (
              <img key={ph.url || i} src={ph.url} alt="" />
            ))}
          </div>
          {photos.length > 1 && (
            <div className="lightbox-count">{photoIdx + 1} / {photos.length}</div>
          )}
        </div>
      )}
    </div>
  )
}
