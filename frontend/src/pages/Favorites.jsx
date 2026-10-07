import { useAutoAnimate } from '@formkit/auto-animate/react'
import { useEffect, useState } from 'react'
import { useKeepPlace } from '../utils/keepPlace'
import { withoutRemoved } from '../utils/removedListings'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ListingCard from '../components/ListingCard'
import { CardSkeletons } from '../components/Skeletons'
import { useFavorites } from '../context/FavoritesContext'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

export default function Favorites() {
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('favorites')
  const { t, i18n } = useTranslation()
  // Удалили или добавили — соседи плавно съезжают (AutoAnimate, ~3 КБ; сам гаснет при «уменьшить движение»)
  const [listRef] = useAutoAnimate()
  const navigate = useNavigate()
  const { ids, idsLoaded } = useFavorites()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)
  // PLONK 2.0: порядок — недавно добавленные / дешевле / дороже / сначала подешевевшие
  const [sort, setSort] = useState('added')

  const userId = user?.id

  // Пока проверяется вход, пользователя ещё «нет» — раньше это считалось «загружено», и вошедший человек видел
  // сначала «войдите», потом «пусто», и только потом карточки. Теперь до ответа — скелет.
  useEffect(() => {
    if (authLoading) return
    if (!userId) { setLoaded(true); return }
    setLoaded(false)
    api.getFavorites(i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }, [userId, i18n.language, authLoading])

  // убираем из списка то, что сняли с сердечка прямо на этом экране
  const shown = idsLoaded ? items.filter((l) => ids.has(l.id)) : items
  const dropped = (l) => l.previous_price != null && l.price != null && Number(l.previous_price) > Number(l.price)
  const priceOf = (l) => (l.is_free ? 0 : l.price == null ? Infinity : Number(l.price) * (l.currency === 'RSD' ? 1 / 117 : 1))
  const visible = sort === 'added' ? shown
    : sort === 'drop' ? [...shown].sort((a, b) => Number(dropped(b)) - Number(dropped(a)))
      : [...shown].sort((a, b) => (sort === 'cheap' ? priceOf(a) - priceOf(b) : priceOf(b) - priceOf(a)))
  const nDropped = shown.filter(dropped).length

  if (!userId && !authLoading) {
    return (
      <div className="fav-page">
        <PageHeader title={t('favorites.title')} kicker={t('favorites.kicker_empty')} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </div>
          <p>{t('favorites.need_auth')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Ffavorites')}>
            {t('actions.continue')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fav-page">
      <PageHeader title={t('favorites.title')}
        kicker={!loaded ? '\u00a0' : visible.length ? `${t('favorites.kicker_n', { count: visible.length })}${nDropped ? ` · ${t('favorites.kicker_drop', { count: nDropped })}` : ''}` : t('favorites.kicker_empty')} />
      {/* сортировка видна и пока грузится — иначе она появлялась позже и сдвигала сетку вниз на 50 px */}
      {(!loaded || visible.length > 1) && (
        <div className="fav-sort">
          {[['added', t('favorites.sort_added')], ['drop', nDropped ? `${t('favorites.sort_drop')} · ${nDropped}` : t('favorites.sort_drop')], ['cheap', t('favorites.sort_cheap')], ['exp', t('favorites.sort_exp')]].map(([k, label]) => (
            <button key={k} type="button" className={`jr-tab${sort === k ? ' on' : ''}`} onClick={() => setSort(k)}>{label}</button>
          ))}
        </div>
      )}

      {!loaded ? (
        <div className="infinite-grid no-pad"><CardSkeletons count={4} /></div>
      ) : visible.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20.8 4.6a5 5 0 0 0-7.1 0L12 6.3l-1.7-1.7a5 5 0 1 0-7.1 7.1L12 20.3l8.8-8.8a5 5 0 0 0 0-6.9z" />
            </svg>
          </div>
          <p>{t('favorites.empty')}</p>
          <Link className="fav-cta" to="/">{t('actions.to_listings')}</Link>
        </div>
      ) : (
        <div className="infinite-grid no-pad" ref={listRef}>
          {withoutRemoved(visible).map((l) => <ListingCard key={l.id} listing={l} />)}
        </div>
      )}
    </div>
  )
}
