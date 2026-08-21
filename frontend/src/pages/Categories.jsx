import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { CategorySkeletons } from '../components/Skeletons'

export default function Categories() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [categories, setCategories] = useState([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    api.getCategories()
      .then(setCategories)
      .catch(() => setCategories([]))
      .finally(() => setLoaded(true))
  }, [])

  return (
    <div className="categories-page">
      <div className="cats-head">
        <button className="cats-back" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="cats-title">{t('common.all_categories')}</div>
      </div>

      <div className="cats-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ opacity: 0.4 }}>
          <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
        </svg>
        {t('common.find_category')}
      </div>

      <div className="cats-grid">
        {!loaded && Array.from({ length: 8 }).map((_, i) => (
          <div className="cats-item skeleton" key={`sk${i}`} />
        ))}
        {loaded && categories.map((cat) => (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="cats-item">
            <span className="cats-label">{cat.name?.[i18n.language] || cat.name?.ru}</span>
            <img
              className="cats-img"
              src={`/cat/${cat.slug}.png`}
              alt=""
              onError={(e) => { e.currentTarget.style.display = 'none' }}
            />
          </Link>
        ))}
      </div>
    </div>
  )
}
