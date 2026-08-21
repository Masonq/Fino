import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Home() {
  const { t, i18n } = useTranslation()
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getCategories()
      .then(setCategories)
      .catch(() => setCategories([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="home">
      <h1>{t('app_name')}</h1>

      <div className="category-grid">
        {loading && <p>...</p>}
        {categories.map((cat) => (
          <Link key={cat.id} to={`/search?category=${cat.slug}`} className="category-card">
            <span className="category-name">{cat.name?.[i18n.language] || cat.name?.ru}</span>
          </Link>
        ))}
        {!loading && categories.length === 0 && (
          <p className="empty-hint">Категории появятся после сидирования БД (seed_categories.py)</p>
        )}
      </div>

      <Link to="/post" className="post-ad-btn">{t('listing.post_new')}</Link>
    </div>
  )
}
