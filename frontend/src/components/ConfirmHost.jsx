import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'

/**
 * Шторка подтверждения (см. utils/confirm.js). Одна на всё приложение, как и остров уведомлений.
 *
 * Выезжает снизу с лёгкой пружиной, затемняет страницу, фокус сразу на главной кнопке; Escape и нажатие мимо —
 * «Отмена». Пока открыта, страница под ней не прокручивается. Для опасных действий (удалить, заблокировать) главная
 * кнопка красная. Анимации выключаются системной настройкой «уменьшить движение».
 */
export default function ConfirmHost() {
  const { t } = useTranslation()
  const [req, setReq] = useState(null)
  const [leaving, setLeaving] = useState(false)
  const okRef = useRef(null)

  useEffect(() => {
    const onAsk = (e) => { setLeaving(false); setReq(e.detail) }
    window.addEventListener('plonk:confirm', onAsk)
    window.__plonkConfirmReady = true
    return () => { window.removeEventListener('plonk:confirm', onAsk); window.__plonkConfirmReady = false }
  }, [])

  const close = useCallback((answer) => {
    if (!req) return
    req.resolve(answer)
    setLeaving(true)
    setTimeout(() => { setReq(null); setLeaving(false) }, 220)
  }, [req])

  useEffect(() => {
    if (!req) return undefined
    okRef.current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') close(false) }
    document.addEventListener('keydown', onKey)
    const before = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = before }
  }, [req, close])

  if (!req) return null
  return createPortal(
    <div className={leaving ? 'cs-root is-leaving' : 'cs-root'}>
      <div className="cs-overlay" onClick={() => close(false)} />
      <div className="cs-sheet" role="alertdialog" aria-modal="true" aria-labelledby="cs-title" aria-describedby={req.text ? 'cs-text' : undefined}>
        <span className="cs-handle" aria-hidden="true" />
        <h3 id="cs-title" className="cs-title">{req.title}</h3>
        {req.text && <p id="cs-text" className="cs-text">{req.text}</p>}
        <button ref={okRef} type="button" className={req.danger ? 'cs-btn is-danger' : 'cs-btn is-primary'} onClick={() => close(true)}>
          {req.confirm || t('confirm.yes')}
        </button>
        <button type="button" className="cs-btn is-cancel" onClick={() => close(false)}>{req.cancel || t('confirm.cancel')}</button>
      </div>
    </div>,
    document.body,
  )
}
