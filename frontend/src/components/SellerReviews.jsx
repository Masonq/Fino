import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

function Stars({ value, size = 14, onPick }) {
  return (
    <span className={onPick ? 'stars pickable' : 'stars'} style={{ fontSize: size }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={n <= value ? 'star on' : 'star'}
          onClick={onPick ? () => onPick(n) : undefined}
        >
          ★
        </span>
      ))}
    </span>
  )
}

export default function SellerReviews({ sellerId, listingId }) {
  const { t } = useTranslation()

  const [data, setData] = useState(null)

  const load = () => {
    api.userReviews(sellerId).then(setData).catch(() => setData(null))
  }

  useEffect(() => {
    if (!sellerId) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sellerId])

  if (!data) return null

  return (
    <div className="reviews-block">
      <div className="reviews-head">
        <div>
          <div className="reviews-title">{t('rev.title')}</div>
          <div className="reviews-summary">
            <Stars value={Math.round(data.rating_avg)} size={15} />
            <span className="reviews-avg">{data.rating_avg > 0 ? data.rating_avg.toFixed(1) : '—'}</span>
            <span className="reviews-count">
              {data.rating_count > 0 ? `${data.rating_count}` : t('rev.none_yet')}
            </span>
          </div>
        </div>


      </div>

      {data.items.length > 0 && (
        <div className="reviews-list">
          {data.items.map((r) => (
            <div className="review-row" key={r.id}>
              <div className="review-top">
                <span className="review-author">{r.author_name || '—'}</span>
                <Stars value={r.rating} size={12} />
              </div>
              {r.comment && <p className="review-text">{r.comment}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
