import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const LISTING_REASONS = [
  'fraud',
  'prohibited_item',
  'spam',
  'duplicate',
  'wrong_category',
  'other',
]

// На человека — только то, что вообще может относиться к поведению,
// а не к самому товару: «не та категория»/«дубликат» тут смысла не
// имеют.
const USER_REASONS = [
  'offensive_user',
  'fraud',
  'spam',
  'other',
]

export default function ReportButton({ listingId, ownerId, targetUserId, iconOnly = false }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  // жаловаться на себя нет смысла — ни на своё объявление, ни на свой профиль
  if (user && ((ownerId && user.id === ownerId) || (targetUserId && user.id === targetUserId))) {
    return null
  }

  const reasons = targetUserId ? USER_REASONS : LISTING_REASONS

  const submit = async () => {
    setBusy(true); setError('')
    try {
      await api.createReport({
        listing_id: listingId || null,
        target_user_id: targetUserId || null,
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
    const onClick = () => {
      if (!user) {
        navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
        return
      }
      setOpen(true)
    }
    const label = t(targetUserId ? 'report.button_user' : 'report.button')

    if (iconOnly) {
      return (
        <button className="report-icon-btn" onClick={onClick} aria-label={label} title={label}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 9v4M12 16.5v.01" strokeLinecap="round" />
            <path d="M10.3 3.9 2.7 17.5a1.8 1.8 0 0 0 1.6 2.7h15.4a1.8 1.8 0 0 0 1.6-2.7L13.7 3.9a1.8 1.8 0 0 0-3.4 0Z" />
          </svg>
        </button>
      )
    }

    return (
      <button className="report-link" onClick={onClick}>
        {label}
      </button>
    )
  }

  return (
    <div className="report-sheet">
      {done ? (
        <p className="report-done">{t('report.thanks')}</p>
      ) : (
        <>
          <div className="report-title">
            {t(targetUserId ? 'report.title_user' : 'report.title')}
          </div>

          <div className="report-reasons">
            {reasons.map((r) => (
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
