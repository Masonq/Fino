import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { monthYear } from '../utils/time'

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
  const { t, i18n } = useTranslation()

  const [data, setData] = useState(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const sentinelRef = useRef(null)

  const load = () => {
    api.userReviews(sellerId, i18n.language).then(setData).catch(() => setData(null))
  }

  const loadMore = useCallback(() => {
    if (loadingMore || !data) return
    setLoadingMore(true)
    api.userReviews(sellerId, i18n.language, data.items.length)
      .then((r) => setData((prev) => ({ ...prev, items: [...prev.items, ...(r.items || [])] })))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [sellerId, i18n.language, data, loadingMore])

  // У продавца с историей отзывов могут быть сотни — показывали первые
  // двадцать, а до остальных было не добраться.
  useEffect(() => {
    if (!data || data.items.length === 0 || data.items.length >= data.total) return
    const el = sentinelRef.current
    if (!el) return
    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '400px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [data, loadMore])

  useEffect(() => {
    if (!sellerId) return
    load()
    // перезагружаем при смене языка: комментарии приходят уже переведёнными
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sellerId, i18n.language])

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
              {data.rating_count > 0 ? t('rev.count', { count: data.rating_count }) : t('rev.none_yet')}
            </span>
          </div>
        </div>
      </div>

      {/* Оценка может быть, а отзывов под ней не быть — например, все они
          без текста. Пустой блок под звёздами выглядел как сбой загрузки. */}
      {data.rating_count > 0 && data.items.length === 0 && (
        <p className="reviews-empty">{t('rev.not_shown')}</p>
      )}

      {data.items.length > 0 && (
        <div className="reviews-list">
          {data.items.map((r) => (
            <div className="review-row" key={r.id}>
              <div className="review-top">
                <span className="review-author">{r.author_name || '—'}</span>
                <Stars value={r.rating} size={12} />
                <span className="review-date">{monthYear(r.created_at, i18n.language)}</span>
              </div>
              {r.comment && <p className="review-text">{r.comment}</p>}
              {r.is_auto_translated && (
                <div className="review-translated">{t('detail.auto_translated')}</div>
              )}
            </div>
          ))}
        </div>
      )}

      <div ref={sentinelRef} className="feed-sentinel">
        {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}
      </div>
    </div>
  )
}
