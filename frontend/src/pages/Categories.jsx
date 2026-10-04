import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import TileArt, { useTileMeasure } from '../components/TileArt'
import { artLayoutMeasured, catSrc } from '../utils/artFit'
import { hasLanding } from '../data/landings'

export default function Categories() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [categories, setCategories] = useState([])
  const [loaded, setLoaded] = useState(false)
  const measure = useTileMeasure()
  // Плитки как у Авито и как внутри разделов: надпись сверху слева, картинка в правом нижнем углу, чуть за краем.
  // Ширина колонки — по настоящей ширине сетки (два столбца на телефоне), высота 96.
  const gridRef = useRef(null)
  const [colW, setColW] = useState(() => Math.floor((Math.min(window.innerWidth, 620) - 24 - 8) / 2))
  useLayoutEffect(() => {
    const el = gridRef.current
    if (!el) return undefined
    const calc = () => {
      const first = el.querySelector('.cats-tile')
      if (first?.offsetWidth) setColW(first.offsetWidth)
    }
    calc()
    const ro = new ResizeObserver(calc)
    ro.observe(el)
    return () => ro.disconnect()
  }, [loaded])

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

      <div className="cats-grid" ref={gridRef}>
        {!loaded && Array.from({ length: 8 }).map((_, i) => (
          <div className="cats-item skeleton" key={`sk${i}`} />
        ))}
        {/* Раздел без выбора помечаем честно: три объявления хуже,
            чем ни одного — они обещают выбор и не дают его. Заходить
            туда не запрещаем: вдруг человек ищет именно это, да и
            опубликовать первым он всё равно может. */}
        {loaded && categories.map((cat) => {
          const label = cat.name?.[i18n.language] || cat.name?.ru || ''
          const { fit } = artLayoutMeasured(label, { kind: '', tile: colW, text: colW - 26, art: 'big', h: 96 }, cat.slug, measure, colW - 26)
          return (
            <Link
              key={cat.id}
              to={hasLanding(cat.slug) ? `/c/${cat.slug}` : `/search?category=${cat.slug}`}
              className={`jl-tile cats-tile${cat.ready === false ? ' soon' : ''}`}
            >
              <span className="jl-tile-text" style={{ maxWidth: fit.text }}>{label}</span>
              {cat.ready === false && <span className="cats-soon">{t('categories.soon')}</span>}
              <TileArt src={catSrc(cat.slug)} name={label} fit={fit} />
            </Link>
          )
        })}
      </div>
    </div>
  )
}
