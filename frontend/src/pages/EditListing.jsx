import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { CITIES, cityLabel } from '../data/cities'
import PageHeader from '../components/PageHeader'
import { EditFormSkeleton } from '../components/Skeletons'

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
  const [photos, setPhotos] = useState([])
  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoError, setPhotoError] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
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
        setPhotos(l.photos || [])
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

  const save = async () => {
    setBusy(true); setError('')
    try {
      await api.updateListing(id, {
        title: title.trim() || null,
        description: description.trim() || null,
        price: price ? Number(price) : null,
        price_negotiable: negotiable,
        city: city || null,
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
            {photos.map((p) => (
              <div key={p.id} className="photo-thumb">
                <img src={p.url} alt="" />
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
