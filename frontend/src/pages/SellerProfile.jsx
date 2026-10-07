import { useCallback, useEffect, useRef, useState } from 'react'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import ListingCard from '../components/ListingCard'
import SellerReviews from '../components/SellerReviews'
import ReportButton from '../components/ReportButton'
import { sinceMonth } from '../utils/time'
import { CardSkeletons } from '../components/Skeletons'
import VerifiedMark from '../components/VerifiedMark'

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
  const navigate = useNavigate()
  const { user } = useAuth()

  const [profile, setProfile] = useState(null)
  const [listings, setListings] = useState([])
  const [total, setTotal] = useState(0)
  const [loadingMore, setLoadingMore] = useState(false)
  const [failed, setFailed] = useState(false)
  const [subBusy, setSubBusy] = useState(false)
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
    // Тот же класс утечки, что уже чинили на страницах категории,
    // объявления и поиска — переход между двумя продавцами (тот же
    // маршрут /seller/:id, другой :id) переиспользует один и тот же
    // компонент. Проверил настоящим переходом: имя ПРЕЖНЕГО продавца
    // было ещё видно даже после того, как URL уже сменился на нового —
    // менялось только спустя ~50мс, когда приходил ответ сервера.
    setProfile(null)
    setListings([])
    setTotal(0)
    setFailed(false)
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
      <div className="page page-wide">
        <PageHeader title={t('seller.title')} />
        <p className="seller-missing">{t('seller.not_found')}</p>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="page page-wide">
        <PageHeader title={t('seller.title')} />
        {/* скелет повторяет новую раскладку: карточка-шапка с аватаром и кнопкой, отзывы, заголовок, сетка */}
        <div className="seller-head seller-head-sk" aria-hidden="true">
          <span className="sk-block" style={{ width: 84, height: 84, borderRadius: '50%' }} />
          <span className="sk-block" style={{ width: 150, height: 24, borderRadius: 8 }} />
          <span className="sk-block" style={{ width: 120, height: 14, borderRadius: 7 }} />
          <span className="sk-block" style={{ width: 220, height: 48, borderRadius: 16 }} />
        </div>
        <div className="sk-block" style={{ height: 76, borderRadius: 24, margin: '12px 0 0' }} />
        <div className="sk-block" style={{ width: 170, height: 24, borderRadius: 8, margin: '22px 0 12px' }} />
        <CardSkeletons count={2} />
      </div>
    )
  }

  // «на сайте с ...» — год и месяц: точная дата ничего не добавляет,
  // а вот давно ли человек здесь, покупателю важно
  const since = profile.created_at
    ? sinceMonth(profile.created_at, i18n.language)
    : null

  const toggleSubscribe = async () => {
    if (!user) { navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`); return }
    setSubBusy(true)
    const was = profile.is_subscribed
    // сразу меняем на экране, не дожидаясь сервера — так кнопка реагирует мгновенно
    setProfile((p) => ({ ...p, is_subscribed: !was }))
    try {
      if (was) await api.unsubscribeFromSeller(profile.id)
      else await api.subscribeToSeller(profile.id)
    } catch {
      setProfile((p) => ({ ...p, is_subscribed: was }))
    } finally {
      setSubBusy(false)
    }
  }

  return (
    <div className="page page-wide">
      <PageHeader title={t('seller.title')}>
        <ReportButton
          targetUserId={profile.id} iconOnly renderMode="trigger"
          open={reportOpen} onOpenChange={setReportOpen}
        />
      </PageHeader>

      <div className="seller-head">
        <Avatar
          src={profile.avatar_url}
          name={profile.company_name || profile.display_name}
          className={profile.is_company ? 'seller-avatar lg is-company' : 'seller-avatar lg'}
        />
        <div className="seller-head-info">
          <div className="seller-name lg">
            <span className="name-text">{profile.company_name || profile.display_name}</span>
            <VerifiedMark official={profile.official} verified={profile.company_verified || profile.document_verified} size={20} />
          </div>
          {profile.is_company && <div className="seller-badge">{t('seller.company_badge')}</div>}
          {profile.rating_count > 0 && (
            <div className="seller-head-rating">
              <span className="seller-head-avg">{profile.rating_avg.toFixed(1)}</span>
              <span className="seller-head-count">{t('rev.count', { count: profile.rating_count })}</span>
            </div>
          )}
          {/* Скорость ответа: для покупателя это первое, что он хочет
              знать перед тем, как написать. Показываем порядок, а не
              точные минуты — «за 47 минут» звучало бы как обещание. */}
          {/* Значок активного продавца: отвечает быстро, есть отзывы,
              нет подтверждённых жалоб. Купить его нельзя — иначе он
              перестал бы что-либо значить. */}
          {profile.active_seller && (
            <div className="seller-active">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m13 2-9 12h7l-1 8 9-12h-7l1-8Z" /></svg>
              {t('seller.active')}
            </div>
          )}
          {profile.reply_speed && (
            <div className="seller-reply">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              {t(`seller.reply_${profile.reply_speed.label}`)}
            </div>
          )}
          {since && <div className="seller-since">{t('seller.since', { date: since })}</div>}
        </div>
        {(!user || user.id !== profile.id) && (
          <button
            type="button"
            className={profile.is_subscribed ? 'seller-sub-btn active' : 'seller-sub-btn'}
            onClick={toggleSubscribe}
            disabled={subBusy}
          >
            {profile.is_subscribed ? t('seller.subscribed') : t('seller.subscribe')}
          </button>
        )}
      </div>

      <ReportButton
        targetUserId={profile.id} renderMode="sheet"
        open={reportOpen} onOpenChange={setReportOpen}
      />

      {profile.company_description && (
        <div className="seller-company-about">{profile.company_description}</div>
      )}

      <div className="seller-section">
        <SellerReviews sellerId={profile.id} expected={profile.rating_count ?? profile.reviews_count} />
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
