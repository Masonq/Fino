import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AdminStatsSkeleton } from '../components/Skeletons'
import BarsChart from '../components/BarsChart'

const PERIODS = [7, 14, 30]

export default function AdminStats() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [days, setDays] = useState(14)
  const [data, setData] = useState(null)
  const [daily, setDaily] = useState([])
  const [categories, setCategories] = useState([])
  const [sources, setSources] = useState([])
  const [quality, setQuality] = useState(null)
  const [denied, setDenied] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) { navigate('/login', { replace: true }); return }

    setLoaded(false)
    Promise.all([
      api.adminStats(days),
      api.adminStatsDaily(days),
      api.adminStatsCategories().catch(() => ({ items: [] })),
      api.adminStatsSources().catch(() => ({ items: [] })),
      api.adminStatsQuality().catch(() => null),
    ])
      .then(([overview, byDay, cats, srcs, qual]) => {
        setData(overview)
        setDaily(byDay.items || [])
        setCategories(cats.items || [])
        setSources(srcs.items || [])
        setQuality(qual)
        setDenied(false)
      })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [authLoading, user, days, navigate])

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('stats.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  const share = (part, whole) => (whole ? Math.round((part / whole) * 100) : 0)

  return (
    <div className="page admin-stats">
      <PageHeader title={t('stats.title')} />

      <div className="admin-filters">
        {PERIODS.map((d) => (
          <button
            key={d}
            className={`chip ${days === d ? 'chip-active' : ''}`}
            onClick={() => setDays(d)}
          >
            {t('stats.days', { count: d })}
          </button>
        ))}
      </div>

      {!loaded && <AdminStatsSkeleton />}

      {data && (
        <>
          <div className="stats-cards">
            <div className="stats-card">
              <div className="stats-value">{data.listings.active}</div>
              <div className="stats-label">{t('stats.in_feed')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.listings.fresh}</div>
              <div className="stats-label">{t('stats.added')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.listings.fresh_own}</div>
              <div className="stats-label">{t('stats.added_own')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.listings.pending}</div>
              <div className="stats-label">{t('stats.pending')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.people.sellers}</div>
              <div className="stats-label">{t('stats.sellers')}</div>
            </div>
            <div className="stats-card">
              <div className="stats-value">{data.people.fresh}</div>
              <div className="stats-label">{t('stats.new_people')}</div>
            </div>
          </div>

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_day')}</div>
            <div className="stats-legend">
              <span className="dot dot-all" /> {t('stats.all')}
              <span className="dot dot-own" /> {t('stats.own')}
            </div>
            <BarsChart key={days} items={daily} valueKey="listings" secondKey="own" />
          </div>

          {/* Посещаемость отдельным графиком, а не вторым рядом в
              предыдущем: числа разного порядка — объявлений за день
              десятки, заходов сотни, — и в одном графике столбики
              объявлений превратились бы в незаметную полоску у нуля. */}
          <div className="stats-block">
            <div className="stats-block-title">{t('stats.visits')}</div>
            {/* Порядок подписей повторяет порядок рядов в графике:
                светлым рисуется первый ряд (заходы), тёмным — второй
                (люди). Подписал их наоборот и увидел на снимке. */}
            <div className="stats-legend">
              <span className="dot dot-all" /> {t('stats.hits')}
              <span className="dot dot-own" /> {t('stats.visitors')}
            </div>
            <BarsChart
              key={`visits-${days}`}
              items={daily}
              valueKey="hits"
              secondKey="visitors"
              unitKey="stats.hits_count"
              secondLabelKey="stats.visitors_short"
            />
          </div>

          {quality && (
            <div className="stats-block">
              <div className="stats-block-title">{t('stats.quality')}</div>
              <div className="stats-rows">
                <div className="stats-row">
                  <span>{t('stats.no_price')}</span>
                  <span>{quality.no_price} · {share(quality.no_price, quality.active)}%</span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.no_photo')}</span>
                  <span>{quality.no_photo} · {share(quality.no_photo, quality.active)}%</span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.no_city')}</span>
                  <span>{quality.no_city} · {share(quality.no_city, quality.active)}%</span>
                </div>
                <div className="stats-row">
                  <span>{t('stats.not_translated')}</span>
                  <span>
                    {quality.not_translated} · {share(quality.not_translated, quality.active)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_category')}</div>
            <div className="stats-rows">
              {categories.map((c) => (
                <div key={c.slug} className={`stats-row ${c.count ? '' : 'stats-row-empty'}`}>
                  <span>{t(`categories.${c.slug}`, c.slug)}</span>
                  <span>{c.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="stats-block">
            <div className="stats-block-title">{t('stats.by_source')}</div>
            <div className="stats-rows">
              {sources.map((s) => (
                <div key={s.source} className="stats-row">
                  <span>{s.source === 'own' ? t('stats.own_source') : (s.title || s.source)}</span>
                  <span>{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
