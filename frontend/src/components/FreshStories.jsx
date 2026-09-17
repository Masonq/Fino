import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import { formatPrice } from '../utils/money'

// Полоска «Только что» в шапке главной — свежие объявления кружками,
// как сторис. Первый кружок — «Продать»: шапка зовёт не только
// смотреть, но и выкладывать своё.
//
// Кольцо: у непросмотренного свежего — акцентное, у просмотренного
// или старше суток — тонкое белое. Подпись под кружком — цена: это
// то, ради чего открывают объявление; время видно по кольцу.
export default function FreshStories({ items, seen, onOpen }) {
  const { t, i18n } = useTranslation()

  const cells = items === null
    ? Array.from({ length: 6 }, (_, i) => <div key={`sk${i}`} className="story story-skeleton"><div className="story-ring"><div className="story-photo" /></div><div className="story-label" /></div>)
    : items.map((l, i) => {
      const hot = l.fresh && !seen.has(l.id)
      return (
        <Link
          key={l.id}
          to={l.path}
          className={hot ? 'story hot' : 'story'}
          onClick={() => onOpen(l.id)}
          onTouchStart={() => api.prefetchListing(l.id)}
          onMouseEnter={() => api.prefetchListing(l.id)}
          aria-label={l.title}
        >
          <div className="story-ring">
            <div className="story-photo">
              <img
                src={l.cover_photo}
                alt=""
                loading={i < 6 ? 'eager' : 'lazy'}
                fetchpriority={i < 6 ? 'high' : 'auto'}
                decoding="async"
                style={{ viewTransitionName: `photo-${l.id}` }}
              />
            </div>
          </div>
          <div className={l.is_free ? 'story-label free' : 'story-label'}>
            {l.is_free ? t('detail.free') : (formatPrice(l.price, l.currency, i18n.language) || '—')}
          </div>
        </Link>
      )
    })

  if (items !== null && items.length === 0) return null

  return (
    <div className="stories" role="list">
      <Link to="/post" className="story story-post" role="listitem">
        <div className="story-ring">
          <div className="story-photo story-plus">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
          </div>
        </div>
        <div className="story-label">{t('fresh.post')}</div>
      </Link>
      {cells}
    </div>
  )
}
