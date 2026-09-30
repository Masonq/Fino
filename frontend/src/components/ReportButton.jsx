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

/**
 * Кнопка «Пожаловаться» — на объявление или на пользователя.
 *
 * По умолчанию сама себе хозяйка: держит открыто/закрыто внутри себя,
 * кнопка и форма выходят одним куском там, где стоит компонент — так
 * и было изначально, годится, когда рядом с триггером есть место для
 * формы (страница объявления).
 *
 * Значок в шапке страницы продавца — исключение: живёт в узкой строке
 * заголовка вместе с «Продавец» и стрелкой назад, а разворачивающаяся
 * форма туда не влезает и не должна пытаться. Для этого — режим
 * renderMode: 'trigger' рисует только кнопку (открытие сообщает наружу
 * через onOpenChange, не хранит своё состояние), 'sheet' рисует только
 * форму, когда open истинно, управляется тем же состоянием снаружи.
 * Обе половины — один открытый диалог, просто в разных местах DOM.
 */
export default function ReportButton({
  listingId, ownerId, targetUserId, iconOnly = false,
  renderMode = 'full', open: openProp, onOpenChange,
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [openState, setOpenState] = useState(false)
  const controlled = openProp !== undefined
  const open = controlled ? openProp : openState
  const setOpen = controlled ? onOpenChange : setOpenState

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

  const onTriggerClick = () => {
    if (!user) {
      navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
      return
    }
    setOpen(true)
  }

  const trigger = () => {
    const label = t(targetUserId ? 'report.button_user' : 'report.button')
    if (iconOnly) {
      return (
        <button className="report-icon-btn" onClick={onTriggerClick} aria-label={label} title={label}>
          {/* Флажок — общепринятый знак «пожаловаться». Прежний треугольник с
              восклицательным знаком читался как «внимание, опасность» и
              пугал, а не подсказывал, что тут можно сообщить о нарушении. */}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5.5 21V4" />
            <path d="M5.5 4.5h11.2l-2.3 4.1 2.3 4.1H5.5" />
          </svg>
        </button>
      )
    }
    return (
      <button className="report-link" onClick={onTriggerClick}>
        {label}
      </button>
    )
  }

  const sheet = () => (
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

  if (renderMode === 'trigger') return trigger()
  if (renderMode === 'sheet') return open ? sheet() : null
  return open ? sheet() : trigger()
}
