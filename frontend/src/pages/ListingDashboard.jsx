import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import PageHeader from '../components/PageHeader'
import BarsChart from '../components/BarsChart'

const PERIODS = [7, 14, 30]

/**
 * Показатели одного объявления — открывается из «Моих объявлений».
 *
 * Пока это просмотры по дням, избранное, начатые переписки. Когда
 * появится платное продвижение — здесь же будет видно, помогает ли
 * оно: сравнить дни с поднятием и без по тому же графику.
 */
export default function ListingDashboard() {
  const { id } = useParams()
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  const [days, setDays] = useState(14)
  const [data, setData] = useState(null)
  const [listing, setListing] = useState(null)
  const [denied, setDenied] = useState(false)

  useEffect(() => {
    api.getListing(id).then(setListing).catch(() => setListing(null))
  }, [id])

  useEffect(() => {
    setData(null)
    api.getListingDashboard(id, days)
      .then(setData)
      .catch((e) => {
        // 401 — вообще не вошёл, 403 — вошёл, но объявление не его.
        // Разные причины, и обе раньше ловились только частично: без
        // явной обработки 401 человек видел бы вечную загрузку.
        if (e.status === 401) navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
        else setDenied(true)
      })
  // Намеренно: navigate меняется при каждом переходе, а уход со страницы нужен ровно один раз.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, days])

  const title = listing?.title || ''

  // Среднее в день — нормализует «просмотров всего» под возраст
  // объявления: 50 просмотров за неделю и 50 за месяц говорят разное.
  const avgPerDay = (() => {
    if (!data?.published_at) return null
    const daysListed = Math.max(1, Math.round((Date.now() - new Date(data.published_at)) / 86400000))
    return (data.views_total / daysListed).toFixed(1)
  })()

  const daysLeft = (() => {
    if (!data?.expires_at) return null
    return Math.ceil((new Date(data.expires_at) - Date.now()) / 86400000)
  })()

  return (
    <div className="page page-narrow">
      <PageHeader title={t('ldash.title')} />

      {title && <div className="ldash-listing-title">{title}</div>}

      <div className="admin-filters">
        {PERIODS.map((p) => (
          <button
            key={p}
            className={`chip ${p === days ? 'chip-active' : ''}`}
            onClick={() => setDays(p)}
          >
            {t('stats.days', { count: p })}
          </button>
        ))}
      </div>

      {denied ? (
        <p className="empty-hint">{t('ldash.not_owner')}</p>
      ) : !data ? (
        <p className="empty-hint">{t('actions.loading')}</p>
      ) : (
        <>
          {/* Итог неделей и человеческим языком: цифры сами по себе не
              говорят, много это или мало, и что поправить. */}
          <div className="ldash-summary">
            {t('ldash.week_line', {
              views: data.views_week ?? 0,
              favorites: data.favorites_count,
              chats: data.chats_count,
            })}
          </div>

          {(data.tips || []).map((tip) => (
            <div className={`ldash-tip ${tip.level}`} key={tip.code}>
              <span className="ldash-tip-dot" aria-hidden="true" />
              <span>{t(`ldash.tip_${tip.code}`, { count: tip.count ?? 0 })}</span>
            </div>
          ))}

          <div className="stats-cards">
            <div className="stats-card">
              <div className="stats-value">{data.views_total}</div>
              <div className="stats-label">{t('ldash.views_total')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.favorites_count}</div>
              <div className="stats-label">{t('ldash.favorites')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.chats_count}</div>
              <div className="stats-label">{t('ldash.chats')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">
                {data.views_total > 0
                  ? `${((data.chats_count / data.views_total) * 100).toFixed(1)}%`
                  : '—'}
              </div>
              <div className="stats-label">{t('ldash.conversion')}</div>
            </div>
            {avgPerDay !== null && (
              <div className="stats-card">
                <div className="stats-value">{avgPerDay}</div>
                <div className="stats-label">{t('ldash.avg_per_day')}</div>
              </div>
            )}
            {daysLeft !== null && (
              <div className="stats-card">
                <div className="stats-value">{daysLeft > 0 ? daysLeft : t('ldash.expires_today')}</div>
                <div className="stats-label">{t('ldash.days_left')}</div>
              </div>
            )}
          </div>

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_day')}</div>
            <BarsChart key={days} items={data.daily} valueKey="views" unitKey="ldash.views_unit" promotions={data.promotions || []} />
          </div>

          {!data.is_complete && (
            <p className="ldash-hint">{t('ldash.incomplete_hint')}</p>
          )}
        </>
      )}
    </div>
  )
}
