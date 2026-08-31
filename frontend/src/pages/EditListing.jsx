import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { CITIES, CITY_COORDS, cityLabel } from '../data/cities'
import PageHeader from '../components/PageHeader'
import { EditFormSkeleton } from '../components/Skeletons'
import LocationPicker from '../components/LocationPicker'

export default function EditListing() {
  const { t, i18n } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [listing, setListing] = useState(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState('')
  const [locationLat, setLocationLat] = useState(null)
  const [locationLng, setLocationLng] = useState(null)
  const [hideExactAddress, setHideExactAddress] = useState(false)
  const [mapOpen, setMapOpen] = useState(false)
  const [photos, setPhotos] = useState([])
  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoError, setPhotoError] = useState('')
  const [video, setVideo] = useState(null)
  const [videoBusy, setVideoBusy] = useState(false)
  const [videoError, setVideoError] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // Тот же защитный сброс, что и на других страницах, завязанных на
    // :id — на этой конкретной прямой ссылки «редактировать другое
    // объявление» в интерфейсе нет (всегда через список «Мои
    // объявления», это другой маршрут, полный перемонтаж), но раз уже
    // проверяли остальные страницы с тем же классом риска — на всякий
    // случай не оставляем данные прошлого объявления в полях формы
    // даже на миг, если такой переход когда-нибудь появится.
    setListing(null)
    setTitle('')
    setDescription('')
    setPrice('')
    setNegotiable(false)
    setCity('')
    setLocationLat(null)
    setLocationLng(null)
    setHideExactAddress(false)
    setPhotos([])
    setVideo(null)
    api.getListing(id)
      .then((l) => {
        setListing(l)
        // переводы приходят объектом по языкам — берём язык оригинала
        const tr = l.translations?.[l.source_language]
          || Object.values(l.translations || {})[0]
          || {}
        setTitle(tr.title || '')
        setDescription(tr.description || '')
        setPrice(l.price != null ? String(l.price) : '')
        setNegotiable(!!l.price_negotiable)
        setCity(l.city || '')
        if (l.location_lat != null) {
          setLocationLat(l.location_lat)
          setLocationLng(l.location_lng)
          setMapOpen(true)
        }
        setHideExactAddress(!!l.hide_exact_address)
        setPhotos(l.photos || [])
        if (l.video_url) setVideo({ url: l.video_url, thumbnail_url: l.video_thumbnail_url })
      })
      .catch(() => setListing(null))
  }, [id])

  const addPhoto = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || photos.length >= 10) return
    setPhotoBusy(true); setPhotoError('')
    try {
      const uploaded = await api.uploadPhoto(file)
      const attached = await api.addListingPhoto(id, {
        url: uploaded.url,
        thumbnail_url: uploaded.thumbnail_url || uploaded.url,
      })
      setPhotos((prev) => [...prev, attached])
    } catch {
      setPhotoError(t('edit.photo_failed'))
    } finally {
      setPhotoBusy(false)
    }
  }

  const removePhoto = async (photoId) => {
    setPhotoBusy(true); setPhotoError('')
    try {
      await api.deleteListingPhoto(id, photoId)
      setPhotos((prev) => prev.filter((p) => p.id !== photoId))
    } catch {
      setPhotoError(t('edit.photo_failed'))
    } finally {
      setPhotoBusy(false)
    }
  }

  // Видео — не отдельный эндпоинт с немедленным сохранением, как у
  // фото (add/deleteListingPhoto): одно поле самого объявления, как
  // координаты — грузится сразу (перекодирование на сервере занимает
  // время, ждать нажатия «Сохранить» после уже готового файла было бы
  // странно), но на сервер объявления улетает вместе с остальной
  // формой по кнопке «Сохранить».
  const handleVideoSelect = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setVideoError('')
    setVideoBusy(true)
    try {
      const res = await api.uploadVideo(file)
      setVideo({ url: res.video_url, thumbnail_url: res.video_thumbnail_url })
    } catch (err) {
      const map = {
        unsupported_format: t('post.video_err_format'),
        file_too_large: t('post.video_err_size'),
        video_too_long: t('post.video_err_length'),
        processing_failed: t('post.video_err_processing'),
      }
      setVideoError(map[err.code] || t('post.video_err_generic'))
    } finally {
      setVideoBusy(false)
    }
  }

  const removeVideo = () => { setVideo(null); setVideoError('') }

  // Обложка — просто фото на первом месте, отдельного поля на экране
  // нет: «сделать обложкой» — переставить это фото вперёд, остальные
  // сохраняют взаимный порядок. Оптимистично меняем сразу, откатываем
  // при ошибке — то же самое, что уже делает FavoritesContext.
  const makeCover = async (photoId) => {
    const before = photos
    const target = photos.find((p) => p.id === photoId)
    if (!target || photos[0]?.id === photoId) return
    const next = [target, ...photos.filter((p) => p.id !== photoId)]
    setPhotos(next)
    setPhotoBusy(true); setPhotoError('')
    try {
      await api.reorderListingPhotos(id, next.map((p) => p.id))
    } catch {
      setPhotos(before)
      setPhotoError(t('edit.photo_failed'))
    } finally {
      setPhotoBusy(false)
    }
  }

  const save = async () => {
    setBusy(true); setError('')
    try {
      await api.updateListing(id, {
        title: title.trim() || null,
        description: description.trim() || null,
        price: price ? Number(price) : null,
        price_negotiable: negotiable,
        city: city || null,
        location_lat: locationLat,
        location_lng: locationLng,
        hide_exact_address: hideExactAddress,
        video_url: video?.url || null,
        video_thumbnail_url: video?.thumbnail_url || null,
      })
      setSaved(true)
      setTimeout(() => navigate('/my'), 1200)
    } catch (e) {
      setError(e.code === 'not_owner' ? t('edit.not_owner') : t('auth.err_generic'))
    } finally {
      setBusy(false)
    }
  }

  if (authLoading || !listing) {
    return (
      <div className="fav-page edit-listing-page">
        <PageHeader title={t('edit.title')} />
        <EditFormSkeleton />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="fav-page edit-listing-page">
        <PageHeader title={t('edit.title')} />
        <div className="fav-empty">
          <p>{t('my.need_login')}</p>
          <button className="fav-cta" onClick={() => navigate(`/login?returnTo=%2Fedit%2F${id}`)}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  if (saved) {
    return (
      <div className="fav-page edit-listing-page">
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </div>
          <p>{t('edit.saved')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page edit-listing-page">
      <PageHeader title={t('edit.title')} />

      <div className="post-fields edit-fields">
        <div className="post-field">
          <label>{t('post.photos')} · {photos.length}/10</label>
          <div className="photo-grid">
            {photos.map((p, i) => (
              <div key={p.id} className="photo-thumb">
                <img src={p.url} alt="" />
                {i === 0 ? (
                  <span className="photo-cover-badge">{t('edit.cover')}</span>
                ) : (
                  <button
                    type="button"
                    className="photo-make-cover"
                    disabled={photoBusy}
                    onClick={() => makeCover(p.id)}
                  >
                    {t('edit.make_cover')}
                  </button>
                )}
                <button
                  type="button"
                  className="photo-remove"
                  disabled={photoBusy}
                  onClick={() => removePhoto(p.id)}
                  aria-label={t('actions.clear')}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.6"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
              </div>
            ))}
            {photos.length < 10 && (
              <label className={photoBusy ? 'photo-add disabled' : 'photo-add'}>
                <input type="file" accept="image/*" onChange={addPhoto} disabled={photoBusy} hidden />
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
                {t('post.photos')}
              </label>
            )}
          </div>
          {photoError && <p className="auth-error">{photoError}</p>}
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
          ) : videoBusy ? (
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
          {videoError && <p className="auth-error">{videoError}</p>}
        </div>

        <div className="post-field">
          <label>{t('listing.title')}</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        <div className="post-field">
          <label>{t('detail.description')}</label>
          <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div className="post-field-row">
          <div className="post-field">
            <label>{t('post.price')}</label>
            <input type="number" inputMode="decimal" pattern="[0-9]*" value={price} onChange={(e) => setPrice(e.target.value)} />
          </div>
          <div className="post-field">
            <label>{t('post.city')}</label>
            <select value={city} onChange={(e) => setCity(e.target.value)}>
              {CITIES.map((c) => (
                <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>
              ))}
            </select>
          </div>
        </div>

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
                  <label className="filter-check">
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

        <label className="filter-check">
          <input type="checkbox" checked={negotiable} onChange={(e) => setNegotiable(e.target.checked)} />
          {t('post.negotiable')}
        </label>

        <p className="edit-note">{t('edit.remoderation')}</p>

        {error && <p className="auth-error">{error}</p>}

        <div className="edit-actions">
          <button className="edit-save" disabled={busy} onClick={save}>
            {busy ? '…' : t('edit.save')}
          </button>
          <button className="edit-cancel" onClick={() => navigate(-1)}>
            {t('rev.cancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
