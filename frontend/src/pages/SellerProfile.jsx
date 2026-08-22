import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import ListingCard from '../components/ListingCard'
import SellerReviews from '../components/SellerReviews'
import { CardSkeletons } from '../components/Skeletons'

/**
 * Открытая страница продавца.
 *
 * Отзывы жили на самом объявлении и занимали больше места, чем оно само.
 * Здесь для них есть простор, а с карточки продавца сюда ведёт нажатие —
 * покупатель приходит, когда действительно захотел посмотреть на человека.
 */
export default function SellerProfile() {
  const { id } = useParams()
  const { t, i18n } = useTranslation()

  const [profile, setProfile] = useState(null)
  const [listings, setListings] = useState([])
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!id) return
    api.sellerProfile(id, i18n.language).then(setProfile).catch(() => setFailed(true))
    api.sellerListings(id, i18n.language).then((r) => setListings(r.items || [])).catch(() => setListings([]))
  }, [id, i18n.language])

  if (failed) {
    return (
      <div className="page">
        <PageHeader title={t('seller.title')} />
        <p className="seller-missing">{t('seller.not_found')}</p>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="page">
        <PageHeader title={t('seller.title')} />
        <CardSkeletons count={2} />
      </div>
    )
  }

  // «на сайте с ...» — год и месяц: точная дата ничего не добавляет,
  // а вот давно ли человек здесь, покупателю важно
  const since = profile.created_at
    ? new Date(profile.created_at + 'Z').toLocaleDateString(i18n.language, { year: 'numeric', month: 'long' })
    : null

  return (
    <div className="page">
      <PageHeader title={t('seller.title')} />

      <div className="seller-head">
        <div className="seller-avatar lg">{profile.display_name?.[0] || '?'}</div>
        <div className="seller-head-info">
          <div className="seller-name lg">
            {profile.company_name || profile.display_name}
            {(profile.phone_verified || profile.company_verified) && (
              <div className="seal seal-sm">
                <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3"><path d="M20 6 9 17l-5-5" /></svg>
              </div>
            )}
          </div>
          {profile.rating_count > 0 && (
            <div className="seller-head-rating">
              <span className="seller-head-avg">{profile.rating_avg.toFixed(1)}</span>
              <span className="seller-head-count">{t('rev.count', { count: profile.rating_count })}</span>
            </div>
          )}
          {since && <div className="seller-since">{t('seller.since', { date: since })}</div>}
        </div>
      </div>

      {listings.length > 0 && (
        <div className="seller-section">
          <div className="seller-section-title">
            {t('seller.listings')} · {profile.active_listings}
          </div>
          <div className="infinite-grid no-pad">
            {listings.map((l) => <ListingCard key={l.id} listing={l} />)}
          </div>
        </div>
      )}

      <div className="seller-section">
        <SellerReviews sellerId={profile.id} />
      </div>
    </div>
  )
}
