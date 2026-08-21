import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'

export default function ListingDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [searchParams] = useSearchParams()

  const [listing, setListing] = useState(null)
  const [schema, setSchema] = useState([])
  const [fav, setFav] = useState(false)
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

  const startChatWith = async (buyerId) => {
    if (!listing) return
    setStarting(true)
    try {
      const chat = await api.startChat(listing.id, buyerId)
      navigate(`/chat/${chat.id}`)
    } catch (e) {
      alert(t('detail.own_listing'))
    } finally {
      setStarting(false)
    }
  }

  useEffect(() => {
    if (searchParams.get('identified') === '1' && listing) {
      const myId = localStorage.getItem('fino_user_id')
      if (myId) startChatWith(myId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing])

  if (!listing) {
    return <div className="detail-page"><p className="empty-hint">{t('detail.loading')}</p></div>
  }

  const lang = i18n.language
  const translation = listing.translations[lang] || Object.values(listing.translations)[0]
  const cover = listing.photos?.find((p) => p.is_cover) || listing.photos?.[0]

  const attrLabel = (key) => {
    const field = schema.find((f) => f.key === key)
    if (!field) return key
    return field.label?.[lang] || field.label?.ru || key
  }
  const attrValue = (key, value) => {
    const field = schema.find((f) => f.key === key)
    if (field?.type === 'boolean') return value ? t('common.yes') : t('common.no')
    if (field?.type === 'select') {
      const opt = field.options?.find((o) => o.value === value)
      return opt?.label?.[lang] || opt?.label?.ru || value
    }
    return value
  }

  const handleWriteToSeller = () => {
    const myId = localStorage.getItem('fino_user_id')
    if (myId) {
      startChatWith(myId)
    } else {
      navigate(`/identify?returnTo=${encodeURIComponent(`/listing/${id}`)}`)
    }
  }

  return (
    <div className="detail-page">
      <div className="detail-photo">
        {cover ? <img src={cover.url} alt="" /> : <div className="photo-placeholder" />}
        <div className="detail-nav">
          <button className="circle-btn" onClick={() => navigate(-1)} aria-label={t('actions.back')}>←</button>
          <button className={fav ? 'circle-btn on' : 'circle-btn'} onClick={() => setFav(!fav)} aria-label={t('misc.in_favorites')}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill={fav ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </button>
        </div>
        {listing.photos?.length > 1 && <div className="photo-count">1 / {listing.photos.length}</div>}
      </div>

      <div className="detail-sheet">
        <div className="detail-price">
          {listing.price != null ? `${listing.price} ${listing.currency === 'EUR' ? '€' : listing.currency}` : t('detail.no_price')}
        </div>
        {listing.price_negotiable && <div className="neg-pill">{t('detail.negotiable')}</div>}

        <div className="detail-title">{translation?.title}</div>
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
          <div className="seller-row">
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
              <div className="seller-meta">{listing.owner.rating_avg?.toFixed(1)} · Fino</div>
            </div>
          </div>
        )}
      </div>

      <div className="sticky-cta">
        <button className="cta-btn icon">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .3 2 .7 3a2 2 0 0 1-.4 2.1L8 10.3a16 16 0 0 0 6 6l1.5-1.4a2 2 0 0 1 2.1-.4c1 .4 2 .6 3 .7a2 2 0 0 1 1.7 2Z" />
          </svg>
        </button>
        <button className="cta-btn primary" disabled={starting} onClick={handleWriteToSeller}>
          {starting ? '...' : t('detail.write_seller')}
        </button>
      </div>
    </div>
  )
}
