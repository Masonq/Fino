import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { displayCity } from '../data/cities'
import PageHeader from '../components/PageHeader'
import PromoteButton from '../components/PromoteButton'
import { ListRowSkeletons } from '../components/Skeletons'
import { formatPrice } from '../utils/money'

const TABS = [
  { key: 'active', labelKey: 'my.tab_active' },
  { key: 'pending_moderation', labelKey: 'my.tab_pending' },
  // Без этой вкладки отклонённое объявление просто пропадало из виду:
  // бэкенд его отдавал, а посмотреть было негде — продавец не узнавал
  // ни того, что его отклонили, ни почему.
  { key: 'rejected', labelKey: 'my.tab_rejected' },
  { key: 'sold', labelKey: 'my.tab_sold' },
  { key: 'archived', labelKey: 'my.tab_archived' },
]

export default function MyListings() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [counts, setCounts] = useState({})
  const [tab, setTab] = useState('active')
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState(null)
  // Панель продвижения открыта максимум для одной карточки за раз —
  // id объявления, если открыта, иначе null.
  const [promoteFor, setPromoteFor] = useState(null)

  const load = () => {
    if (!user) { setLoaded(true); return }
    api.myListings(i18n.language)
      .then((res) => { setItems(res.items || []); setCounts(res.counts || {}) })
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }

  useEffect(load, [user, i18n.language])

  const changeStatus = async (id, status) => {
    setBusyId(id)
    try {
      await api.setListingStatus(id, status)
      load()
    } catch { /* оставляем как было */ }
    finally { setBusyId(null) }
  }

  const remove = async (id) => {
    if (!window.confirm(t('my.confirm_delete'))) return
    setBusyId(id)
    try {
      await api.deleteListing(id)
      load()
    } catch (e) {
      alert(e.code === 'listing_has_history' ? t('my.delete_has_history') : t('auth.err_generic'))
    }
    finally { setBusyId(null) }
  }

  if (authLoading) return <div className="fav-page"><PageHeader title={t('my.title')} /></div>

  if (!user) {
    return (
      <div className="fav-page">
        <PageHeader title={t('my.title')} />
        <div className="fav-empty">
          <p>{t('my.need_login')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fmy')}>
            {t('common.login')}
          </button>
        </div>
      </div>
    )
  }

  const visible = items.filter((l) => l.status === tab)

  return (
    <div className="fav-page">
      <PageHeader title={t('my.title')} />

      <div className="my-tabs">
        {TABS.map((tb) => (
          <button
            key={tb.key}
            className={tab === tb.key ? 'my-tab active' : 'my-tab'}
            onClick={() => setTab(tb.key)}
          >
            {t(tb.labelKey)}
            {counts[tb.key] > 0 && <span className="my-tab-count">{counts[tb.key]}</span>}
          </button>
        ))}
      </div>

      {!loaded ? (
        <div className="my-list"><ListRowSkeletons count={4} /></div>
      ) : visible.length === 0 ? (
        <div className="fav-empty">
          <p>{t('my.empty')}</p>
          <Link className="fav-cta" to="/post">{t('nav.post')}</Link>
        </div>
      ) : (
        <div className="my-list">
          {visible.map((l) => (
            <div className="my-row" key={l.id}>
              <Link to={l.path} className="my-main">
                <div className="my-thumb">
                  {l.cover_photo ? <img src={l.cover_photo} alt="" /> : <div className="photo-placeholder" />}
                </div>
                <div className="my-body">
                  <div className="my-title">{l.title}</div>
                  <div className="my-price">
                    {formatPrice(l.price, l.currency, i18n.language) || t('detail.no_price')}
                  </div>
                  <div className="my-meta">
                    {displayCity(l.city, i18n.language)}
                    {l.views_count > 0 && ` · ${t('my.views')} ${l.views_count}`}
                  </div>
                  {l.status === 'rejected' && l.rejection_reason && (
                    <div className="my-rejection">{l.rejection_reason}</div>
                  )}
                </div>
                {/* Показатели и правка — своим столбцом справа от текста,
                    не поверх фото (там их не видно на тёмных снимках,
                    да и закрывают собой сам товар) и не в тесном ряду
                    кнопок снизу. */}
                <div className="my-quick-actions">
                  <button
                    className="my-quick-icon"
                    aria-label={t('ldash.short')}
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigate(`/my/${l.id}/stats`) }}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18" /><path d="M18 9 12 15l-3-3-4 4" /></svg>
                  </button>
                  <button
                    className="my-quick-icon"
                    aria-label={t('edit.save_short')}
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigate(`/edit/${l.id}`) }}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                  </button>
                </div>
              </Link>

              <div className="my-actions">
                {l.status === 'active' && (
                  <>
                    <button disabled={busyId === l.id} onClick={() => changeStatus(l.id, 'sold')}>
                      {t('my.mark_sold')}
                    </button>
                    <button disabled={busyId === l.id} onClick={() => changeStatus(l.id, 'archived')}>
                      {t('my.archive')}
                    </button>
                  </>
                )}
                {(l.status === 'sold' || l.status === 'archived') && (
                  <>
                    <button disabled={busyId === l.id} onClick={() => changeStatus(l.id, 'active')}>
                      {t('my.restore')}
                    </button>
                    <button className="danger" disabled={busyId === l.id} onClick={() => remove(l.id)}>
                      {t('my.delete')}
                    </button>
                  </>
                )}
              </div>

              {/* Продвинуть — отдельной заметной строкой, не наравне
                  с управлением статусом: пять кнопок в одном тесном
                  ряду теснили друг друга, а это единственная кнопка,
                  что приносит деньги — прятать её среди прочих не
                  стоит. На всю ширину, не по размеру текста. */}
              {l.status === 'active' && (
                <div className="my-promote-slot">
                  <PromoteButton
                    listingId={l.id} renderMode="trigger"
                    open={promoteFor === l.id}
                    onOpenChange={(v) => setPromoteFor(v ? l.id : null)}
                  />
                </div>
              )}

              {promoteFor === l.id && (
                <div className="promo-sheet-dock">
                  <PromoteButton
                    listingId={l.id} renderMode="sheet"
                    open={promoteFor === l.id}
                    onOpenChange={(v) => setPromoteFor(v ? l.id : null)}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
