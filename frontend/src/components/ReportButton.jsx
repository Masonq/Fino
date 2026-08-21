import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const REASONS = [
  'fraud',
  'prohibited_item',
  'spam',
  'duplicate',
  'wrong_category',
  'other',
]

export default function ReportButton({ listingId, ownerId }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  // своё объявление не показываем жалобой
  if (user && ownerId && user.id === ownerId) return null

  const submit = async () => {
    setBusy(true); setError('')
    try {
      await api.createReport({
        listing_id: listingId,
        reason,
        comment: comment.trim() || null,
      })
      setDone(true)
      setTimeout(() => { setOpen(false); setDone(false); setReason(''); setComment('') }, 1800)
    } catch (e) {
      const map = {
        already_reported: t('report.err_already'),
        too_many_reports: t('report.err_too_many'),
        self_report: t('report.err_self'),
      }
      setError(map[e.code] || t('auth.err_generic'))
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button
        className="report-link"
        onClick={() => {
          if (!user) {
            navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
            return
          }
          setOpen(true)
        }}
      >
        {t('report.button')}
      </button>
    )
  }

  return (
    <div className="report-sheet">
      {done ? (
        <p className="report-done">{t('report.thanks')}</p>
      ) : (
        <>
          <div className="report-title">{t('report.title')}</div>

          <div className="report-reasons">
            {REASONS.map((r) => (
              <button
                key={r}
                className={reason === r ? 'report-reason active' : 'report-reason'}
                onClick={() => setReason(r)}
              >
                {t(`report.r_${r}`)}
              </button>
            ))}
          </div>

          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t('report.comment_ph')}
            rows={3}
          />

          {error && <p className="auth-error">{error}</p>}

          <div className="report-actions">
            <button className="review-cancel" onClick={() => { setOpen(false); setError('') }}>
              {t('rev.cancel')}
            </button>
            <button className="report-send" disabled={busy || !reason} onClick={submit}>
              {busy ? '…' : t('report.send')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
