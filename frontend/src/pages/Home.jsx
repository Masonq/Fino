import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import LanguageSwitcher from '../components/LanguageSwitcher'

const CITIES = ['Београд', 'Нови Сад', 'Ниш', 'Крагујевац', 'Суботица']

export default function Home() {
  const { t, i18n } = useTranslation()
  const [categories, setCategories] = useState([])
  const [listings, setListings] = useState([])
  const [cols, setCols] = useState(2)
  const [city, setCity] = useState(CITIES[0])

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    api.searchListings({ lang: i18n.language, limit: 12 })
      .then((res) => setListings(res.items || []))
      .catch(() => setListings([]))
  }, [i18n.language])

  return (
    <div className="home">
      <div className="avito-banner">
        <div className="avito-toprow">
          <Link to="/search" className="avito-search">
            <div className="avito-search-logo">
              <span style={{ background: 'var(--primary)' }} />
              <span style={{ background: 'var(--violet)' }} />
              <span style={{ background: 'var(--coral)' }} />
            </div>
            <span>{t('search.placeholder')}</span>
            <span className="avito-search-divider" />
            <span className="avito-search-filter" aria-label="Фильтры">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
            </span>
          </Link>
          <Link to="/identify" className="avito-login-pill">
            {localStorage.getItem('fino_user_id') ? <div className="avatar-mini">М</div> : t('common.login')}
          </Link>
        </div>

        <Link to="/search" className="avito-promo-row">
          <span className="avito-promo-text">{t('common.safe_deal')} <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6"><path d="m9 6 6 6-6 6" /></svg></span>
          <div className="avito-promo-illustration">
            <img src="/promo-safe-deal.png" alt="" />
          </div>
        </Link>
      </div>

      <div className="page-meta-row">
        <div className="city-pill">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" /><circle cx="12" cy="9" r="2.5" />
          </svg>
          <select value={city} onChange={(e) => setCity(e.target.value)} aria-label="Город">
            {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" className="city-pill-chevron">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
        <LanguageSwitcher />
      </div>

      <div className="cat-grid-2row">
        <Link to="/categories" className="cat-tile-2row all">
          <div className="cat-tile-2row-label">{t('common.all')}</div>
          <div className="cat-tile-2row-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>
          </div>
        </Link>
        {categories.map((cat) => (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="cat-tile-2row">
            <div className="cat-tile-2row-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
            {cat.image_url && (
              <div className="cat-tile-2row-photo"><img src={cat.image_url} alt="" /></div>
            )}
          </Link>
        ))}
      </div>

      <div className="feed-head-row">
        <div className="feed-heading">{t('common.recommendations')}</div>
        <div className="col-toggle">
          <button className={cols === 2 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(2)} aria-label="По 2 в ряд">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /></svg>
          </button>
          <button className={cols === 1 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(1)} aria-label="По 1 в ряд">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
          </button>
        </div>
      </div>

      <div className={cols === 2 ? 'infinite-grid' : 'infinite-list'}>
        {listings.map((l) => (
          <ListingCard key={l.id} listing={l} large={cols === 1} />
        ))}
        {listings.length === 0 && (
          <p className="empty-hint">{t('common.no_listings')}</p>
        )}
      </div>
    </div>
  )
}
