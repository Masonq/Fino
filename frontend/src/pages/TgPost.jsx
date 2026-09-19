import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
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
  // Что мы поняли из названия: раздел, уверенность и что предложить,
  // если не уверены.
  const [guess, setGuess] = useState(null)
  const [category, setCategory] = useState(null)
  const [picking, setPicking] = useState(false)
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(null)
  const fileInput = useRef(null)

  // Вход. Пока он не прошёл, форму не показываем: публиковать
  // некому, а просить заполнить и потом отказать — худшее из решений.
  useEffect(() => {
    const app = tg()
    // Мост Telegram грузится на любой странице сайта, и сам по себе он
    // ничего не доказывает: в обычном браузере объект есть, а данных в
    // нём нет. Проверяем именно подписанную строку — без неё это не
    // Telegram, а человек, открывший адрес руками.
    if (!app?.initData) { setError('not_in_telegram'); return }
    app.ready()
    app.expand()
    api.tgWebAppAuth(app.initData)
      .then((res) => { api.setToken(res.token); setReady(true) })
      .catch(() => setError('auth_failed'))
  }, [])

  // Цвет окна под наш фон и запрет случайного закрытия.
  //
  // Telegram по умолчанию закрывает окно смахиванием вниз — тем же
  // движением, которым прокручивают форму. Заполнил четыре поля,
  // потянул список вверх чуть резче — и всё пропало. Просим Telegram
  // спрашивать подтверждение и, где умеет, вовсе отключить смахивание.
  useEffect(() => {
    const app = tg()
    if (!app) return
    try { app.setBackgroundColor?.('#FAFAF9') } catch { /* не беда */ }
    // Появилось в Bot API 7.7; на старых клиентах метода нет, и тогда
    // остаётся подтверждение ниже.
    try { app.disableVerticalSwipes?.() } catch { /* не беда */ }
    // Подтверждение при закрытии: даже если смахивание сработает,
    // Telegram переспросит, а не выбросит заполненное молча.
    try { app.enableClosingConfirmation?.() } catch { /* не беда */ }
  }, [])

  // Спрашиваем раздел, когда человек перестал печатать: на каждую
  // букву — это полсотни запросов на одно объявление.
  useEffect(() => {
    if (!ready || title.trim().length < 4) { setGuess(null); return }
    const timer = setTimeout(() => {
      api.tgGuessCategory({ title, description, lang: i18n.language })
        .then((res) => { setGuess(res); if (res.sure) setCategory(null) })
        .catch(() => setGuess(null))
    }, 600)
    return () => clearTimeout(timer)
  }, [ready, title, description, i18n.language])

  const shown = category || guess?.category

  const pickPhotos = async (event) => {
    const chosen = Array.from(event.target.files || []).slice(0, 8 - photos.length)
    if (!chosen.length) return
    setUploading(true)
    setError('')
    try {
      const uploaded = []
      for (const file of chosen) {
        // Видео и фотографии выбираются одной кнопкой: человек не
        // обязан знать заранее, что у него в галерее, — разбираемся
        // сами по типу файла. Видео к объявлению одно: два ролика
        // подряд никто не смотрит.
        if (file.type.startsWith('video/')) {
          if (photos.some((p) => p.is_video)) { setError('video_one'); continue }
          const res = await api.uploadVideo(file)
          uploaded.push({
            url: res.url, thumbnail_url: res.thumbnail_url, is_video: true,
          })
          continue
        }
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

  // Видео вместо фотографии не годится: в ленте видна обложка, а у
  // ролика её может не быть — вещь без снимка не продаётся.
  const canSend = photos.some((p) => !p.is_video) && title.trim().length >= 5
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
        photos: photos.map((p) => ({
          url: p.url, thumbnail_url: p.thumbnail_url, is_video: !!p.is_video,
        })),
        lang: i18n.language,
        category_id: category?.id || guess?.category?.id || null,
      })
      setDone(res)
      // Объявление ушло, терять больше нечего: подтверждение при
      // закрытии снимаем, иначе человек жмёт «вернуться в чат» и
      // получает лишний вопрос.
      try { tg()?.disableClosingConfirmation?.() } catch { /* не беда */ }
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
      {/* Знак сайта: человек открыл окно из переписки и должен сразу
          понимать, куда попал. В шапке Telegram название обрезано
          («PLONK — публикация объявле…»), и кроме неё опознать нас
          нечем. */}
      <div className="tg-head">
        <img className="tg-logo" src="/logo-mark.png" alt="PLONK" />
        <div className="tg-head-text">
          <div className="tg-title">{t('tg_post.title')}</div>
          <div className="tg-sub">{t('tg_post.subtitle')}</div>
        </div>
      </div>

      {/* Путь к своим объявлениям — строкой во всю ширину под шапкой.
          В самой шапке кнопка не помещалась в одну строку и делала ряд
          кривым: переносилась на две и становилась выше заголовка.
          Внизу страницы её не видно, пока не долистаешь. */}
      <Link className="tg-my-entry" to="/tg/my">
        <span className="tg-my-entry-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"
               strokeLinecap="round"><path d="M4 7h16M4 12h16M4 17h10" /></svg>
        </span>
        {t('tg_post.my_listings')}
        <svg className="tg-my-entry-arrow" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
      </Link>

      {/* Фотографии первыми: вещь без снимка не продаётся, и просить их
          после того, как человек уже всё описал, поздно. */}
      <div className="tg-photos">
        {photos.map((p, i) => (
          <div className={p.is_video ? 'tg-photo is-video' : 'tg-photo'} key={p.url}>
            {p.thumbnail_url || !p.is_video
              ? <img src={p.thumbnail_url || p.url} alt="" />
              : <video src={p.url} muted playsInline />}
            {p.is_video && (
              <span className="tg-photo-play" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
              </span>
            )}
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
            <input
              ref={fileInput}
              type="file"
              accept="image/*,video/*"
              multiple
              hidden
              onChange={pickPhotos}
            />
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
            // На iOS клавиатура закрывается клавишей «Готово», а она
            // появляется, только если поле внутри формы или ему задан
            // enterKeyHint. Формы тут нет — задаём подсказку сами,
            // иначе клавиатуру нечем убрать, и она закрывает половину
            // экрана вместе с кнопкой «Опубликовать».
            enterKeyHint="done"
            onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }}
          />

          {/* Что мы поняли — сразу под названием. Человек не выбирает
              раздел из дерева, но видит наш выбор и правит в одно
              нажатие. Когда разбор не уверен, показываем подходящие
              кнопками: верный обычно среди них. */}
          {shown && (
            <div className={guess?.sure || category ? 'tg-guess' : 'tg-guess unsure'}>
              <span className="tg-guess-text">
                {t('tg_post.section')}: <b>{shown.title}</b>
              </span>
              <button onClick={() => setPicking((v) => !v)}>
                {t('tg_post.change')}
              </button>
            </div>
          )}
          {guess && !guess.sure && !category && guess.options?.length > 1 && (
            <div className="tg-guess-note">
              {guess.category ? t('tg_post.pick_sub') : t('tg_post.not_sure')}
            </div>
          )}
          {/* Кнопки показываем, только когда есть из чего выбирать:
              одна кнопка с тем же разделом, что в строке выше, —
              бессмысленный повтор. */}
          {(picking || (guess && !guess.sure && !category))
            && guess?.options?.length > 1 && (
            <div className="field-chips tg-guess-options">
              {guess.options.map((option) => (
                <button
                  key={option.id}
                  className={shown?.id === option.id ? 'chip chip-active' : 'chip'}
                  onClick={() => { setCategory(option); setPicking(false) }}
                >
                  {option.title}
                </button>
              ))}
            </div>
          )}
        </label>

        <div className="field-row">
          {/* Подписи у строки нет нарочно: переключатель сам говорит,
              о чём речь, а «Цена» над кнопкой «Цена» — то же слово
              дважды подряд.

              «Бесплатно» было ссылкой сбоку и читалось как подсказка, а
              не как выбор: непонятно, нажата она или нет. Теперь это
              переключатель из двух состояний — «Цена» и «Даром», — и
              видно, что выбрано. Поле цены при «Даром» не гаснет, а
              исчезает: гасшее поле выглядит поломкой. */}
          <div className="tg-mode">
            <button
              className={free ? 'tg-mode-btn' : 'tg-mode-btn on'}
              onClick={() => setFree(false)}
            >
              {t('tg_post.mode_price')}
            </button>
            <button
              className={free ? 'tg-mode-btn on' : 'tg-mode-btn'}
              onClick={() => { setFree(true); setPrice('') }}
            >
              {t('tg_post.mode_free')}
            </button>
          </div>
          {!free && (
            <div className="tg-price">
              <input
                className="field-input"
                type="number"
                inputMode="numeric"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder={t('tg_post.price_ph')}
                autoFocus={false}
                enterKeyHint="done"
                onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }}
              />
              <span className="tg-currency">RSD</span>
            </div>
          )}
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
          <span className="field-label">
            {t('tg_post.about')}
            {/* В многострочном поле Enter переносит строку, поэтому
                закрыть клавиатуру им нельзя — даём кнопку рядом с
                подписью. Она появляется, только когда пишут. */}
            <button
              type="button"
              className="field-done"
              onClick={(e) => {
                e.preventDefault()
                document.activeElement?.blur?.()
              }}
            >
              {t('actions.done')}
            </button>
          </span>
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
