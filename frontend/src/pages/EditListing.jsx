import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { CITIES, cityLabel } from '../data/cities'

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
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getListing(id)
      .then((l) => {
        setListing(l)
        setTitle(l.title || '')
        setDescription(l.description || '')
        setPrice(l.price != null ? String(l.price) : '')
        setNegotiable(!!l.price_negotiable)
        setCity(l.city || '')
      })
      .catch(() => setListing(null))
  }, [id])

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
    return <div className="fav-page"><h2>{t('edit.title')}</h2></div>
  }

  if (!user) {
    return (
      <div className="fav-page">
        <h2>{t('edit.title')}</h2>
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
      <div className="fav-page">
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
    <div className="fav-page">
      <h2>{t('edit.title')}</h2>

      <div className="post-fields" style={{ padding: '0 12px' }}>
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

        <button className="auth-submit" disabled={busy} onClick={save}>
          {busy ? '…' : t('edit.save')}
        </button>
        <button className="review-cancel" style={{ marginTop: 8, width: '100%', padding: 13, borderRadius: 13 }} onClick={() => navigate(-1)}>
          {t('rev.cancel')}
        </button>
      </div>
    </div>
  )
}
