import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { CITIES, cityLabel } from '../data/cities'
import ContactHint from '../components/ContactHint'

/**
 * Публикатор внутри Telegram.
 *
 * Обычная форма размещения на сайте длинная и правильная: категория,
 * характеристики, состояние, доставка. Здесь другой случай — человек в
 * переписке, у него минута, и если спросить больше необходимого, он
 * закроет окно.
 *
 * Поэтому один экран и пять полей: фото, что продаёте, цена, город,
 * пара слов. Раздел не спрашиваем вовсе — его подбирает сам сайт по
 * заголовку, как делает это при переносе объявлений из чатов.
 *
 * Вход без кода и пароля: Telegram сам сообщает, кто открыл окно, и
 * подпись проверяется ключом бота.
 */
const tg = () => window.Telegram?.WebApp

export default function TgPost() {
  const { t, i18n } = useTranslation()

  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [photos, setPhotos] = useState([])
  const [uploading, setUploading] = useState(false)
  const [title, setTitle] = useState('')
  const [price, setPrice] = useState('')
  const [free, setFree] = useState(false)
  const [city, setCity] = useState(() => {
    try { return localStorage.getItem('plonk_city') || 'beograd' } catch { return 'beograd' }
  })
  const [description, setDescription] = useState('')
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(null)
  const fileInput = useRef(null)

  // Вход. Пока он не прошёл, форму не показываем: публиковать
  // некому, а просить заполнить и потом отказать — худшее из решений.
  useEffect(() => {
    const app = tg()
    if (!app) { setError('not_in_telegram'); return }
    app.ready()
    app.expand()
    api.tgWebAppAuth(app.initData)
      .then((res) => { api.setToken(res.token); setReady(true) })
      .catch(() => setError('auth_failed'))
  }, [])

  // Цвет окна под наш фон: иначе вокруг формы остаётся тёмная рамка
  // телеграмной темы, и экран выглядит чужим.
  useEffect(() => {
    const app = tg()
    if (app?.setBackgroundColor) {
      try { app.setBackgroundColor('#FAFAF9') } catch { /* не беда */ }
    }
  }, [])

  const pickPhotos = async (event) => {
    const chosen = Array.from(event.target.files || []).slice(0, 8 - photos.length)
    if (!chosen.length) return
    setUploading(true)
    try {
      const uploaded = []
      for (const file of chosen) {
        const res = await api.uploadPhoto(file)
        uploaded.push({ url: res.url, thumbnail_url: res.thumbnail_url })
      }
      setPhotos((prev) => [...prev, ...uploaded])
    } catch {
      setError('upload_failed')
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const canSend = photos.length > 0 && title.trim().length >= 5
    && (free || Number(price) > 0) && !sending

  const send = async () => {
    setSending(true)
    setError('')
    try {
      const res = await api.tgPublish({
        title: title.trim(),
        description: description.trim(),
        price: free ? null : Number(price),
        is_free: free,
        city,
        photos,
        lang: i18n.language,
      })
      setDone(res)
      tg()?.HapticFeedback?.notificationOccurred?.('success')
    } catch (err) {
      setError(err?.message === 'must_rename' ? 'must_rename' : 'send_failed')
      setSending(false)
    }
  }

  if (error === 'not_in_telegram') {
    return (
      <div className="tg-page">
        <p className="empty-hint">{t('tg_post.open_in_telegram')}</p>
      </div>
    )
  }

  if (done) {
    return (
      <div className="tg-page tg-done">
        <div className="tg-done-mark">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="M20 6 9 17l-5-5" /></svg>
        </div>
        <div className="tg-done-title">{t('tg_post.published')}</div>
        <p className="tg-done-text">
          {done.in_channel ? t('tg_post.published_channel') : t('tg_post.published_site')}
        </p>
        <a className="form-save" href={done.url} target="_blank" rel="noopener noreferrer">
          {t('tg_post.open_listing')}
        </a>
        <button className="form-secondary" onClick={() => tg()?.close?.()}>
          {t('tg_post.back_to_chat')}
        </button>
      </div>
    )
  }

  if (!ready) {
    // Ошибка входа показывалась строкой внутри формы, а форма при
    // неудачном входе не рисуется вовсе — человек видел вечное
    // «Загружаем…» и не понимал, что случилось.
    return (
      <div className="tg-page">
        {error
          ? (
            <div className="tg-done">
              <p className="tg-done-text">{t(`tg_post.err_${error}`, t('errors.generic'))}</p>
              <button className="form-secondary" onClick={() => window.location.reload()}>
                {t('actions.retry')}
              </button>
            </div>
          )
          : <p className="empty-hint">{t('actions.loading')}</p>}
      </div>
    )
  }

  return (
    <div className="tg-page">
      <div className="tg-head">
        <div className="tg-title">{t('tg_post.title')}</div>
        <div className="tg-sub">{t('tg_post.subtitle')}</div>
      </div>

      {/* Фотографии первыми: вещь без снимка не продаётся, и просить их
          после того, как человек уже всё описал, поздно. */}
      <div className="tg-photos">
        {photos.map((p, i) => (
          <div className="tg-photo" key={p.url}>
            <img src={p.thumbnail_url || p.url} alt="" />
            <button onClick={() => setPhotos(photos.filter((_, j) => j !== i))} aria-label={t('actions.delete')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </div>
        ))}
        {photos.length < 8 && (
          <label className="tg-photo tg-photo-add">
            {uploading ? '…' : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 5v14M5 12h14" /></svg>
            )}
            <input ref={fileInput} type="file" accept="image/*" multiple hidden onChange={pickPhotos} />
          </label>
        )}
      </div>

      <div className="form-card">
        <label className="field-row">
          <span className="field-label">{t('tg_post.what')}</span>
          <input
            className="field-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t('tg_post.what_ph')}
            maxLength={120}
          />
        </label>

        <div className="field-row">
          <span className="field-label">{t('tg_post.price')}</span>
          <div className="tg-price">
            <input
              className="field-input"
              type="number"
              inputMode="numeric"
              value={free ? '' : price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={free ? t('detail.free') : t('tg_post.price_ph')}
              disabled={free}
            />
            <button
              className={free ? 'chip chip-active' : 'chip'}
              onClick={() => { setFree(!free); setPrice('') }}
            >
              {t('detail.free')}
            </button>
          </div>
        </div>

        <div className="field-row">
          <span className="field-label">{t('listing.city')}</span>
          <select
            className="field-input"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          >
            {CITIES.map((c) => (
              <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>
            ))}
          </select>
        </div>

        <label className="field-row">
          <span className="field-label">{t('tg_post.about')}</span>
          <textarea
            className="field-input field-textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('tg_post.about_ph')}
            rows={4}
            maxLength={2000}
          />
          <ContactHint text={description} onFix={setDescription} />
        </label>
      </div>

      {error && <p className="auth-error">{t(`tg_post.err_${error}`, t('errors.generic'))}</p>}

      <button className="form-save" disabled={!canSend} onClick={send}>
        {sending ? t('tg_post.sending') : t('tg_post.publish')}
      </button>
      <p className="tg-note">{t('tg_post.note')}</p>
    </div>
  )
}
