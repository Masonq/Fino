import EmptyArt from '../components/EmptyArt'
import SlidePill from '../components/SlidePill'
import { useAutoAnimate } from '@formkit/auto-animate/react'
import { showIsland } from '../utils/island'
import { confirmSheet } from '../utils/confirm'
import { intlLocale } from '../utils/time'
import { useEffect, useState } from 'react'
import { keepValue, readValue, useKeepPlace } from '../utils/keepPlace'
import { withoutRemoved } from '../utils/removedListings'
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

// Один и тот же силуэт, что и в панели «Поднять просмотры» — узнаваем
// в двух местах сразу. Плоские, однотонные (currentColor), под цвет
// текста бейджа — на 14px глянцевый 3D-рендер, как у картинок
// категорий, превращается в кашу, тут это другой масштаб задачи.
const PROMO_ICONS = {
  highlight: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21l3.5-1 11-11-2.5-2.5-11 11L3 21z" />
      <path d="M14.5 6.5L17.5 9.5" />
      <circle cx="19" cy="19" r="2.3" fill="currentColor" stroke="none" />
    </svg>
  ),
  bump: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M20 20l-4.35-4.35" />
      <path d="M10.5 13.5V7.5M10.5 7.5L8 10M10.5 7.5L13 10" />
    </svg>
  ),
  xl_card: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 9V5a1 1 0 011-1h4" />
      <path d="M20 9V5a1 1 0 00-1-1h-4" />
      <path d="M4 15v4a1 1 0 001 1h4" />
      <path d="M20 15v4a1 1 0 01-1 1h-4" />
    </svg>
  ),
}

