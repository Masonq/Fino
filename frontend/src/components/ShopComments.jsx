import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const ago = (iso, lang) => {
  const m = Math.max(1, Math.round((Date.now() - new Date(iso).getTime()) / 60000))
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: 'auto', style: 'short' })
  if (m < 60) return rtf.format(-m, 'minute')
  if (m < 1440) return rtf.format(-Math.round(m / 60), 'hour')
  return rtf.format(-Math.round(m / 1440), 'day')
}

/**
 * Комментарии шопса — шторкой поверх видео. Номера и ссылки сервер не пропускает: вопрос о товаре —
 * кнопкой «Спросить продавца» в чат. Автор ролика удаляет любые комментарии, остальные — жалуются.
 */
export default function ShopComments({ shop, item, onClose, onCount, onAsk }) {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const input = useRef(null)

  useEffect(() => {
    api.shopComments(shop.id).then((r) => { setItems(r.items); onCount(r.total) }).catch(() => setItems([]))
  }, [shop.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const send = () => {
    if (!user?.id) { navigate(`/login?returnTo=${encodeURIComponent(`/shops?start=${shop.id}`)}`); return }
    const v = text.trim()
    if (!v) return
    setBusy(true); setErr('')
    api.shopComment(shop.id, v)
      .then((c) => { setItems((cur) => [c, ...(cur || [])]); setText(''); onCount((n) => n + 1) })
      .catch((e) => setErr(e.code === 'comment_contacts' ? t('shops.err_contacts') : e.status === 429 ? t('shops.err_often') : t('shops.err_comment')))
      .finally(() => setBusy(false))
  }
  const remove = (c) => api.shopCommentDelete(shop.id, c.id).then(() => { setItems((cur) => cur.filter((x) => x.id !== c.id)); onCount((n) => Math.max(0, n - 1)) })
  const report = (c) => api.shopCommentReport(shop.id, c.id).then(() => setItems((cur) => cur.filter((x) => x.id !== c.id)))

  // в body, а не внутри ленты: у ленты свой слой ниже меню, и поле ввода оказывалось под нижним меню
  return createPortal(
    <div className="jr-overlay sh-cm-overlay" onClick={onClose}>
      <div className="jr-sheet sh-cm" role="dialog" aria-label={t('shops.comments')} onClick={(e) => e.stopPropagation()}>
        <div className="jr-grab" />
        <div className="sh-cm-head">
          <div className="jr-title">{t('shops.comments')}</div>
          {item && item.status === 'active' && <button type="button" className="jr-btn primary sm" onClick={() => onAsk(item)}>{t('shops.ask_seller')}</button>}
        </div>
        <div className="sh-cm-list">
          {items === null ? <div className="jr-skel" /> : items.length === 0 ? <div className="jr-hint">{t('shops.no_comments')}</div> : items.map((c) => (
            <div key={c.id} className="sh-cm-row">
              <div className="jr-ava sh-cm-ava">{c.user?.avatar ? <img src={c.user.avatar} alt="" /> : (c.user?.name || '?')[0]}</div>
              <div className="sh-cm-body">
                <div className="sh-cm-who">{c.user?.name}{c.is_author && <span className="sh-cm-badge">{t('shops.author_badge')}</span>}<span className="jr-muted">{ago(c.created_at, i18n.language)}</span></div>
                <div className="sh-cm-text">{c.text}</div>
                <div className="sh-cm-acts">
                  {c.can_delete && <button type="button" onClick={() => remove(c)}>{t('shops.delete')}</button>}
                  {user?.id && c.user?.id !== user.id && <button type="button" onClick={() => report(c)}>{t('shops.report_c')}</button>}
                </div>
              </div>
            </div>
          ))}
        </div>
        {err && <div className="jr-err">{err}</div>}
        <div className="sh-cm-input">
          <input ref={input} value={text} maxLength={500} placeholder={user?.id ? t('shops.comment_ph') : t('shops.login_to')}
            onFocus={() => { if (!user?.id) navigate(`/login?returnTo=${encodeURIComponent(`/shops?start=${shop.id}`)}`) }}
            onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') send() }} />
          <button type="button" className="jr-btn primary sm" disabled={busy || !text.trim()} onClick={send}>{t('shops.send')}</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
