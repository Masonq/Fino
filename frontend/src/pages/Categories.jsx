import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export default function Categories() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [categories, setCategories] = useState([])

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  return (
    <div className="categories-page">
      <div className="cats-head">
        <button className="cats-back" onClick={() => navigate(-1)} aria-label="Назад">←</button>
        <div className="cats-title">{t('common.all_categories')}</div>
      </div>

      <div className="cats-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ opacity: 0.4 }}>
          <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
        </svg>
        {t('common.find_category')}
      </div>

      <div className="cats-grid">
        {categories.map((cat) => (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="cats-item">
            <div className="cats-photo">
              {cat.image_url && <img src={cat.image_url} alt="" />}
              <div className="cats-dot" style={{ background: cat.color || '#0E9F6E' }} />
            </div>
            <div className="cats-label">{cat.name?.[i18n.language] || cat.name?.ru}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
