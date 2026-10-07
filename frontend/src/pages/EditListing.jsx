import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { CITIES, CITY_COORDS, cityLabel } from '../data/cities'
import PageHeader from '../components/PageHeader'
import { EditFormSkeleton } from '../components/Skeletons'
import LocationPicker from '../components/LocationPicker'
import PriceField from '../components/PriceField'
import Sheet from '../components/Sheet'

export default function EditListing() {
  const { t, i18n } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [listing, setListing] = useState(null)
  // характеристики раздела (комнаты, марка, размер…) — как при размещении; раньше в правке их не было вовсе
  const [attrs, setAttrs] = useState({})
  const [schema, setSchema] = useState([])
  // раздел: можно сменить, если ошибся при размещении
  const [catSlug, setCatSlug] = useState('')
  const [catPath, setCatPath] = useState('')
  const [catOpen, setCatOpen] = useState(false)
  const [catQuery, setCatQuery] = useState('')
  const [tree, setTree] = useState([])
  const loadSchema = (slug, keep) => api.getCategorySchema(slug).then((r) => {
    const sc = Array.isArray(r) ? r : (r?.attribute_schema || r?.fields || [])
    setSchema(sc)
    // при смене раздела оставляем только подходящие новому разделу характеристики
    if (!keep) setAttrs((a) => Object.fromEntries(Object.entries(a).filter(([k]) => sc.some((f) => f.key === k))))
  }).catch(() => setSchema([]))
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState('RSD')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState('')
  const [locationLat, setLocationLat] = useState(null)
  const [locationLng, setLocationLng] = useState(null)
  const [hideExactAddress, setHideExactAddress] = useState(false)
  const [mapOpen, setMapOpen] = useState(false)
  const [photos, setPhotos] = useState([])
  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoError, setPhotoError] = useState('')
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
        setCurrency(l.currency === 'EUR' ? 'EUR' : 'RSD')
        setNegotiable(!!l.price_negotiable)
        setCity(l.city || '')
        if (l.location_lat != null) {
          setLocationLat(l.location_lat)
          setLocationLng(l.location_lng)
          setMapOpen(true)
        }
        setHideExactAddress(!!l.hide_exact_address)
        setPhotos(l.photos || [])
        setAttrs(l.attributes || {})
        const slug = l.category_slug || l.category?.slug
        setCatSlug(slug || '')
        const path = (l.category_path || []).map((c) => (typeof c.name === 'string' ? c.name : c.name?.[i18n.language] || c.name?.ru)).filter(Boolean)
        setCatPath(path.join(' › '))
        if (slug) loadSchema(slug, true)
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

  // Видео — запись в той же коллекции photos (is_video:true), не
  // отдельное поле объявления: то же самое, что уже устроено для фото
  // (add/deleteListingPhoto — сразу на сервер, не ждёт «Сохранить»),
  // просто перед прикреплением ещё и перекодируется.
  const hasVideo = photos.some((p) => p.is_video)

  const handleVideoSelect = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || hasVideo || photos.length >= 10) return
    setVideoError('')
    setVideoBusy(true)
    try {
      const uploaded = await api.uploadVideo(file)
      const attached = await api.addListingPhoto(id, {
        url: uploaded.video_url,
        thumbnail_url: uploaded.video_thumbnail_url,
        is_video: true,
      })
      setPhotos((prev) => [...prev, attached])
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
        currency,
        price_negotiable: negotiable,
        city: city || null,
        location_lat: locationLat,
        location_lng: locationLng,
        hide_exact_address: hideExactAddress,
        ...(schema.length ? { attributes: attrs } : {}),
        ...(catSlug && catSlug !== (listing?.category_slug || listing?.category?.slug) ? { category_slug: catSlug } : {}),
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
                <img src={p.is_video ? p.thumbnail_url : p.url} alt="" />
                {p.is_video && (
                  <span className="grid-video-badge">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="#fff"><path d="M8 5v14l11-7z" /></svg>
                  </span>
                )}
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
            {photos.length < 10 && !hasVideo && (
              <label className={videoBusy ? 'photo-add disabled' : 'photo-add'}>
                <input type="file" accept="video/mp4,video/quicktime,video/webm,video/3gpp" onChange={handleVideoSelect} disabled={videoBusy} hidden />
                {videoBusy
                  ? <span className="spinner" />
                  : <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2" /></svg>}
                {videoBusy ? t('post.video_processing') : t('post.video_add')}
              </label>
            )}
          </div>
          {photoError && <p className="auth-error">{photoError}</p>}
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

        {/* раздел — с кнопкой «Изменить»: поиск по всем конечным разделам с путём, как «Перенести в раздел» */}
        <div className="post-field">
          <label>{t('edit.category')}</label>
          <button type="button" className="edit-cat" onClick={() => {
            setCatOpen(true)
            if (!tree.length) api.getCategories().then((r) => setTree(Array.isArray(r) ? r : (r?.items || []))).catch(() => {})
          }}>
            <span>{catPath || '—'}</span><b>{t('actions.change')}</b>
          </button>
        </div>

        {schema.length > 0 && (
          <div className="edit-attrs">
            <div className="edit-attrs-title">{t('detail.params')}</div>
            {schema.map((field) => {
              const label = field.label?.[i18n.language] || field.label?.ru || field.key
              const set = (v) => setAttrs((a) => ({ ...a, [field.key]: v }))
              return (
                <div key={field.key} className="post-field">
                  {field.type !== 'boolean' && <label>{label}{field.required && ' *'}</label>}
                  {field.type === 'text' && <input type="text" value={attrs[field.key] ?? ''} onChange={(e) => set(e.target.value)} />}
                  {field.type === 'number' && <input type="number" inputMode="decimal" value={attrs[field.key] ?? ''} onChange={(e) => set(e.target.value)} />}
                  {field.type === 'boolean' && (
                    <label className="post-checkbox"><input type="checkbox" checked={!!attrs[field.key]} onChange={(e) => set(e.target.checked)} />{label}</label>
                  )}
                  {field.type === 'select' && (
                    <select value={attrs[field.key] ?? ''} onChange={(e) => set(e.target.value)}>
                      <option value="">—</option>
                      {field.options?.map((opt) => <option key={opt.value} value={opt.value}>{opt.label?.[i18n.language] || opt.label?.ru || opt.value}</option>)}
                    </select>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Цена во всю ширину, с валютой внутри поля, и «Торг уместен»
            сразу под ней: это свойство цены. Раньше галочка стояла
            после города и карты, а цена делила строку с городом — с
            переключателем валюты в половине экрана семизначная цена
            (квартира в евро) уже не помещалась. */}
        <PriceField
          label={t('post.price')}
          price={price}
          currency={currency}
          onPrice={setPrice}
          onCurrency={setCurrency}
        />
        <label className="filter-check">
          <input type="checkbox" checked={negotiable} onChange={(e) => setNegotiable(e.target.checked)} />
          {t('post.negotiable')}
        </label>

        <div className="post-field">
          <label>{t('post.city')}</label>
          <select value={city} onChange={(e) => setCity(e.target.value)}>
            {CITIES.map((c) => (
              <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>
            ))}
          </select>
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
      <Sheet open={catOpen} onClose={() => setCatOpen(false)} title={t('edit.category')}>
        <input className="move-search" placeholder={t('move.search')} value={catQuery} onChange={(e) => setCatQuery(e.target.value)} />
        <div className="move-list">
          {(() => {
            const nm = (c) => (typeof c.name === 'string' ? c.name : c.name?.[i18n.language] || c.name?.ru || c.slug)
            const out = []
            const walk = (n, trail) => { const kids = n.children || []; if (!kids.length && trail.length) out.push({ c: n, path: trail.join(' › ') }); kids.forEach((k) => walk(k, [...trail, nm(n)])) }
            tree.forEach((r) => walk(r, []))
            const q = catQuery.trim().toLowerCase()
            const shown = q ? out.filter(({ c }) => nm(c).toLowerCase().includes(q)) : out
            if (!tree.length) return <div className="empty-hint">…</div>
            if (!shown.length) return <div className="empty-hint">{t('move.nothing')}</div>
            return shown.slice(0, 200).map(({ c, path }) => (
              <button key={c.slug} type="button" className="reasons-item move-found" onClick={() => {
                setCatSlug(c.slug); setCatPath(`${path} › ${nm(c)}`); setCatOpen(false); setCatQuery(''); loadSchema(c.slug, false)
              }}>
                <b>{nm(c)}</b><span>{path}</span>
              </button>
            ))
          })()}
        </div>
      </Sheet>
    </div>
  )
}
