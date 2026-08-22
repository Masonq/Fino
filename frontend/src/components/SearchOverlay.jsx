import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { displayCity } from '../data/cities'
import { formatPrice } from '../utils/money'

export default function SearchOverlay({ open, onClose }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const [text, setText] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)

  // Фокус ставится сразу при открытии — мы остаёмся на той же странице,
  // поэтому iOS считает это продолжением жеста и показывает клавиатуру.
  useEffect(() => {
    if (open) inputRef.current?.focus()
    else { setText(''); setItems([]) }
  }, [open])

  useEffect(() => {
    if (!open || !text.trim()) { setItems([]); return }
    setLoading(true)
    const id = setTimeout(() => {
      api.searchListings({ q: text.trim(), lang: i18n.language, limit: 8 })
        .then((res) => setItems(res.items || []))
        .catch(() => setItems([]))
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(id)
  }, [text, open, i18n.language])

  const submit = () => {
    if (!text.trim()) return
    onClose()
    navigate(`/search?q=${encodeURIComponent(text.trim())}`)
  }

  if (!open) return null

  return (
    <div className="search-overlay">
      <div className="search-topbar">
        <button className="search-back" onClick={onClose} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="search-field">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            ref={inputRef}
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
            placeholder={t('search.placeholder_full')}
            autoComplete="off"
            enterKeyHint="search"
          />
          {text && (
            <button className="search-clear" onClick={() => { setText(''); inputRef.current?.focus() }} aria-label={t('actions.clear')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
      </div>

      <div className="search-suggest">
        {loading && <p className="empty-hint">{t('search.searching')}</p>}

        {!loading && text.trim() && items.length === 0 && (
          <p className="empty-hint">{t('search.nothing')}</p>
        )}

        {items.map((l) => (
          <button
            key={l.id}
            className="suggest-row"
            onClick={() => { onClose(); navigate(`/listing/${l.id}`) }}
          >
            <div className="suggest-thumb">
              {l.cover_photo && <img src={l.cover_photo} alt="" />}
            </div>
            <div className="suggest-body">
              <div className="suggest-title">{l.title}</div>
              <div className="suggest-meta">
                {formatPrice(l.price, l.currency, i18n.language) || t('detail.no_price')}
                {l.city && ` · ${displayCity(l.city, i18n.language)}`}
              </div>
            </div>
          </button>
        ))}

        {text.trim() && items.length > 0 && (
          <button className="suggest-all" onClick={submit}>
            {t('actions.show_more')}
          </button>
        )}
      </div>
    </div>
  )
}
