import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { CITIES, CITY_COORDS, cityLabel } from '../data/cities'
import { shrinkImage } from '../data/shrinkImage'
import { useAuth } from '../context/AuthContext'
import CategoryArt from '../components/CategoryArt'
import LocationPicker from '../components/LocationPicker'

const STEPS = ['category', 'attributes', 'details', 'contact']

// Черновик — на случай случайного закрытия вкладки или сбоя сети
// посреди заполнения. Не вечно: через двое суток предлагать
// восстановить старую, наверняка уже неактуальную форму (цены,
// состояние вещи) хуже, чем просто дать начать заново.
const DRAFT_KEY = 'fino_post_draft'
const DRAFT_TTL_HOURS = 48

export default function PostAd() {
  const { t, i18n } = useTranslation()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [categories, setCategories] = useState([])
  const [category, setCategory] = useState(null)
  const [schema, setSchema] = useState([])
  const [attrs, setAttrs] = useState({})

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState('')
  const [locationLat, setLocationLat] = useState(null)
  const [locationLng, setLocationLng] = useState(null)
  const [hideExactAddress, setHideExactAddress] = useState(false)
  const [mapOpen, setMapOpen] = useState(false)
  const [photos, setPhotos] = useState([]) // [{url, thumbnail_url, uploading}]
  const [video, setVideo] = useState(null) // {url, thumbnail_url} | {uploading:true} | {failed:true} | null
  const [videoError, setVideoError] = useState('')

  const [phone, setPhone] = useState('')
  const [displayName, setDisplayName] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)
  const [path, setPath] = useState([])

  // Черновик, найденный при заходе на форму — ждёт решения человека
  // (восстановить / начать заново), пока не null. Сохранение текущего
  // ввода намеренно не идёт, пока это решение не принято — иначе
  // пустая свежая форма затёрла бы найденный черновик раньше, чем
  // человек успеет на него посмотреть.
  const [draftPrompt, setDraftPrompt] = useState(null)
  const draftResolved = useRef(false)

  useEffect(() => {
    let raw
    try { raw = localStorage.getItem(DRAFT_KEY) } catch { return }
    if (!raw) { draftResolved.current = true; return }
    try {
      const draft = JSON.parse(raw)
      const ageHours = (Date.now() - (draft.savedAt || 0)) / 3600000
      // Пустая форма (ни категории, ни заголовка) — сохранять было
      // нечего, не спрашиваем.
      const hasContent = draft.category || draft.title || draft.description
      if (ageHours < DRAFT_TTL_HOURS && hasContent) {
        setDraftPrompt(draft)
      } else {
        localStorage.removeItem(DRAFT_KEY)
        draftResolved.current = true
      }
    } catch {
      localStorage.removeItem(DRAFT_KEY)
      draftResolved.current = true
    }
  }, [])

  const restoreDraft = async () => {
    const d = draftPrompt
    setDraftPrompt(null)
    draftResolved.current = true
    if (!d) return
    if (d.category) {
      setCategory(d.category)
      setPath(d.path || [])
      try {
        const res = await api.getCategorySchema(d.category.slug)
        setSchema(res.attribute_schema || [])
      } catch { setSchema([]) }
    }
    setAttrs(d.attrs || {})
    setTitle(d.title || '')
    setDescription(d.description || '')
    setPrice(d.price || '')
    setCurrency(d.currency || 'EUR')
    setNegotiable(!!d.negotiable)
    setCity(d.city || '')
    if (d.locationLat != null) { setLocationLat(d.locationLat); setLocationLng(d.locationLng); setMapOpen(true) }
    setHideExactAddress(!!d.hideExactAddress)
    if (d.video?.url) setVideo(d.video)
    setPhotos(d.photos || [])
    setDisplayName(d.displayName || '')
    if (d.step != null) setStep(d.step)
  }

  const discardDraft = () => {
    localStorage.removeItem(DRAFT_KEY)
    setDraftPrompt(null)
    draftResolved.current = true
  }

  // Сохраняем на каждое осмысленное изменение — форма короткая (4
  // шага), а localStorage дешёвый; ждать отдельного debounce тут
  // избыточно. Только реально загруженные фото (со своим url) —
  // blob-ссылки на ещё не отправленные файлы не переживут
  // перезагрузку вкладки в любом случае.
  useEffect(() => {
    if (!draftResolved.current) return
    const hasContent = category || title || description
    if (!hasContent) {
      localStorage.removeItem(DRAFT_KEY)
      return
    }
    const draft = {
      savedAt: Date.now(), step, category, path, attrs, title, description,
      price, currency, negotiable, city, displayName, locationLat, locationLng, hideExactAddress,
      photos: photos.filter((p) => p.url && !p.uploading && !p.failed),
      video: video && video.url ? video : null,
    }
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify(draft)) } catch { /* переполнен или недоступен — не критично */ }
  }, [step, category, path, attrs, title, description, price, currency, negotiable, city, displayName, photos, locationLat, locationLng, hideExactAddress, video])

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  // Предзаполняем телефон, если человек уже указывал его раньше —
  // иначе вводить одно и то же при каждой публикации.
  useEffect(() => {
    if (!user) return
    api.me().then((me) => { if (me?.phone) setPhone(me.phone) }).catch(() => {})
  }, [user])

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [step])

  // Промежуточный выбор подкатегории. Отдельным шагом не делаем — это ещё
  // одна точка выхода из формы; показываем список прямо на первом шаге.
  // Путь вниз по категориям — массив, не одно значение: раньше parent
  // был единственным уровнем, и третий уровень было некуда деть.

  const pickCategory = async (cat) => {
    setCategory(cat)
    try {
      const res = await api.getCategorySchema(cat.slug)
      setSchema(res.attribute_schema || [])
      setAttrs({})
    } catch {
      setSchema([])
    }
    setStep(1)
  }

  const setAttr = (key, value) => setAttrs((prev) => ({ ...prev, [key]: value }))

  const handlePhotoSelect = async (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = '' // чтобы можно было выбрать тот же файл повторно

    const room = 10 - photos.length
    if (files.length > room) setError(t('post.photo_limit'))
    const chosen = files.slice(0, room)
    if (chosen.length === 0) return

    // Показываем все превью сразу, а грузим одновременно: по очереди
    // десять снимков с телефона занимают около минуты ожидания.
    const entries = chosen.map((file) => ({
      file,
      localId: `${Date.now()}-${Math.random()}`,
      previewUrl: URL.createObjectURL(file),
    }))
    setPhotos((prev) => [
      ...prev,
      ...entries.map(({ localId, previewUrl }) => ({ localId, previewUrl, uploading: true })),
    ])

    await Promise.all(entries.map(async ({ file, localId }) => {
      try {
        const prepared = await shrinkImage(file)
        const res = await api.uploadPhoto(prepared)
        setPhotos((prev) => prev.map((p) => (p.localId === localId ? { ...p, ...res, uploading: false } : p)))
      } catch {
        // помечаем ошибкой, а не убираем молча — иначе непонятно,
        // почему фото исчезло
        setPhotos((prev) => prev.map((p) => (p.localId === localId ? { ...p, uploading: false, failed: true } : p)))
      }
    }))
  }

  const removePhoto = (localId) => setPhotos((prev) => prev.filter((p) => p.localId !== localId))

  // Видео — одно на объявление, не массив: перекодирование на сервере
  // (см. media.py:upload_video) занимает заметное время, тут честный
  // спиннер, а не мгновенное превью, как у фото.
  const handleVideoSelect = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setVideoError('')
    setVideo({ uploading: true })
    try {
      const res = await api.uploadVideo(file)
      setVideo({ url: res.video_url, thumbnail_url: res.video_thumbnail_url })
    } catch (err) {
      setVideo(null)
      const map = {
        unsupported_format: t('post.video_err_format'),
        file_too_large: t('post.video_err_size'),
        video_too_long: t('post.video_err_length'),
        processing_failed: t('post.video_err_processing'),
      }
      setVideoError(map[err.code] || t('post.video_err_generic'))
    }
  }

  const removeVideo = () => { setVideo(null); setVideoError('') }

  const requiredAttrsFilled = schema
    .filter((f) => f.required)
    .every((f) => attrs[f.key] !== undefined && attrs[f.key] !== '')

  const handleSubmit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      if (!user?.id) {
        navigate('/login?returnTo=%2Fpost')
        return
      }

      await api.createListing({
        category_id: category.id,
        source_language: i18n.language,
        price: price ? Number(price) : null,
        currency,
        price_negotiable: negotiable,
        attributes: attrs,
        city,
        location_lat: locationLat,
        location_lng: locationLng,
        hide_exact_address: hideExactAddress,
        video_url: video?.url || null,
        video_thumbnail_url: video?.thumbnail_url || null,
        translations: [{ language: i18n.language, title, description }],
        photos: photos.filter((p) => p.url && !p.failed).map((p) => ({ url: p.url, thumbnail_url: p.thumbnail_url })),
      })

      // Телефон вводили на этом же шаге, но раньше он никуда не уходил —
      // просто терялся при отправке. Сохраняем в профиль, раз уж
      // человек его ввёл; не блокируем публикацию, если это не удастся.
      if (phone.trim()) {
        api.updateMe({ phone: phone.trim() }).catch(() => {})
      }

      localStorage.removeItem(DRAFT_KEY)
      setDone(true)
    } catch (e) {
      // Показываем, что именно не так, а не общее «не получилось»
      const map = {
        empty_title: t('post.need_title'),
        title_too_short: t('post.need_title'),
        bad_currency: t('post.err_currency'),
        too_many_listings_hour: t('limits.too_many_listings_hour'),
        too_many_listings_day: t('limits.too_many_listings_day'),
      }
      setError(map[e.code] || t('post.publish_failed'))
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <div className="post-ad-page post-success">
        <div className="seal" style={{ width: 56, height: 56, margin: '0 auto 16px' }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
        </div>
        <h2>{t('post.sent_title')}</h2>
        <p className="empty-hint">{t('post.sent_text')}</p>
        <button className="post-submit-btn" onClick={() => navigate('/')}>{t('actions.to_home')}</button>
      </div>
    )
  }

  // Вход сразу, а не на последнем шаге: раньше форма давала заполнить
  // всё, включая фото, и только на шаге контактов просила войти —
  // человек терял уже сделанную работу или недоумевал, почему фото не
  // прикрепляются молча (грузились без входа под лимитом по IP).
  if (authLoading) {
    return <div className="post-ad-page" />
  }
  if (!user) {
    return (
      <div className="post-ad-page">
        <div className="fav-empty">
          <p>{t('post.need_login')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fpost')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="post-ad-page">
      {draftPrompt && (
        <div className="draft-banner">
          <span>{t('post.draft_found')}</span>
          <div className="draft-banner-actions">
            <button className="draft-restore-btn" onClick={restoreDraft}>{t('post.draft_restore')}</button>
            <button className="draft-discard-btn" onClick={discardDraft}>{t('post.draft_discard')}</button>
          </div>
        </div>
      )}
      <div className="post-steps">
        {STEPS.map((s, i) => (
          <div key={s} className={i <= step ? 'post-step-dot active' : 'post-step-dot'} />
        ))}
      </div>

      {step === 0 && (() => {
        // Текущий уровень — либо корневые категории (path пуст), либо
        // дети последнего элемента пути. Один и тот же блок для любой
        // глубины — раньше было два отдельных (корень/один подуровень),
        // и третий уровень было решительно некуда деть: клик по
        // подкатегории с собственными детьми сразу завершал бы выбор,
        // пропуская их. Теперь клик проверяет наличие детей на каждом
        // шаге одинаково, вне зависимости от того, первый это уровень
        // или третий.
        const current = path.length ? path[path.length - 1] : null
        const items = current ? (current.children || []) : categories
        const isRoot = path.length === 0
        return (
          <>
            {!isRoot && (
              <button className="post-back" onClick={() => setPath((p) => p.slice(0, -1))}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m15 18-6-6 6-6" />
                </svg>
                {current.name?.[i18n.language] || current.name?.ru}
              </button>
            )}
            <h2>{isRoot ? t('listing.select_category') : t('listing.select_subcategory')}</h2>
            <div className={isRoot ? 'post-cat-grid' : 'post-sub-list'}>
              {items.map((cat) => (
                <button
                  key={cat.id}
                  className={isRoot ? 'post-cat-item' : 'post-sub-item'}
                  onClick={() => ((cat.children || []).length ? setPath((p) => [...p, cat]) : pickCategory(cat))}
                >
                  {isRoot ? (
                    <>
                      <span className="post-cat-label">
                        {cat.name?.[i18n.language] || cat.name?.ru}
                      </span>
                      <span className="post-cat-img"><CategoryArt slug={cat.slug} /></span>
                    </>
                  ) : (
                    cat.name?.[i18n.language] || cat.name?.ru
                  )}
                </button>
              ))}
            </div>
          </>
        )
      })()}

      {step === 1 && category && (
        <>
          <button className="post-back" onClick={() => setStep(0)}><svg className="back-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>{category.name?.[i18n.language] || category.name?.ru}</button>
          <h2>{t('post.step_params')}</h2>
          {schema.length === 0 && <p className="empty-hint">{t('post.no_params')}</p>}
          <div className="post-fields params-fields">
            {schema.map((field) => (
              <div key={field.key} className="post-field">
                <label>{field.label?.[i18n.language] || field.label?.ru || field.key}{field.required && ' *'}</label>
                {field.type === 'text' && (
                  <input type="text" value={attrs[field.key] || ''} onChange={(e) => setAttr(field.key, e.target.value)} />
                )}
                {field.type === 'number' && (
                  <input type="number" inputMode="decimal" pattern="[0-9]*" value={attrs[field.key] || ''} onChange={(e) => setAttr(field.key, e.target.value)} />
                )}
                {field.type === 'boolean' && (
                  <label className="post-checkbox">
                    <input type="checkbox" checked={!!attrs[field.key]} onChange={(e) => setAttr(field.key, e.target.checked)} />
                    {field.label?.[i18n.language] || field.label?.ru}
                  </label>
                )}
                {field.type === 'select' && (
                  <select value={attrs[field.key] || ''} onChange={(e) => setAttr(field.key, e.target.value)}>
                    <option value="" disabled>—</option>
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label?.[i18n.language] || opt.label?.ru}</option>
                    ))}
                  </select>
                )}
              </div>
            ))}
          </div>
          <button className="post-submit-btn" disabled={!requiredAttrsFilled} onClick={() => setStep(2)}>{t('actions.next')}</button>
        </>
      )}

      {step === 2 && (
        <>
          <button className="post-back" onClick={() => setStep(1)}><svg className="back-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>{t('actions.back')}</button>
          <h2>{t('post.step_details')}</h2>
          <div className="post-fields">
            <div className="post-field">
              <label>{t('listing.title')} *</label>
              <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t('post.title_ph')} />
            </div>
            <div className="post-field">
              <label>{t('listing.description')}</label>
              <textarea rows="4" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="post-field">
              <label>{t('post.photos')} · {photos.length}/10</label>
              <div className="photo-grid">
                {photos.map((p) => (
                  <div key={p.localId} className="photo-thumb">
                    <img src={p.thumbnail_url || p.previewUrl} alt="" />
                    {p.failed && (
                      <span className="photo-failed" title={t('post.photo_failed')}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                          <path d="M12 8v5M12 16h.01" />
                        </svg>
                      </span>
                    )}
                    {p.uploading && <div className="photo-thumb-loading"><span className="spinner" /></div>}
                    {!p.uploading && (
                      <button type="button" className="photo-remove" onClick={() => removePhoto(p.localId)} aria-label={t('actions.clear')}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6"><path d="M18 6 6 18M6 6l12 12" /></svg>
                      </button>
                    )}
                  </div>
                ))}
                {photos.length < 10 && (
                  <label className="photo-add">
                    <input type="file" accept="image/*" multiple onChange={handlePhotoSelect} hidden />
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
                    {t('post.photos')}
                  </label>
                )}
              </div>
            </div>
            <div className="post-field">
              <label>{t('post.video_optional')}</label>
              {video?.url ? (
                <div className="video-thumb">
                  <img src={video.thumbnail_url} alt="" />
                  <div className="video-play-badge">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff"><path d="M8 5v14l11-7z" /></svg>
                  </div>
                  <button type="button" className="photo-remove" onClick={removeVideo} aria-label={t('actions.clear')}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6"><path d="M18 6 6 18M6 6l12 12" /></svg>
                  </button>
                </div>
              ) : video?.uploading ? (
                <div className="video-thumb video-uploading">
                  <span className="spinner" />
                  <span className="video-uploading-text">{t('post.video_processing')}</span>
                </div>
              ) : (
                <label className="photo-add video-add">
                  <input type="file" accept="video/mp4,video/quicktime,video/webm,video/3gpp" onChange={handleVideoSelect} hidden />
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2" /></svg>
                  {t('post.video_add')}
                </label>
              )}
              {videoError && <div className="post-map-hint error">{videoError}</div>}
            </div>
            <div className="post-field-row">
              <div className="post-field">
                <label>{t('listing.price')}</label>
                <input type="number" inputMode="decimal" pattern="[0-9]*" value={price} onChange={(e) => setPrice(e.target.value)} />
              </div>
              <div className="post-field" style={{ maxWidth: 90 }}>
                <label>{t('post.currency')}</label>
                <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                  <option value="EUR">EUR</option>
                  <option value="RSD">RSD</option>
                </select>
              </div>
            </div>
            <label className="post-checkbox">
              <input type="checkbox" checked={negotiable} onChange={(e) => setNegotiable(e.target.checked)} />
              {t('listing.negotiable')}
            </label>
            <div className="post-field">
              <label>{t('post.city')}</label>
              <select value={city} onChange={(e) => setCity(e.target.value)}>
                <option value="">{t('post.choose_city')}</option>
                {CITIES.map((c) => <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>)}
              </select>
            </div>
            {/* Необязательно — только для тех, кому важна точная точка
                (недвижимость, услуги на выезд), большинству хватает
                текста города. Раскрывается по кнопке, а не всегда
                открыта: карта — тяжёлый компонент, не должна грузиться
                (и тянуть тайлы OpenStreetMap) у каждого, кто её не
                попросит. */}
            <div className="post-field">
              <button
                type="button"
                className="post-map-toggle"
                onClick={() => setMapOpen((v) => !v)}
              >
                {locationLat != null ? t('post.location_set') : t('post.location_add')}
                <span className={mapOpen ? 'chev up' : 'chev'}>›</span>
              </button>
              {mapOpen && (
                <>
                  <LocationPicker
                    value={locationLat != null ? [locationLat, locationLng] : null}
                    defaultCenter={CITY_COORDS[city] || null}
                    onChange={(lat, lng) => { setLocationLat(lat); setLocationLng(lng) }}
                  />
                  <div className="post-map-hint">{t('post.location_hint')}</div>
                  {locationLat != null && (
                    <>
                      <label className="post-checkbox">
                        <input
                          type="checkbox"
                          checked={hideExactAddress}
                          onChange={(e) => setHideExactAddress(e.target.checked)}
                        />
                        {t('post.hide_exact_address')}
                      </label>
                      <button
                        type="button"
                        className="post-map-clear"
                        onClick={() => { setLocationLat(null); setLocationLng(null) }}
                      >
                        {t('post.location_clear')}
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
          {/* Подсказываем, чего не хватает: кнопка просто серая — человек
              не понимает, почему нельзя продолжить. */}
          {(() => {
            const missing = []
            if (title.trim().length < 3) missing.push(t('post.need_title'))
            if (!city) missing.push(t('post.need_city'))
            return missing.length > 0 ? (
              <p className="post-hint">{missing.join(' · ')}</p>
            ) : null
          })()}
          <button
            className="post-submit-btn"
            disabled={title.trim().length < 3 || !city}
            onClick={() => setStep(3)}
          >
            {t('actions.next')}
          </button>
        </>
      )}

      {step === 3 && (
        <>
          <button className="post-back" onClick={() => setStep(2)}><svg className="back-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>{t('actions.back')}</button>
          <h2>{t('post.step_contact')}</h2>
          <div className="post-fields">
            <p className="empty-hint">{t('post.posting_as')} <b>{user.display_name}</b></p>
            <div className="post-field">
              <label>{t('post.phone')}</label>
              <input type="tel" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+381 6..." />
            </div>
          </div>
          {error && <p className="post-error">{error}</p>}
          <button
            className="post-submit-btn"
            disabled={submitting}
            onClick={handleSubmit}
          >
            {submitting ? '...' : t('listing.publish')}
          </button>
        </>
      )}
    </div>
  )
}
