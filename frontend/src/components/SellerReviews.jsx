import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

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
  const navigate = useNavigate()
  const { user } = useAuth()

  const [data, setData] = useState(null)
  const [canWrite, setCanWrite] = useState(false)
  const [open, setOpen] = useState(false)
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    api.userReviews(sellerId).then(setData).catch(() => setData(null))
  }

  useEffect(() => {
    if (!sellerId) return
    load()
    if (user) {
      api.canReview(sellerId)
        .then((res) => setCanWrite(!!res.can))
        .catch(() => setCanWrite(false))
    } else {
      setCanWrite(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sellerId, user])

  const submit = async () => {
    setBusy(true); setError('')
    try {
      await api.createReview({
        target_id: sellerId,
        listing_id: listingId || null,
        rating,
        comment: comment.trim() || null,
      })
      setOpen(false); setComment(''); setCanWrite(false)
      load()
    } catch (e) {
      const map = {
        no_contact: t('rev.err_no_contact'),
        already_reviewed: t('rev.err_already'),
        self_review: t('rev.err_self'),
      }
      setError(map[e.code] || t('auth.err_generic'))
    } finally {
      setBusy(false)
    }
  }

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

        {user && canWrite && !open && (
          <button className="reviews-write" onClick={() => setOpen(true)}>
            {t('rev.write')}
          </button>
        )}
        {!user && (
          <button
            className="reviews-write"
            onClick={() => navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)}
          >
            {t('rev.write')}
          </button>
        )}
      </div>

      {open && (
        <div className="review-form">
          <Stars value={rating} size={26} onPick={setRating} />
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t('rev.comment_ph')}
            rows={3}
          />
          {error && <p className="auth-error">{error}</p>}
          <div className="review-form-actions">
            <button className="review-cancel" onClick={() => { setOpen(false); setError('') }}>
              {t('rev.cancel')}
            </button>
            <button className="review-send" disabled={busy} onClick={submit}>
              {busy ? '…' : t('rev.send')}
            </button>
          </div>
        </div>
      )}

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