export default function MyListings() {
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('my-listings')
  const { t, i18n } = useTranslation()
  // Удалили или добавили — соседи плавно съезжают (AutoAnimate, ~3 КБ; сам гаснет при «уменьшить движение»)
  const [listRef] = useAutoAnimate()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  // закреплённые в профиле (до трёх) и «поделиться карточкой» — готовая картинка с фото, ценой и ссылкой для сторис и постов
  const [pins, setPins] = useState([])
  useEffect(() => { if (user?.id) api.sellerProfile(user.id, i18n.language).then((p) => setPins(p.pinned_ids || [])).catch(() => {}) }, [user?.id, i18n.language])
  const shareCard = async (l) => {
    const url = `${window.location.origin}${l.public_path || `/go/${l.id}`}`
    const img = `/api/og/listing/${l.id}.png?v=3&lang=${i18n.language}`
    try {
      const blob = await (await fetch(img)).blob()
      const file = new File([blob], 'plonk.png', { type: 'image/png' })
      if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], text: `${l.title} — ${url}` }); return }
    } catch { /* не вышло файлом — делимся ссылкой */ }
    try { await navigator.share({ title: l.title, url }) } catch { window.open(img, '_blank') }
  }

  const [items, setItems] = useState([])
  const [renewing, setRenewing] = useState(null)

  // Сколько дней осталось до снятия. Округляем вверх: «остался 1 день»
  // честнее, чем «0 дней», когда до снятия ещё несколько часов.
  const daysLeft = (l) => {
    if (!l.expires_at) return null
    const ms = new Date(l.expires_at + 'Z').getTime() - Date.now()
    return ms <= 0 ? 0 : Math.ceil(ms / 86400000)
  }

  const renew = async (l) => {
    setRenewing(l.id)
    try {
      const res = await api.renewListing(l.id)
      setItems((prev) => prev.map((x) => (
        x.id === l.id ? { ...x, expires_at: res.expires_at, status: 'active' } : x
      )))
    } catch { /* не вышло — строка останется, человек нажмёт ещё раз */ }
    finally { setRenewing(null) }
  }
  const [counts, setCounts] = useState({})
  const [tab, setTab] = useState(() => readValue('my-tab', 'active'))
  useEffect(() => { keepValue('my-tab', tab) }, [tab])
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState(null)
  // Панель продвижения открыта максимум для одной карточки за раз —
  // id объявления, если открыта, иначе null.
  const [promoteFor, setPromoteFor] = useState(null)
  // Всплывающая подсказка «до какого числа» под значком продвижения —
  // тоже максимум одна открытая сразу, ключ вида "id_объявления:тип".
  const [infoFor, setInfoFor] = useState(null)

  // initial — первый заход или смена пользователя/языка: до ответа скелет. Обновление после действия (снять,
  // удалить, продлить) скелет не показывает — иначе список мигал бы после каждого нажатия.
  const load = (initial = false) => {
    if (authLoading) return
    if (!user) { setLoaded(true); return }
    if (initial) setLoaded(false)
    api.myListings(i18n.language)
      .then((res) => { setItems(res.items || []); setCounts(res.counts || {}) })
      .catch(() => setItems([]))
      .finally(() => setLoaded(true))
  }

  useEffect(() => { load(true) }, [user, i18n.language, authLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  // Закрываем открытую подсказку по тапу куда угодно ещё — иначе она
  // висела бы до следующего тапа по тому же значку.
  useEffect(() => {
    if (!infoFor) return
    const close = () => setInfoFor(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [infoFor])

  const changeStatus = async (id, status) => {
    setBusyId(id)
    // Панель продвижения могла быть открыта именно для этого
    // объявления — «Продано»/«Снять с публикации»/«Вернуть в продажу»
    // переносит его в другую вкладку, продвигать там уже нельзя
    // (бэкенд и так откажет), панель должна закрыться вместе со сменой.
    setPromoteFor((prev) => (prev === id ? null : prev))
    try {
      await api.setListingStatus(id, status)
      load()
    } catch { /* оставляем как было */ }
    finally { setBusyId(null) }
  }

  const remove = async (id) => {
    if (!(await confirmSheet({ title: t('my.confirm_delete'), confirm: t('confirm.delete'), danger: true }))) return
    setBusyId(id)
    setPromoteFor((prev) => (prev === id ? null : prev))
    try {
      await api.deleteListing(id)
      load()
    } catch (e) {
      showIsland({ text: e.code === 'listing_has_history' ? t('my.delete_has_history') : t('auth.err_generic'), kind: 'warn' })
    }
    finally { setBusyId(null) }
  }

  if (!user && !authLoading) {
    return (
      <div className="fav-page">
        <PageHeader title={t('my.title')} kicker={t('my.kicker')} />
        <div className="fav-empty">
          <EmptyArt name="my" />
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
      <PageHeader title={t('my.title')} kicker={t('my.kicker')} />

      <div className="my-tabs">
        <div className="pill-track pill-row">
          <SlidePill />
        {TABS.map((tb) => (
          <button
            key={tb.key}
            className={tab === tb.key ? 'my-tab active' : 'my-tab'}
            onClick={() => setTab(tb.key)}
          >
            {t(tb.labelKey)}
            <span className="my-tab-count">{counts[tb.key] > 0 ? counts[tb.key] : ''}</span>
          </button>
        ))}
        </div>
      </div>

      {!loaded ? (
        <div className="my-list"><ListRowSkeletons count={4} /></div>
      ) : visible.length === 0 ? (
        <div className="fav-empty">
          <EmptyArt name="my" />
          <p>{t('my.empty')}</p>
          <Link className="fav-cta" to="/post">{t('nav.post')}</Link>
        </div>
      ) : (
        <div className="my-list" ref={listRef}>
          {withoutRemoved(visible).map((l) => (
            <div className="my-row" key={l.id}>
              <Link to={l.path} className="my-main">
                <div className="my-thumb">
                  {l.cover_photo ? <img src={l.cover_photo} alt="" /> : <div className="photo-placeholder" />}
                </div>
                <div className="my-body">
                  <div className="my-title-row">
                    <div className="my-title">{l.title}</div>
                    {l.active_promotions?.length > 0 && (
                      <div className="my-promo-icons">
                        {l.active_promotions.map((p) => (
                          <div className="my-promo-icon-wrap" key={p.type}>
                            <button
                              className="my-promo-icon"
                              aria-label={t(`promo.type_${p.type}`)}
                              onClick={(e) => {
                                e.preventDefault(); e.stopPropagation()
                                setInfoFor(infoFor === `${l.id}:${p.type}` ? null : `${l.id}:${p.type}`)
                              }}
                            >
                              {PROMO_ICONS[p.type]}
                            </button>
                            {infoFor === `${l.id}:${p.type}` && (
                              <div className="my-promo-info" onClick={(e) => e.stopPropagation()}>
                                <strong>{t(`promo.type_${p.type}`)}</strong>
                                <span>
                                  {p.expires_at
                                    ? t('promo.active_until', { date: new Date(p.expires_at).toLocaleDateString(intlLocale(i18n.language), { day: "numeric", month: "long", year: "numeric" }) })
                                    : t('promo.active_now')}
                                </span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
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
                  {l.status === 'active' && (
                    <button className={`my-quick-icon${pins.includes(l.id) ? ' is-on' : ''}`} aria-label={t(pins.includes(l.id) ? 'pins.unpin' : 'pins.pin')}
                      onClick={async (e) => { e.preventDefault(); e.stopPropagation(); try { const r = await api.togglePin(l.id); setPins(r.pins) } catch (err) { confirmSheet({ title: t(err?.code === 'pins_limit' ? 'pins.limit' : 'support.failed'), confirm: 'OK' }) } }}>
                      <svg viewBox="0 0 24 24" fill={pins.includes(l.id) ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 17v5" /><path d="M9 10.8V4h6v6.8l2.6 3.2H6.4Z" /></svg>
                    </button>
                  )}
                  {l.status === 'active' && (
                    <button className="my-quick-icon" aria-label={t('pins.share')}
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); shareCard(l) }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7" /><path d="m16 6-4-4-4 4" /><path d="M12 2v13" /></svg>
                    </button>
                  )}
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
                {(l.status === 'pending_moderation' || l.status === 'rejected') && (
                  <button className="danger" disabled={busyId === l.id} onClick={() => remove(l.id)}>
                    {t('my.delete')}
                  </button>
                )}
              </div>

              {/* Статус уже купленного продвижения теперь значками
                  у заголовка (my-promo-icons выше) — видно сразу на
                  карточке, без лишнего клика в панель «Поднять
                  просмотры», но не отдельным рядом текстовых бейджей,
                  тесно с кнопками статуса под ним. */}

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

              {promoteFor === l.id && l.status === 'active' && (
                <div className="promo-sheet-dock">
                  <PromoteButton
                    listingId={l.id} renderMode="sheet"
                    open={promoteFor === l.id}
                    onOpenChange={(v) => setPromoteFor(v ? l.id : null)}
                  />
                </div>
              )}
              {/* Скоро снимут — и что с этим делать. Напоминание
                  приходило, а продлить можно было только правкой
                  объявления наугад: объявления умирали не потому, что
                  вещь продана. */}
              {daysLeft(l) !== null && daysLeft(l) <= 7 && l.status === 'active' && (
                <div className="my-expiry">
                  <span>{t('my.expires_in', { count: daysLeft(l) })}</span>
                  <button
                    disabled={renewing === l.id}
                    onClick={() => renew(l)}
                  >
                    {t('my.renew')}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
