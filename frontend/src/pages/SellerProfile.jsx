import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import ListingCard from '../components/ListingCard'
import SellerReviews from '../components/SellerReviews'
import ReportButton from '../components/ReportButton'
import { CardSkeletons } from '../components/Skeletons'

// Сколько карточек показывать, пока не развернули весь список.
const PREVIEW_COUNT = 6

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
  const [total, setTotal] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const [failed, setFailed] = useState(false)
  // По умолчанию — всего несколько карточек, не всё, что есть у
  // магазина: у некоторых продавцов тысячи объявлений, и до отзывов
  // внизу страницы было physически не долистать — подгрузка при
  // прокрутке услужливо подсовывала ещё и ещё, так и не давая дойти
  // до конца. Разворачивается по нажатию, не само.
  const [expanded, setExpanded] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const sentinelRef = useRef(null)

  useEffect(() => {
    if (!id) return
    api.sellerProfile(id, i18n.language).then(setProfile).catch(() => setFailed(true))
    api.sellerListings(id, i18n.language)
      .then((r) => { setListings(r.items || []); setTotal(r.total || 0) })
      .catch(() => { setListings([]); setTotal(0) })
  }, [id, i18n.language])

  const loadMore = useCallback(() => {
    if (loadingMore) return
    setLoadingMore(true)
    api.sellerListings(id, i18n.language, listings.length)
      .then((r) => setListings((prev) => [...prev, ...(r.items || [])]))
      .catch(() => {})
      .finally(() => setLoadingMore(false))
  }, [id, i18n.language, listings.length, loadingMore])

  // Подгрузка по мере прокрутки — только после того, как сам развернул
  // список: до этого хватает и первой горстки карточек, а бесконечная
  // подгрузка сама по себе и была причиной, почему до отзывов было не
  // добраться.
  useEffect(() => {
    if (!expanded) return
    if (listings.length === 0 || listings.length >= total) return
    const el = sentinelRef.current
    if (!el) return
    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore() },
      { rootMargin: '600px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [expanded, listings.length, total, loadMore])

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
      <PageHeader title={t('seller.title')}>
        <ReportButton
          targetUserId={profile.id} iconOnly renderMode="trigger"
          open={reportOpen} onOpenChange={setReportOpen}
        />
      </PageHeader>

      <div className="seller-head">
        <div className={profile.is_company ? 'seller-avatar lg is-company' : 'seller-avatar lg'}>
          {profile.avatar_url
            ? <img src={profile.avatar_url} alt="" />
            : (profile.company_name || profile.display_name)?.[0] || '?'}
        </div>
        <div className="seller-head-info">
          <div className="seller-name lg">
            {profile.company_name || profile.display_name}
            {(profile.phone_verified || profile.company_verified || profile.document_verified) && (
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

      <ReportButton
        targetUserId={profile.id} renderMode="sheet"
        open={reportOpen} onOpenChange={setReportOpen}
      />

      {profile.company_description && (
        <div className="seller-company-about">{profile.company_description}</div>
      )}

      <div className="seller-section">
        <SellerReviews sellerId={profile.id} />
      </div>

      {listings.length > 0 && (
        <div className="seller-section">
          <div className="seller-section-title">
            {t('seller.listings')} · {total}
          </div>
          <div className="infinite-grid no-pad">
            {(expanded ? listings : listings.slice(0, PREVIEW_COUNT)).map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
          {!expanded && total > PREVIEW_COUNT ? (
            <button className="seller-show-all" onClick={() => setExpanded(true)}>
              {t('seller.show_all', { count: total })}
            </button>
          ) : expanded && (
            <div ref={sentinelRef} className="feed-sentinel">
              {loadingMore && <span className="feed-loading">{t('actions.loading')}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
