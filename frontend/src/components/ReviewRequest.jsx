import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

export default function ReviewRequest({ chatId, targetId, listingId, targetName, onDone }) {
  const { t } = useTranslation()

  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [hidden, setHidden] = useState(false)

  if (hidden) return null

  const send = async (value, withComment) => {
    setBusy(true)
    try {
      await api.createReview({
        target_id: targetId,
        listing_id: listingId || null,
        rating: value,
        comment: withComment?.trim() || null,
      })
      setDone(true)
      onDone?.()
    } catch { /* оставляем приглашение на месте */ }
    finally { setBusy(false) }
  }

  const dismiss = async () => {
    setHidden(true)
    api.dismissInvite(chatId).catch(() => {})
  }

  if (done) {
    return (
      <div className="review-request done">
        <div className="rr-check">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </div>
        {t('rev.thanks')}
      </div>
    )
  }

  return (
    <div className="review-request">
      <div className="rr-title">{t('rev.how_was_it', { name: targetName || '' })}</div>

      {rating === 0 ? (
        // Первый шаг — один тап. Форму показываем только тем, кто ответил.
        <div className="rr-quick">
          <button disabled={busy} onClick={() => setRating(5)}>
            <span className="rr-emoji">👍</span>
            {t('rev.good')}
          </button>
          <button disabled={busy} onClick={() => setRating(2)}>
            <span className="rr-emoji">👎</span>
            {t('rev.bad')}
          </button>
        </div>
      ) : (
        <div className="rr-detail">
          <div className="rr-stars">
            {[1, 2, 3, 4, 5].map((n) => (
              <span
                key={n}
                className={n <= rating ? 'star on' : 'star'}
                onClick={() => setRating(n)}
              >
                ★
              </span>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t('rev.comment_ph')}
            rows={2}
          />
          <button className="rr-send" disabled={busy} onClick={() => send(rating, comment)}>
            {busy ? '…' : t('rev.send')}
          </button>
        </div>
      )}

      <button className="rr-dismiss" onClick={dismiss}>{t('rev.not_now')}</button>
    </div>
  )
}
