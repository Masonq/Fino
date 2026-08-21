import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import { CardSkeletons } from '../components/Skeletons'
import { CITIES, cityLabel } from '../data/cities'

const SORTS = [
  { key: 'new', labelKey: 'search.sort_new' },
  { key: 'cheap', labelKey: 'search.sort_cheap' },
  { key: 'expensive', labelKey: 'search.sort_expensive' },
]

const PAGE = 20

export default function Search() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  const [text, setText] = useState(params.get('q') || '')
  const [categories, setCategories] = useState([])
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loaded, setLoaded] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [cols, setCols] = useState(2)

  // фильтры
  const [category, setCategory] = useState(params.get('category') || '')
  const [priceMin, setPriceMin] = useState(params.get('price_min') || '')
  const [priceMax, setPriceMax] = useState(params.get('price_max') || '')
  const [city, setCity] = useState(params.get('city') || '')
  const [withPhoto, setWithPhoto] = useState(params.get('with_photo') === '1')
  const [sort, setSort] = useState(params.get('sort') || 'new')

  const inputRef = useRef(null)

  // Фокус на поле сразу при открытии экрана — иначе после нажатия на поиск
  // приходится тапать второй раз. Но только если запрос пустой: когда открыли
  // ссылку с готовым поиском или пришли из категории, клавиатура не нужна.
  useEffect(() => {
    if (params.get('q') || params.get('category')) return
    // небольшая задержка — iOS не отдаёт фокус, пока идёт переход между экранами
    const id = setTimeout(() => inputRef.current?.focus(), 120)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  const query = useMemo(() => {
    const p = { lang: i18n.language, limit: PAGE, offset: 0, sort }
    if (text.trim()) p.q = text.trim()
    if (category) p.category_slug = category
    if (priceMin) p.price_min = priceMin
    if (priceMax) p.price_max = priceMax
    if (city.trim()) p.city = city.trim()
    if (withPhoto) p.with_photo = true
    return p
  }, [text, category, priceMin, priceMax, city, withPhoto, sort, i18n.language])

  // поиск с задержкой, чтобы не дёргать сервер на каждую букву;
  // при первом открытии экрана ждать незачем — запрашиваем сразу
  const firstRun = useRef(true)
  useEffect(() => {
    const wait = firstRun.current ? 0 : 350
    firstRun.current = false
    const id = setTimeout(() => {
      setLoading(true)
      api.searchListings(query)
        .then((res) => { setItems(res.items || []); setTotal(res.total || 0) })
        .catch(() => { setItems([]); setTotal(0) })
        .finally(() => { setLoading(false); setLoaded(true) })
    }, wait)
    return () => clearTimeout(id)
  }, [query])

  // синхронизируем адрес страницы, чтобы результат можно было переслать ссылкой
  useEffect(() => {
    const next = {}
    if (text.trim()) next.q = text.trim()
    if (category) next.category = category
    if (priceMin) next.price_min = priceMin
    if (priceMax) next.price_max = priceMax
    if (city.trim()) next.city = city.trim()
    if (withPhoto) next.with_photo = '1'
    if (sort !== 'new') next.sort = sort
    setParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, category, priceMin, priceMax, city, withPhoto, sort])

  const loadMore = () => {
    setLoading(true)
    api.searchListings({ ...query, offset: items.length })
      .then((res) => setItems((prev) => [...prev, ...(res.items || [])]))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  const resetFilters = () => {
    setCategory(''); setPriceMin(''); setPriceMax(''); setCity(''); setWithPhoto(false); setSort('new')
  }

  const activeCount = [category, priceMin, priceMax, city, withPhoto ? '1' : ''].filter(Boolean).length

  return (
    <div className="search-page-full">
      <div className="search-topbar">
        <button className="search-back" onClick={() => navigate(-1)} aria-label={t('actions.back')}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
        </button>
        <div className="search-field">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            ref={inputRef}
            type="search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t('search.placeholder_full')}
            autoComplete="off"
          />
          {text && (
            <button className="search-clear" onClick={() => { setText(''); inputRef.current?.focus() }} aria-label={t('actions.clear')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>
        <button
          className={activeCount ? 'search-filter-btn on' : 'search-filter-btn'}
          onClick={() => setShowFilters((v) => !v)}
          aria-label={t('misc.filters')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
          {activeCount > 0 && <span className="filter-badge">{activeCount}</span>}
        </button>
      </div>

      {showFilters && (
        <div className="filters-panel">
          <div className="post-field">
            <label>{t('search.category')}</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">{t('search.all_categories')}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.slug}>{c.name?.[i18n.language] || c.name?.ru}</option>
              ))}
            </select>
          </div>

          <div className="post-field-row">
            <div className="post-field">
              <label>{t('search.price_from')}</label>
              <input type="number" inputMode="numeric" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} placeholder="0" />
            </div>
            <div className="post-field">
              <label>{t('search.price_to')}</label>
              <input type="number" inputMode="numeric" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} placeholder="—" />
            </div>
          </div>

          <div className="post-field">
            <label>{t('search.city')}</label>
            <select value={city} onChange={(e) => setCity(e.target.value)}>
              <option value="">{t('search.all_cities')}</option>
              {CITIES.map((c) => <option key={c.slug} value={c.slug}>{cityLabel(c.slug, i18n.language)}</option>)}
            </select>
          </div>

          <label className="filter-check">
            <input type="checkbox" checked={withPhoto} onChange={(e) => setWithPhoto(e.target.checked)} />
            {t('search.only_photo')}
          </label>

          <div className="sort-row">
            {SORTS.map((s) => (
              <button
                key={s.key}
                className={sort === s.key ? 'sort-chip active' : 'sort-chip'}
                onClick={() => setSort(s.key)}
              >
                {t(s.labelKey)}
              </button>
            ))}
          </div>

          {activeCount > 0 && (
            <button className="filters-reset" onClick={resetFilters}>{t('actions.reset_filters')}</button>
          )}
        </div>
      )}

      <div className="results-head">
        <span className="results-count">
          {!loaded ? t('search.searching') : `${t('search.found')}: ${total}`}
        </span>
        <div className="col-toggle">
          <button className={cols === 2 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(2)} aria-label={t('misc.cols_2')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="3" y="4" width="7" height="16" rx="1.5" /><rect x="14" y="4" width="7" height="16" rx="1.5" /></svg>
          </button>
          <button className={cols === 1 ? 'col-btn active' : 'col-btn'} onClick={() => setCols(1)} aria-label={t('misc.cols_1')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
          </button>
        </div>
      </div>

      <div className={cols === 2 ? 'infinite-grid' : 'infinite-list'}>
        {!loaded
          ? <CardSkeletons count={cols === 2 ? 4 : 2} />
          : items.map((l) => (
              <ListingCard key={l.id} listing={l} large={cols === 1} />
            ))}
      </div>

      {loaded && !loading && items.length === 0 && (
        <p className="empty-hint">{t('search.nothing')}</p>
      )}

      {items.length < total && (
        <button className="load-more" onClick={loadMore} disabled={loading}>
          {loading ? t('actions.loading') : t('actions.show_more')}
        </button>
      )}
    </div>
  )
}
