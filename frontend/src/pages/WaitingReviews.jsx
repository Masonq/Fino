import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import PageHeader from '../components/PageHeader'
import Avatar from '../components/Avatar'
import { api } from '../api/client'

/**
 * Люди, которые ждут вашего отзыва.
 *
 * Приглашение появляется после переписки, похожей на сделку, но живёт
 * только в самой переписке: не открыл её — не узнал. Здесь они собраны
 * вместе, и у каждого видно, о ком и о какой вещи речь: «оставьте
 * отзыв» без имени и товара человеку ничего не говорит.
 */
export default function WaitingReviews() {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState(null)

  useEffect(() => {
    api.waitingReviews(i18n.language)
      .then((res) => setItems(res.items || []))
      .catch(() => setItems([]))
  }, [i18n.language])

  return (
    <div className="page page-narrow">
      <PageHeader title={t('reviews.waiting_title')} />

      {items === null ? (
        <div aria-hidden="true">{[0, 1, 2, 3].map((i) => <div key={i} className="sk-block" style={{ height: 76, borderRadius: 20, marginBottom: 10 }} />)}</div>
      ) : items.length === 0 ? (
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.8-5.4 2.8 1-6L3.2 9.4l6.1-.9L12 3Z" />
            </svg>
          </div>
          <p>{t('reviews.waiting_empty')}</p>
        </div>
      ) : (
        <div className="profile-menu">
          {items.map((item) => (
            <Link key={item.chat_id} className="waiting-row" to={`/chat/${item.chat_id}`}>
              <Avatar src={item.target_avatar} name={item.target_name} className="seller-avatar" />
              <div className="waiting-text">
                <div className="waiting-name">{item.target_name || t('reviews.someone')}</div>
                {item.listing_title && (
                  <div className="waiting-listing">{item.listing_title}</div>
                )}
              </div>
              {item.listing_photo && (
                <div className="waiting-thumb"><img src={item.listing_photo} alt="" /></div>
              )}
              <svg className="seller-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
