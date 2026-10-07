import EmptyArt from '../components/EmptyArt'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import ListingCard from '../components/ListingCard'
import { CardSkeletons } from '../components/Skeletons'
import { readHistory, clearHistory } from '../data/history'

export default function History() {
  const { t, i18n } = useTranslation()

  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const load = () => {
    const ids = readHistory().map((x) => x.id)
    if (ids.length === 0) { setItems([]); setLoaded(true); return }

    api.listingsByIds(ids, i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }

  useEffect(load, [i18n.language])

  return (
    <div className="fav-page">
      <PageHeader title={t('history.title')} count={items.length} kicker={t('history.kicker')}>
        {/* кнопка есть всегда (пока пусто — невидима): иначе шапка меняла высоту, когда история загружалась */}
        <button
          className="history-clear"
          style={items.length ? undefined : { visibility: 'hidden' }}
          onClick={() => { clearHistory(); setItems([]) }}
        >
          {t('history.clear')}
        </button>
      </PageHeader>

      {!loaded ? (
        <div className="infinite-grid no-pad"><CardSkeletons count={4} /></div>
      ) : items.length === 0 ? (
        <div className="fav-empty">
          <EmptyArt name="history" />
          <p>{t('history.empty')}</p>
          <Link className="fav-cta" to="/">{t('actions.to_listings')}</Link>
        </div>
      ) : (
        <div className="infinite-grid no-pad">
          {items.map((l) => <ListingCard key={l.id} listing={l} />)}
        </div>
      )}
    </div>
  )
}
