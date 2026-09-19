import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { formatPrice } from '../utils/money'

/**
 * Свои объявления внутри Telegram.
 *
 * Отдельного экрана для отклонённых нет нарочно: человек не делит свои
 * вещи на «ждущие проверки» и «отклонённые», он помнит их как «мои
 * объявления». Поэтому список один, а состояние — пометкой в строке, и
 * действие стоит рядом с той строкой, где оно нужно: проданное снять,
 * цену поправить, истекающее продлить, отклонённое исправить.
 *
 * Правка ограничена названием, описанием и ценой. Фотографии и раздел
 * здесь не трогаем: для них нужна та же форма, что при публикации, а
 * городить её второй раз — значит получить два места, где одно и то же
 * делается по-разному.
 */
const tg = () => window.Telegram?.WebApp

export default function TgMy() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  const [items, setItems] = useState(null)
  const [busy, setBusy] = useState(null)
  const [editing, setEditing] = useState(null)
  const [draft, setDraft] = useState({ title: '', description: '', price: '', free: false })
  const [error, setError] = useState('')

  // Кнопка «назад» — своя у Telegram, в его же шапке: рисовать вторую
  // внутри страницы значит показать человеку две кнопки, которые
  // делают одно и то же. На странице публикатора она не нужна —
  // оттуда выходят кнопкой «Закрыть».
  useEffect(() => {
    const back = tg()?.BackButton
    if (!back) return
    const go = () => navigate('/tg/post')
    back.onClick?.(go)
    back.show?.()
    return () => {
      back.offClick?.(go)
      back.hide?.()
    }
  }, [navigate])

  useEffect(() => {
    const app = tg()
    if (!app?.initData) { setItems([]); setError('not_in_telegram'); return }
    app.ready()
    app.expand()
    api.tgWebAppAuth(app.initData)
      .then((res) => {
        api.setToken(res.token)
        return api.tgMyListings(i18n.language)
      })
      .then((res) => setItems(res.items || []))
      .catch(() => { setItems([]); setError('auth_failed') })
  }, [i18n.language])

  const reload = () => api.tgMyListings(i18n.language)
    .then((res) => setItems(res.items || []))
    .catch(() => {})

  const act = async (id, run) => {
    setBusy(id)
    setError('')
    try {
      await run()
      await reload()
      tg()?.HapticFeedback?.notificationOccurred?.('success')
    } catch {
      setError('action_failed')
    } finally {
      setBusy(null)
    }
  }

  const startEdit = (item) => {
    setEditing(item.id)
    setDraft({
      title: item.title,
      description: item.description || '',
      price: item.price != null ? String(item.price) : '',
      free: !!item.is_free,
    })
  }

  const saveEdit = async (item) => act(item.id, async () => {
    await api.tgEditListing(item.id, {
      title: draft.title.trim(),
      description: draft.description.trim(),
      price: draft.free ? null : Number(draft.price),
      is_free: draft.free,
    })
    setEditing(null)
  })

  if (items === null) {
    return <div className="tg-page"><p className="empty-hint">{t('actions.loading')}</p></div>
  }

  return (
    <div className="tg-page">
      <div className="tg-head">
        <img className="tg-logo" src="/logo-mark.png" alt="PLONK" />
        <div className="tg-head-text">
          <div className="tg-title">{t('tg_my.title')}</div>
          <div className="tg-sub">{t('tg_my.subtitle')}</div>
        </div>
      </div>

      {error === 'not_in_telegram' ? (
        <div className="tg-empty">
          <div className="tg-empty-title">{t('tg_post.open_in_telegram_title')}</div>
          <p className="tg-empty-text">{t('tg_post.open_in_telegram')}</p>
          <a className="form-save" href="https://t.me/Baraholka_plonk_bot?start=post">
            {t('tg_post.go_to_bot')}
          </a>
          <Link className="tg-my-link" to="/my">{t('tg_post.or_on_site')}</Link>
        </div>
      ) : error && (
        <p className="auth-error">{t(`tg_my.err_${error}`, t('errors.generic'))}</p>
      )}

      {items.length === 0 ? (
        <div className="tg-empty">
          <div className="tg-empty-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
                 strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="16" rx="3" />
              <path d="M8 10h8M8 14h5" />
            </svg>
          </div>
          <div className="tg-empty-title">{t('tg_my.empty')}</div>
          <p className="tg-empty-text">{t('tg_my.empty_hint')}</p>
          <Link className="form-save" to="/tg/post">{t('tg_my.post_first')}</Link>
        </div>
      ) : (
        <div className="tg-my-list">
          {items.map((item) => (
            <div className="tg-my-card" key={item.id}>
              <div className="tg-my-row">
                <div className="tg-my-photo">
                  {item.photo
                    ? <img src={item.photo} alt="" />
                    : <div className="photo-placeholder" />}
                </div>
                <div className="tg-my-text">
                  <div className="tg-my-title">{item.title}</div>
                  <div className="tg-my-price">
                    {item.is_free
                      ? t('detail.free')
                      : formatPrice(item.price, 'RSD', i18n.language) || '—'}
                  </div>
                  <div className={`tg-my-state ${item.status}`}>
                    {t(`tg_my.state_${item.status}`)}
                    {item.status === 'active' && item.days_left != null && item.days_left <= 7
                      && ` · ${t('tg_my.days_left', { count: item.days_left })}`}
                  </div>
                </div>
              </div>

              {/* Причина отклонения — рядом с самим объявлением, а не в
                  письме, которое надо искать: человек читает и тут же
                  правит. */}
              {item.status === 'rejected' && item.reason && (
                <div className="tg-my-reason">{item.reason}</div>
              )}

              {editing === item.id ? (
                <div className="tg-my-edit">
                  <input
                    className="field-input"
                    value={draft.title}
                    onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                    placeholder={t('tg_post.what_ph')}
                    maxLength={120}
                    enterKeyHint="done"
                  />
                  <textarea
                    className="field-input field-textarea"
                    value={draft.description}
                    onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                    placeholder={t('tg_post.about_ph')}
                    rows={3}
                    maxLength={2000}
                  />
                  <div className="tg-my-actions">
                    <button
                      className="form-save"
                      disabled={busy === item.id || draft.title.trim().length < 5}
                      onClick={() => saveEdit(item)}
                    >
                      {t('tg_my.send_again')}
                    </button>
                    <button className="form-secondary" onClick={() => setEditing(null)}>
                      {t('actions.cancel')}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="tg-my-actions">
                  {item.status === 'rejected' && (
                    <button className="chip chip-active" onClick={() => startEdit(item)}>
                      {t('tg_my.fix')}
                    </button>
                  )}
                  {item.status === 'active' && (
                    <>
                      <button
                        className="chip"
                        disabled={busy === item.id}
                        onClick={() => act(item.id, () => api.tgMarkSold(item.id))}
                      >
                        {t('tg_my.sold')}
                      </button>
                      <button className="chip" onClick={() => startEdit(item)}>
                        {t('tg_my.edit')}
                      </button>
                      {item.days_left != null && item.days_left <= 7 && (
                        <button
                          className="chip"
                          disabled={busy === item.id}
                          onClick={() => act(item.id, () => api.tgRenewListing(item.id))}
                        >
                          {t('tg_my.renew')}
                        </button>
                      )}
                    </>
                  )}
                  <a className="chip" href={item.url} target="_blank" rel="noopener noreferrer">
                    {t('tg_my.open')}
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {items.length > 0 && (
        <Link className="form-secondary tg-my-new" to="/tg/post">{t('tg_my.new')}</Link>
      )}
    </div>
  )
}
